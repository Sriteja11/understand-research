from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from pydantic import BaseModel, Field
import chromadb
from backend.app.config import settings


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section: str
    text: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VectorStore(ABC):
    @abstractmethod
    def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> None:
        pass

    @abstractmethod
    def count(self) -> int:
        pass

    @abstractmethod
    def list_indexed_document_names(self) -> Set[str]:
        pass


class ChromaVectorStore(VectorStore):
    """Persistent ChromaDB implementation of VectorStore."""

    def __init__(self, persist_dir: Optional[str] = None, collection_name: str = "research_documents"):
        target_path = Path(persist_dir or settings.chroma_path).resolve()
        target_path.mkdir(parents=True, exist_ok=True)
        self.persist_dir = str(target_path)
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        if not ids:
            return
        # Chroma expects primitive values in metadata
        cleaned_metadatas = []
        for meta in metadatas:
            cleaned = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    cleaned[k] = v
                else:
                    cleaned[k] = str(v)
            cleaned_metadatas.append(cleaned)

        # Batch upsert to Chroma
        batch_size = 200
        for i in range(0, len(ids), batch_size):
            end = i + batch_size
            self.collection.upsert(
                ids=ids[i:end],
                embeddings=embeddings[i:end],
                documents=documents[i:end],
                metadatas=cleaned_metadatas[i:end]
            )

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        total_items = self.count()
        if total_items == 0:
            return []

        actual_k = min(top_k, total_items)
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": actual_k,
            "include": ["documents", "metadatas", "distances"]
        }
        if filter_metadata:
            kwargs["where"] = filter_metadata

        query_res = self.collection.query(**kwargs)
        results: List[SearchResult] = []

        ids = query_res.get("ids", [[]])[0]
        docs = query_res.get("documents", [[]])[0]
        metas = query_res.get("metadatas", [[]])[0]
        distances = query_res.get("distances", [[]])[0]

        for i in range(len(ids)):
            meta = metas[i] if i < len(metas) else {}
            dist = distances[i] if i < len(distances) else 1.0
            # With cosine space in Chroma, distance = 1 - cosine_similarity
            similarity = max(0.0, 1.0 - float(dist))

            results.append(
                SearchResult(
                    chunk_id=ids[i],
                    document_id=str(meta.get("document_id", "")),
                    document_name=str(meta.get("document_name", "")),
                    page_number=int(meta.get("page_number", 1)),
                    section=str(meta.get("section", "General")),
                    text=docs[i],
                    score=round(similarity, 4),
                    metadata=meta
                )
            )

        return results

    def delete_document(self, document_id: str) -> None:
        try:
            self.collection.delete(where={"document_id": document_id})
        except Exception:
            pass

    def count(self) -> int:
        return self.collection.count()

    def list_indexed_document_names(self) -> Set[str]:
        total = self.count()
        if total == 0:
            return set()
        data = self.collection.get(include=["metadatas"])
        names: Set[str] = set()
        for meta in data.get("metadatas", []):
            if meta and "document_name" in meta:
                names.add(meta["document_name"])
        return names


_default_vector_store = None

def get_vector_store() -> VectorStore:
    global _default_vector_store
    if _default_vector_store is None:
        _default_vector_store = ChromaVectorStore()
    return _default_vector_store

