import pytest

from app.rag.local_reranker import LocalCrossEncoderReranker, _sigmoid
from app.rag.types import RetrievedChunk


def make_result(chunk_id: str, content: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc",
        content=content,
        score=score,
        metadata={},
    )


def test_sigmoid_bounds() -> None:
    assert _sigmoid(0.0) == 0.5
    assert 0.0 < _sigmoid(-10.0) < 0.01
    assert 0.99 < _sigmoid(10.0) < 1.0


@pytest.mark.asyncio
async def test_local_reranker_orders_by_model_score(tmp_path, monkeypatch) -> None:
    reranker = LocalCrossEncoderReranker(tmp_path)
    scores = {(q, c): score for (q, c), score in [
        (("年费", "完全无关的内容"), 0.05),
        (("年费", "年费减免规则说明"), 0.93),
        (("年费", "账单日说明"), 0.30),
    ]}

    def fake_score(pairs):
        return [scores[pair] for pair in pairs]

    monkeypatch.setattr(reranker, "_score", fake_score)
    results = [
        make_result("c1", "完全无关的内容", 0.9),
        make_result("c2", "年费减免规则说明", 0.4),
        make_result("c3", "账单日说明", 0.7),
    ]

    reranked = await reranker.rerank("年费", results, 2)

    assert [item.chunk_id for item in reranked] == ["c2", "c3"]
    assert reranked[0].score == pytest.approx(0.93)
    assert reranked[0].metadata is results[1].metadata


@pytest.mark.asyncio
async def test_local_reranker_empty_results(tmp_path) -> None:
    reranker = LocalCrossEncoderReranker(tmp_path)

    assert await reranker.rerank("q", [], 5) == []
