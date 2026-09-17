from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # LLM Settings
    llm_provider: str = "openrouter"  # "openrouter", "gemini", or "ollama"
    llm_model: str = "gemini-2.5-flash"
    gemini_api_key: str = ""

    # OpenRouter Settings
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Ollama Settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:4b"

    # Embedding and Reranker
    embedding_model: str = "all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Storage Paths
    chroma_path: str = "./data/chroma"
    upload_path: str = "./data/uploads"
    seed_docs_path: str = "./data/seed_documents"
    sqlite_path: str = "./data/app.db"

    # Retrieval Settings
    retrieval_top_k: int = 10
    rerank_top_k: int = 4
    relevance_threshold: float = 0.20

    # Chunking Settings
    chunk_size: int = 650
    chunk_overlap: int = 80

    # Safety and Limits
    max_query_length: int = 2000
    max_upload_size_mb: int = 50

    def resolve_path(self, relative_path: str) -> Path:
        return Path(relative_path).resolve()


settings = Settings()

