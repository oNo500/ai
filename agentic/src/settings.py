"""Application settings using pydantic-settings."""

from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ai-agent-service"
    debug: bool = False
    openai_api_key: str = "sk-placeholder"
    openai_model: str = "gpt-4o-mini"
    redis_url: str = "redis://localhost:6379/0"
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "default"
    # Rate limiting
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60
    # RAG / pgvector
    postgres_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/agentic"
    rag_collection: str = "rag_documents"
    # Mem0 long-term memory backend
    mem0_vector_store_provider: str = "memory"  # "memory" | "qdrant"
    mem0_qdrant_url: str = "http://localhost:6333"
    mem0_qdrant_collection: str = "mem0"

    def build_mem0_config(self) -> dict[str, Any] | None:
        if self.mem0_vector_store_provider == "memory":
            return None
        if self.mem0_vector_store_provider == "qdrant":
            return {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "url": self.mem0_qdrant_url,
                        "collection_name": self.mem0_qdrant_collection,
                        "embedding_model_dims": 1536,
                    },
                }
            }
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
