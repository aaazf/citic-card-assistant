from app.services.knowledge_service import KnowledgeSearchService


class KnowledgeMCPAdapter:
    """Thin adapter reserved for a future MCP server implementation."""

    def __init__(self, service: KnowledgeSearchService) -> None:
        self.service = service

    async def search_knowledge(self, query: str, top_k: int = 5) -> dict[str, object]:
        results = await self.service.search(query, top_k)
        return {
            "query": query,
            "results": [result.model_dump() for result in results],
        }
