import os
import asyncio
import uuid
from typing import Optional, Dict, Any, AsyncIterator
from pathlib import Path
from backend.app.config import settings
from backend.app.db.database import get_db_connection
from backend.app.ingestion import get_parser_for_file
from backend.app.ingestion.chunker import chunk_document
from backend.app.retrieval.embedder import get_embedding_provider
from backend.app.retrieval.vector_store import get_vector_store

# In-memory progress tracking for active indexing jobs
_job_progress: Dict[str, Dict[str, Any]] = {}

class IndexingService:
    """Coordinate parsing, chunking, embedding, and vector upsert."""

    def __init__(self):
        self.embedder = get_embedding_provider()
        self.vector_store = get_vector_store()

    def update_job_status(self, job_id: str, document_id: str, status: str, progress: int, error: Optional[str] = None):
        _job_progress[document_id] = {
            "job_id": job_id,
            "document_id": document_id,
            "status": status,
            "progress": progress,
            "error": error
        }
        with get_db_connection() as conn:
            conn.execute(
                """
                UPDATE indexing_jobs
                SET status = ?, progress = ?, error = ?, completed_at = CASE WHEN ? IN ('COMPLETED', 'FAILED') THEN CURRENT_TIMESTAMP ELSE completed_at END
                WHERE id = ?
                """,
                (status, progress, error, status, job_id)
            )
            conn.execute(
                """
                UPDATE documents
                SET status = ?, error = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, error, document_id)
            )

    async def index_document(self, document_id: str, job_id: str, file_path: str, filename: str) -> None:
        """Execute full indexing pipeline asynchronously."""
        try:
            # Step 1: Parse
            self.update_job_status(job_id, document_id, "PARSING", 20)
            await asyncio.sleep(0.05)
            parser = get_parser_for_file(file_path)
            pages = parser.parse(file_path)

            if not pages:
                raise ValueError(f"No pages extracted from {filename}")

            # Step 2: Chunk
            self.update_job_status(job_id, document_id, "CHUNKING", 40)
            await asyncio.sleep(0.05)
            chunks = chunk_document(
                document_id=document_id,
                document_name=filename,
                pages=pages,
                chunk_size_words=settings.chunk_size,
                chunk_overlap_words=settings.chunk_overlap
            )

            if not chunks:
                raise ValueError(f"No usable text chunks generated from {filename}")

            # Step 3: Embed
            self.update_job_status(job_id, document_id, "EMBEDDING", 70)
            await asyncio.sleep(0.05)
            texts = [c.text for c in chunks]
            embeddings = self.embedder.embed_documents(texts)

            # Step 4: Index into ChromaDB
            self.update_job_status(job_id, document_id, "INDEXING", 90)
            await asyncio.sleep(0.05)
            ids = [c.chunk_id for c in chunks]
            metadatas = [c.metadata for c in chunks]
            self.vector_store.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

            # Step 5: Completed
            self.update_job_status(job_id, document_id, "COMPLETED", 100)

        except Exception as err:
            err_msg = str(err)
            self.update_job_status(job_id, document_id, "FAILED", 0, error=err_msg)

    async def stream_indexing_progress(self, document_id: str) -> AsyncIterator[str]:
        """Stream SSE events for a document's indexing job."""
        last_progress = -1
        while True:
            info = _job_progress.get(document_id)
            if not info:
                # Read from SQLite
                with get_db_connection() as conn:
                    row = conn.execute(
                        "SELECT status, progress, error, id as job_id FROM indexing_jobs WHERE document_id = ? ORDER BY started_at DESC LIMIT 1",
                        (document_id,)
                    ).fetchone()
                    if row:
                        info = dict(row)
                    else:
                        yield f"event: error\ndata: {{\"error\": \"Document {document_id} not found\"}}\n\n"
                        break

            status = info.get("status", "QUEUED")
            progress = info.get("progress", 0)
            error = info.get("error")

            if progress != last_progress or status in ("COMPLETED", "FAILED"):
                last_progress = progress
                if status == "FAILED":
                    yield f"event: error\ndata: {{\"status\": \"FAILED\", \"error\": \"{error}\"}}\n\n"
                    break
                elif status == "COMPLETED":
                    yield f"event: complete\ndata: {{\"status\": \"COMPLETED\", \"progress\": 100}}\n\n"
                    break
                else:
                    yield f"event: status\ndata: {{\"status\": \"{status}\", \"progress\": {progress}}}\n\n"

            await asyncio.sleep(0.3)

    def index_seed_documents(self) -> int:
        """Scan seed directory and index any unindexed research papers."""
        seed_dir = settings.resolve_path(settings.seed_docs_path)
        pdf_files = []
        if seed_dir.exists():
            pdf_files = list(seed_dir.glob("*.pdf")) + list(seed_dir.glob("*.txt")) + list(seed_dir.glob("*.md"))

        if not pdf_files:
            alt_dir = settings.resolve_path("Research papers")
            if alt_dir.exists():
                pdf_files = list(alt_dir.glob("*.pdf")) + list(alt_dir.glob("*.txt")) + list(alt_dir.glob("*.md"))

        if not pdf_files:
            return 0

        indexed_names = self.vector_store.list_indexed_document_names()
        indexed_count = 0
        for p in sorted(pdf_files):
            filename = p.name
            if filename in indexed_names:
                # Ensure record exists in SQLite
                with get_db_connection() as conn:
                    exists = conn.execute(
                        "SELECT id FROM documents WHERE filename = ?", (filename,)
                    ).fetchone()
                    if not exists:
                        doc_id = f"seed_{uuid.uuid4().hex[:8]}"
                        conn.execute(
                            """
                            INSERT INTO documents (id, filename, path, file_type, file_size, status, is_seed)
                            VALUES (?, ?, ?, ?, ?, 'COMPLETED', 1)
                            """,
                            (doc_id, filename, str(p), p.suffix.lower(), p.stat().st_size)
                        )
                continue

            # Need to index this seed file
            doc_id = f"seed_{uuid.uuid4().hex[:8]}"
            job_id = f"job_{uuid.uuid4().hex[:8]}"
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO documents (id, filename, path, file_type, file_size, status, is_seed)
                    VALUES (?, ?, ?, ?, ?, 'INDEXING', 1)
                    """,
                    (doc_id, filename, str(p), p.suffix.lower(), p.stat().st_size)
                )
                conn.execute(
                    """
                    INSERT INTO indexing_jobs (id, document_id, status, progress)
                    VALUES (?, ?, 'INDEXING', 10)
                    """,
                    (job_id, doc_id)
                )

            try:
                parser = get_parser_for_file(str(p))
                pages = parser.parse(str(p))
                chunks = chunk_document(
                    document_id=doc_id,
                    document_name=filename,
                    pages=pages,
                    chunk_size_words=settings.chunk_size,
                    chunk_overlap_words=settings.chunk_overlap
                )
                if chunks:
                    texts = [c.text for c in chunks]
                    embeddings = self.embedder.embed_documents(texts)
                    ids = [c.chunk_id for c in chunks]
                    metadatas = [c.metadata for c in chunks]
                    self.vector_store.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

                    with get_db_connection() as conn:
                        conn.execute(
                            "UPDATE documents SET status = 'COMPLETED', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (doc_id,)
                        )
                        conn.execute(
                            "UPDATE indexing_jobs SET status = 'COMPLETED', progress = 100, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (job_id,)
                        )
                    indexed_count += 1
            except Exception as err:
                with get_db_connection() as conn:
                    conn.execute(
                        "UPDATE documents SET status = 'FAILED', error = ? WHERE id = ?",
                        (str(err), doc_id)
                    )
                    conn.execute(
                        "UPDATE indexing_jobs SET status = 'FAILED', error = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (str(err), job_id)
                    )

        return indexed_count


_default_indexing_service = None

def get_indexing_service() -> IndexingService:
    global _default_indexing_service
    if _default_indexing_service is None:
        _default_indexing_service = IndexingService()
    return _default_indexing_service

