import json
import time
import uuid
import re
from typing import AsyncIterator, List, Dict, Any, Optional
from backend.app.config import settings
from backend.app.db.database import get_db_connection
from backend.app.retrieval.vector_store import SearchResult
from backend.app.services.retrieval_service import get_retrieval_service
from backend.app.services.security_service import get_security_service
from backend.app.llm import get_llm_provider
from backend.app.prompts.answer import SYSTEM_PROMPT, build_rag_prompt
from backend.app.schemas.chat import Citation, EvidenceItem, ChatResponse

CITATION_REGEX = re.compile(
    r"\[(?:Doc|Document):\s*([^,]+),\s*(?:Page|p):\s*(\d+),\s*(?:Chunk):\s*([^\]]+)\]",
    re.IGNORECASE
)

class ChatService:
    """Orchestrate retrieval, security checks, LLM generation, and SSE events."""

    def __init__(self):
        self.retrieval_service = get_retrieval_service()
        self.security_service = get_security_service()
        self.llm_provider = get_llm_provider()

    def ensure_session(self, session_id: Optional[str]) -> str:
        sid = session_id or f"sess_{uuid.uuid4().hex[:8]}"
        with get_db_connection() as conn:
            exists = conn.execute("SELECT id FROM sessions WHERE id = ?", (sid,)).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO sessions (id, title) VALUES (?, ?)",
                    (sid, "New Research Session")
                )
        return sid

    def save_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        meta_json = json.dumps(metadata) if metadata else None
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO messages (id, session_id, role, content, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (msg_id, session_id, role, content, meta_json)
            )

            # If this is a user message and session has default title, set title to first message
            if role == "user":
                clean_title = content.strip().replace("\n", " ")
                if len(clean_title) > 60:
                    clean_title = clean_title[:57] + "..."
                conn.execute(
                    """
                    UPDATE sessions
                    SET title = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND (title = 'New Research Session' OR title IS NULL OR title = '')
                    """,
                    (clean_title, session_id)
                )
            else:
                conn.execute(
                    "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (session_id,)
                )

    def extract_citations(self, text: str, evidence: List[SearchResult]) -> List[Citation]:
        citations: List[Citation] = []
        matches = CITATION_REGEX.findall(text)
        seen = set()

        for doc_match, page_match, chunk_match in matches:
            clean_chunk = chunk_match.strip()
            key = f"{doc_match.strip()}_{page_match.strip()}_{clean_chunk}"
            if key not in seen:
                seen.add(key)
                citations.append(
                    Citation(
                        document=doc_match.strip(),
                        page=int(page_match.strip()),
                        chunk_id=clean_chunk
                    )
                )

        # If LLM didn't emit exact regex citations but answered with evidence, extract citations from used evidence
        if not citations and evidence and "insufficient evidence" not in text.lower():
            for ev in evidence[:3]:
                citations.append(
                    Citation(
                        document=ev.document_name,
                        page=ev.page_number,
                        chunk_id=ev.chunk_id
                    )
                )
        return citations

    async def chat_stream(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = 10
    ) -> AsyncIterator[str]:
        """Execute RAG chat and yield SSE formatted events."""
        start_time = time.time()
        sid = self.ensure_session(session_id)

        # 1. Validate query
        try:
            clean_query = self.security_service.validate_query(query)
        except ValueError as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            return

        # Save user message
        self.save_message(sid, "user", clean_query)

        # 2. Check for injection attempt in query
        security_report = self.security_service.inspect_content(clean_query)

        # 3. Retrieve evidence
        evidence_results, is_sufficient = self.retrieval_service.retrieve(
            query=clean_query,
            initial_top_k=top_k,
            final_top_k=settings.rerank_top_k
        )

        # Emit retrieval event
        yield f"event: retrieval\ndata: {json.dumps({'query': clean_query, 'candidate_count': len(evidence_results), 'has_injection_warning': security_report['has_injection']})}\n\n"

        # 4. Handle insufficient evidence
        if not is_sufficient or not evidence_results:
            refusal_text = "Insufficient evidence"
            latency = round((time.time() - start_time) * 1000, 2)
            
            yield f"event: evidence\ndata: {json.dumps({'evidence': []})}\n\n"
            yield f"event: token\ndata: {json.dumps({'text': refusal_text})}\n\n"
            yield f"event: complete\ndata: {json.dumps({'session_id': sid, 'answer': refusal_text, 'evidence': [], 'citations': [], 'grounded': False, 'latency_ms': latency})}\n\n"
            
            self.save_message(
                sid,
                "assistant",
                refusal_text,
                {"evidence": [], "citations": [], "grounded": False, "latency_ms": latency}
            )
            return

        # 5. Format evidence payload
        evidence_payload = [
            {
                "document": ev.document_name,
                "chunk_id": ev.chunk_id,
                "page": ev.page_number,
                "section": ev.section,
                "text": ev.text,
                "score": ev.score
            }
            for ev in evidence_results
        ]
        yield f"event: evidence\ndata: {json.dumps({'evidence': evidence_payload})}\n\n"

        # 6. Build RAG prompt with security boundary wrapping
        prompt = build_rag_prompt(clean_query, evidence_results)

        # 7. Stream LLM tokens
        full_tokens: List[str] = []
        try:
            async for token in self.llm_provider.stream(prompt, SYSTEM_PROMPT):
                full_tokens.append(token)
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
        except Exception as e:
            # Fallback or error reporting
            err_msg = f"LLM generation failed: {str(e)}"
            yield f"event: error\ndata: {json.dumps({'error': err_msg})}\n\n"
            return

        answer_text = "".join(full_tokens).strip()
        latency = round((time.time() - start_time) * 1000, 2)

        # Check if LLM itself declared insufficient evidence
        is_grounded = True
        if "insufficient evidence" in answer_text.lower():
            is_grounded = False

        # 8. Extract citations
        citations = self.extract_citations(answer_text, evidence_results) if is_grounded else []
        citations_payload = [c.model_dump() for c in citations]
        yield f"event: citation\ndata: {json.dumps({'citations': citations_payload})}\n\n"

        # 9. Emit complete event
        complete_payload = {
            "session_id": sid,
            "answer": answer_text,
            "evidence": evidence_payload,
            "citations": citations_payload,
            "grounded": is_grounded,
            "latency_ms": latency
        }
        yield f"event: complete\ndata: {json.dumps(complete_payload)}\n\n"

        # Save assistant message in SQLite
        self.save_message(
            sid,
            "assistant",
            answer_text,
            {
                "evidence": evidence_payload,
                "citations": citations_payload,
                "grounded": is_grounded,
                "latency_ms": latency
            }
        )

    async def execute_chat(
        self,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = 10
    ) -> ChatResponse:
        """Non-streaming chat execution for programmatic evaluation."""
        start_time = time.time()
        sid = self.ensure_session(session_id)
        clean_query = self.security_service.validate_query(query)

        evidence_results, is_sufficient = self.retrieval_service.retrieve(
            query=clean_query,
            initial_top_k=top_k,
            final_top_k=settings.rerank_top_k
        )

        latency = round((time.time() - start_time) * 1000, 2)

        if not is_sufficient or not evidence_results:
            return ChatResponse(
                session_id=sid,
                answer="Insufficient evidence",
                evidence=[],
                citations=[],
                grounded=False,
                latency_ms=latency
            )

        evidence_items = [
            EvidenceItem(
                document=ev.document_name,
                chunk_id=ev.chunk_id,
                page=ev.page_number,
                section=ev.section,
                text=ev.text,
                score=ev.score
            )
            for ev in evidence_results
        ]

        prompt = build_rag_prompt(clean_query, evidence_results)
        answer_text = await self.llm_provider.generate(prompt, SYSTEM_PROMPT)
        total_latency = round((time.time() - start_time) * 1000, 2)

        is_grounded = True
        if "insufficient evidence" in answer_text.lower():
            is_grounded = False

        citations = self.extract_citations(answer_text, evidence_results) if is_grounded else []

        return ChatResponse(
            session_id=sid,
            answer=answer_text,
            evidence=evidence_items,
            citations=citations,
            grounded=is_grounded,
            latency_ms=total_latency
        )


_default_chat_service = None

def get_chat_service() -> ChatService:
    global _default_chat_service
    if _default_chat_service is None:
        _default_chat_service = ChatService()
    return _default_chat_service

