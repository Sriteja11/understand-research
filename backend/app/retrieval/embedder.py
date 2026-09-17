from abc import ABC, abstractmethod
from typing import List
from sentence_transformers import SentenceTransformer
from backend.app.config import settings

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        pass


class LocalSentenceTransformerEmbedder(EmbeddingProvider):
    """Local embedding model provider running on sentence-transformers."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.embedding_model
        # Load local model
        self.model = SentenceTransformer(self.model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()


_default_embedder = None

def get_embedding_provider() -> EmbeddingProvider:
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = LocalSentenceTransformerEmbedder()
    return _default_embedder

