from typing import List, Tuple
from backend.app.config import settings
from backend.app.retrieval.embedder import get_embedding_provider
from backend.app.retrieval.vector_store import get_vector_store, SearchResult
from backend.app.retrieval.reranker import get_reranker

class RetrievalService:
    """Retrieve and rerank relevant document chunks for user queries."""

    def __init__(self):
        self.embedder = get_embedding_provider()
        self.vector_store = get_vector_store()
        self.reranker = get_reranker()

    def retrieve(
        self,
        query: str,
        initial_top_k: int = None,
        final_top_k: int = None,
        threshold: float = None
    ) -> Tuple[List[SearchResult], bool]:
        """Retrieve evidence chunks for query.
        
        Returns tuple of (evidence_chunks, is_sufficient_evidence).
        """
        top_k = initial_top_k or settings.retrieval_top_k
        top_n = final_top_k or settings.rerank_top_k
        min_score = threshold if threshold is not None else settings.relevance_threshold

        query_clean = query.strip()
        if not query_clean:
            return [], False

        # 1. Embed query
        query_embedding = self.embedder.embed_query(query_clean)

        # 2. Vector search in ChromaDB
        candidates = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k
        )

        if not candidates:
            return [], False

        # 3. Rerank candidates
        reranked = self.reranker.rerank(
            query=query_clean,
            results=candidates,
            top_n=top_n
        )

        # 4. Filter against relevance threshold
        supported_evidence = [r for r in reranked if r.score >= min_score]

        if not supported_evidence:
            return [], False

        return supported_evidence, True


_default_retrieval_service = None

def get_retrieval_service() -> RetrievalService:
    global _default_retrieval_service
    if _default_retrieval_service is None:
        _default_retrieval_service = RetrievalService()
    return _default_retrieval_service

