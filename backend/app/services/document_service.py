import os
import uuid
import shutil
from typing import List, Optional, Dict, Any
from pathlib import Path
from backend.app.config import settings
from backend.app.db.database import get_db_connection
from backend.app.db.models import DocumentModel, IndexingJobModel
from backend.app.retrieval.vector_store import get_vector_store

class DocumentService:
    """Manage documents and indexing jobs."""

    def __init__(self):
        self.upload_dir = settings.resolve_path(settings.upload_path)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.seed_dir = settings.resolve_path(settings.seed_docs_path)
        self.seed_dir.mkdir(parents=True, exist_ok=True)

    def list_documents(self) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_indexing_job(self, document_id: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM indexing_jobs WHERE document_id = ? ORDER BY started_at DESC LIMIT 1",
                (document_id,)
            ).fetchone()
            return dict(row) if row else None

    def create_uploaded_document(self, filename: str, content: bytes) -> tuple[str, str, str]:
        """Save uploaded file, create document and indexing records."""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".pdf", ".txt", ".md"]:
            raise ValueError(f"Unsupported file format '{ext}'. Allowed: .pdf, .txt, .md")

        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError(f"File size exceeds maximum allowed of {settings.max_upload_size_mb} MB")

        if len(content) == 0:
            raise ValueError("Uploaded file is empty (0 bytes).")

        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        safe_filename = f"{doc_id}_{filename}"
        dest_path = self.upload_dir / safe_filename

        with open(dest_path, "wb") as f:
            f.write(content)

        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (id, filename, path, file_type, file_size, status, is_seed)
                VALUES (?, ?, ?, ?, ?, 'QUEUED', 0)
                """,
                (doc_id, filename, str(dest_path), ext, len(content))
            )
            conn.execute(
                """
                INSERT INTO indexing_jobs (id, document_id, status, progress)
                VALUES (?, ?, 'QUEUED', 0)
                """,
                (job_id, doc_id)
            )

        return doc_id, job_id, str(dest_path)

    def delete_document(self, doc_id: str) -> bool:
        doc = self.get_document(doc_id)
        if not doc:
            return False

        # Remove from vector store
        store = get_vector_store()
        store.delete_document(doc_id)

        # Remove physical file if in uploads
        file_path = Path(doc["path"])
        if file_path.exists() and "uploads" in str(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        # Remove database records
        with get_db_connection() as conn:
            conn.execute("DELETE FROM indexing_jobs WHERE document_id = ?", (doc_id,))
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

        return True


_default_document_service = None

def get_document_service() -> DocumentService:
    global _default_document_service
    if _default_document_service is None:
        _default_document_service = DocumentService()
    return _default_document_service

