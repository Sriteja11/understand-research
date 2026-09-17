import re
import math
from abc import ABC, abstractmethod
from typing import List, Dict
from backend.app.retrieval.vector_store import SearchResult
from backend.app.config import settings

class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, results: List[SearchResult], top_n: int = 4) -> List[SearchResult]:
        pass


class HybridReranker(Reranker):
    """Lexical-semantic hybrid reranker with cross-encoder capability.
    
    Combines dense vector similarity scores with BM25-style lexical matching,
    or uses CrossEncoder when available.
    """

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.reranker_model
        self.cross_encoder = None
        self._load_cross_encoder()

    def _load_cross_encoder(self):
        try:
            from sentence_transformers import CrossEncoder
            self.cross_encoder = CrossEncoder(self.model_name)
        except Exception:
            # Fall back to lexical-semantic scoring if cross-encoder cannot load offline
            self.cross_encoder = None

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def _bm25_score(self, query_terms: List[str], doc_terms: List[str], avg_len: float) -> float:
        if not doc_terms:
            return 0.0
        k1 = 1.5
        b = 0.75
        doc_len = len(doc_terms)
        term_freqs: Dict[str, int] = {}
        for t in doc_terms:
            term_freqs[t] = term_freqs.get(t, 0) + 1

        score = 0.0
        for q in query_terms:
            if q in term_freqs:
                tf = term_freqs[q]
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_len / (avg_len or 1.0)))
                score += numerator / denominator
        return score

    def rerank(self, query: str, results: List[SearchResult], top_n: int = 4) -> List[SearchResult]:
        if not results:
            return []

        # If cross-encoder is initialized, use it directly
        if self.cross_encoder is not None:
            try:
                pairs = [[query, r.text] for r in results]
                scores = self.cross_encoder.predict(pairs)
                for i, r in enumerate(results):
                    # Sigmoid transform to normalize cross-encoder logits into [0, 1]
                    raw_score = float(scores[i])
                    normalized = 1.0 / (1.0 + math.exp(-raw_score))
                    r.score = round(normalized, 4)
                sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
                return sorted_results[:top_n]
            except Exception:
                pass

        # Lexical-semantic reciprocal rank fusion fallback
        query_terms = self._tokenize(query)
        doc_terms_list = [self._tokenize(r.text) for r in results]
        avg_len = sum(len(dt) for dt in doc_terms_list) / (len(doc_terms_list) or 1)

        bm25_scores = [self._bm25_score(query_terms, dt, avg_len) for dt in doc_terms_list]
        max_bm25 = max(bm25_scores) if bm25_scores and max(bm25_scores) > 0 else 1.0

        for i, r in enumerate(results):
            norm_bm25 = bm25_scores[i] / max_bm25
            # Weighted hybrid score: 60% semantic similarity + 40% lexical match
            combined = 0.60 * r.score + 0.40 * norm_bm25
            r.score = round(combined, 4)

        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
        return sorted_results[:top_n]


_default_reranker = None

def get_reranker() -> Reranker:
    global _default_reranker
    if _default_reranker is None:
        _default_reranker = HybridReranker()
    return _default_reranker

