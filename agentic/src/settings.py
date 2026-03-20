"""Application settings using pydantic-settings."""

import os
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_ENV = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
_LOCAL_ENV = os.path.join(os.path.dirname(__file__), "..", ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[_ROOT_ENV, _LOCAL_ENV],
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
    # RAG / pgvector — reads DATABASE_URL from root .env, accepts postgres:// or postgresql+psycopg://
    postgres_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/agentic",
        validation_alias="DATABASE_URL",
    )

    @field_validator("postgres_url", mode="before")
    @classmethod
    def normalize_postgres_scheme(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        return v
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
