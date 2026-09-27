from app.rag.router import RelevanceRouter
from app.rag.types import RetrievedChunk, RouteMode


def chunk(score: float, identifier: str = "chunk") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=identifier,
        document_id="document",
        content="content",
        score=score,
        metadata={"filename": "notes.md"},
    )


def test_router_selects_knowledge_hybrid_and_general() -> None:
    router = RelevanceRouter(similarity_threshold=0.5)

    knowledge = router.decide("q", [chunk(0.8, "knowledge")])
    hybrid = router.decide("q", [chunk(0.4, "hybrid")])
    general = router.decide("q", [chunk(0.1, "general")])

    assert knowledge.route is RouteMode.KNOWLEDGE
    assert [item.chunk_id for item in knowledge.results] == ["knowledge"]
    assert hybrid.route is RouteMode.HYBRID
    assert [item.chunk_id for item in hybrid.results] == ["hybrid"]
    assert general.route is RouteMode.GENERAL
    assert general.results == []
