import pytest
from backend.app.retrieval.vector_store import SearchResult
from backend.app.retrieval.reranker import HybridReranker

def test_hybrid_reranker():
    reranker = HybridReranker()
    results = [
        SearchResult(
            chunk_id="c1",
            document_id="d1",
            document_name="doc1.pdf",
            page_number=1,
            section="Section 1",
            text="The quick brown fox jumps over the lazy dog.",
            score=0.5
        ),
        SearchResult(
            chunk_id="c2",
            document_id="d2",
            document_name="doc2.pdf",
            page_number=2,
            section="Section 2",
            text="Attention mechanisms calculate dot product similarities between query and key vectors.",
            score=0.4
        )
    ]

    reranked = reranker.rerank("attention mechanisms and query key vectors", results, top_n=2)
    assert len(reranked) == 2
    # The second document matches the query terms much better
    assert reranked[0].chunk_id == "c2"
    assert reranked[0].score > reranked[1].score

