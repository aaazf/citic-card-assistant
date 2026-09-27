import pytest

from app.mcp.adapter import KnowledgeMCPAdapter
from app.schemas.search import KnowledgeSearchResult


class StubKnowledgeSearchService:
    async def search(self, query: str, top_k: int) -> list[KnowledgeSearchResult]:
        return [
            KnowledgeSearchResult(
                document_id="document",
                content=f"{query}:{top_k}",
                score=0.9,
                metadata={"filename": "notes.md", "chunk_id": "chunk"},
            )
        ]


@pytest.mark.asyncio
async def test_mcp_adapter_reuses_structured_search_service() -> None:
    adapter = KnowledgeMCPAdapter(StubKnowledgeSearchService())  # type: ignore[arg-type]

    result = await adapter.search_knowledge("query", top_k=3)

    assert result["query"] == "query"
    assert result["results"][0]["metadata"]["filename"] == "notes.md"
