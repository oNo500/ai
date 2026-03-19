"""RAG tool: vector search via pgvector."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from src.settings import get_settings

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool


class VectorStore:
    def __init__(self) -> None:
        settings = get_settings()
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key,
        )
        self._store = PGVector(
            embeddings=embeddings,
            collection_name=settings.rag_collection,
            connection=settings.postgres_url,
            use_jsonb=True,
        )

    async def search(self, query: str, *, k: int = 5) -> list[str]:
        docs = await self._store.asimilarity_search(query, k=k)
        return [doc.page_content for doc in docs]

    async def ingest(self, texts: list[str]) -> list[Any]:
        return await self._store.aadd_texts(texts)


def make_rag_search_tool(vs: VectorStore) -> BaseTool:
    @tool
    async def rag_search(query: str) -> str:
        """Search the knowledge base for relevant documents."""
        chunks = await vs.search(query, k=5)
        if not chunks:
            return "No relevant documents found."
        return "\n\n---\n\n".join(chunks)

    return rag_search
