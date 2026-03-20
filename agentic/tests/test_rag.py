"""RAG tool unit tests (TDD — RED first)."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestVectorStore:
    async def test_search_returns_list_of_strings(self):
        from src.agent.tools.rag import VectorStore

        mock_store = MagicMock()
        mock_store.asimilarity_search = AsyncMock(
            return_value=[
                MagicMock(page_content="chunk A"),
                MagicMock(page_content="chunk B"),
            ]
        )

        vs = VectorStore.__new__(VectorStore)
        vs._store = mock_store

        results = await vs.search("what is RAG?", k=2)
        assert results == ["chunk A", "chunk B"]

    async def test_ingest_calls_add_documents(self):
        from src.agent.tools.rag import VectorStore

        mock_store = MagicMock()
        mock_store.aadd_texts = AsyncMock(return_value=["id1", "id2"])

        vs = VectorStore.__new__(VectorStore)
        vs._store = mock_store

        ids = await vs.ingest(["text one", "text two"])
        mock_store.aadd_texts.assert_called_once_with(["text one", "text two"])
        assert ids == ["id1", "id2"]

    def test_vector_store_init_uses_settings(self):
        from src.agent.tools.rag import VectorStore

        mock_pg_store = MagicMock()

        with (
            patch("src.agent.tools.rag.PGVector") as mock_pgvector,
            patch("src.agent.tools.rag.OpenAIEmbeddings"),
        ):
            mock_pgvector.return_value = mock_pg_store
            vs = VectorStore()

        mock_pgvector.assert_called_once()
        assert vs._store is mock_pg_store


class TestRagSearchTool:
    async def test_rag_search_tool_calls_vector_store(self):
        from src.agent.tools.rag import make_rag_search_tool

        mock_vs = MagicMock()
        mock_vs.search = AsyncMock(return_value=["result one", "result two"])

        tool = make_rag_search_tool(mock_vs)
        result = await tool.arun("what is LangGraph?")

        mock_vs.search.assert_called_once_with("what is LangGraph?", k=5)
        assert "result one" in result
        assert "result two" in result

    def test_rag_search_tool_has_correct_name(self):
        from src.agent.tools.rag import make_rag_search_tool

        mock_vs = MagicMock()
        tool = make_rag_search_tool(mock_vs)
        assert tool.name == "rag_search"


class TestSettingsRag:
    def test_settings_has_postgres_url(self):
        from src.settings import Settings

        s = Settings()
        assert hasattr(s, "postgres_url")

    def test_settings_has_rag_collection(self):
        from src.settings import Settings

        s = Settings()
        assert hasattr(s, "rag_collection")
        assert s.rag_collection == "rag_documents"


class TestIngestEndpoint:
    async def test_ingest_endpoint_returns_ids(self):
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        from src.main import app

        mock_vs = MagicMock()
        mock_vs.ingest = AsyncMock(return_value=["id1", "id2"])

        with patch("src.agent.tools.rag.VectorStore", return_value=mock_vs):
            with TestClient(app) as client:
                resp = client.post(
                    "/rag/ingest",
                    json={"texts": ["hello world", "foo bar"]},
                )

        assert resp.status_code == 200
        assert resp.json()["ids"] == ["id1", "id2"]
