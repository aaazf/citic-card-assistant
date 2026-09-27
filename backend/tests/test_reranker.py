import pytest

from app.rag.reranker import LLMReranker
from app.rag.types import RetrievedChunk
from tests.fakes import FakeLLMProvider


def candidate(identifier: str, score: float = 0.4) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=identifier,
        document_id="document",
        content=f"content {identifier}",
        score=score,
        metadata={"filename": f"{identifier}.md"},
    )


@pytest.mark.asyncio
async def test_llm_reranker_sorts_and_replaces_vector_scores() -> None:
    provider = FakeLLMProvider(
        '```json\n[{"index":1,"score":0.1},{"index":2,"score":0.9},'
        '{"index":3,"score":0.5}]\n```'
    )
    reranker = LLMReranker(provider)

    results = await reranker.rerank(
        "question",
        [candidate("one"), candidate("two"), candidate("three")],
        top_k=3,
    )

    assert [item.chunk_id for item in results] == ["two", "three", "one"]
    assert [item.score for item in results] == [0.9, 0.5, 0.1]


@pytest.mark.asyncio
async def test_llm_reranker_falls_back_on_invalid_output() -> None:
    provider = FakeLLMProvider("not json")
    reranker = LLMReranker(provider)
    original = [candidate("one"), candidate("two")]

    results = await reranker.rerank("question", original, top_k=2)

    assert results == original
