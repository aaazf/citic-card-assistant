import pytest

from app.providers.base import ChatResult
from app.rag.query_rewrite import QueryRewriter  # noqa: F401  (ensures wiring import path)
from app.rag.router import RelevanceRouter
from app.rag.types import (
    RouteMode,
    StreamCompletedEvent,
    StreamDeltaEvent,
)
from app.services.rag_service import MONEY_REFUSAL_ANSWER, STRICT_NO_EVIDENCE_ANSWER, RAGService
from app.services.retrieval_service import RetrievalService
from tests.fakes import FakeEmbeddingProvider, InMemoryVectorStore


class AnsweringLLM:
    async def chat(self, messages: object) -> ChatResult:
        del messages
        return ChatResult(content="通用回答内容", model="stub")

    async def stream_chat(self, messages: object):
        del messages
        yield "通用回答内容"


def build_service() -> RAGService:
    return RAGService(
        retrieval_service=RetrievalService(FakeEmbeddingProvider(), InMemoryVectorStore()),
        llm_provider=AnsweringLLM(),  # type: ignore[arg-type]
        router=RelevanceRouter(0.5),
    )


@pytest.mark.asyncio
async def test_money_query_without_evidence_is_refused_with_escalation() -> None:
    answer = await build_service().answer("取现手续费是多少")

    assert answer.route is RouteMode.GENERAL
    assert answer.content == MONEY_REFUSAL_ANSWER
    assert answer.citations == []
    assert answer.suggest_human is True


@pytest.mark.asyncio
async def test_non_money_general_query_is_refused_by_default() -> None:
    answer = await build_service().answer("如何制定一周的健身计划")

    assert answer.route is RouteMode.GENERAL
    assert answer.content == STRICT_NO_EVIDENCE_ANSWER
    assert answer.citations == []
    assert answer.suggest_human is True


@pytest.mark.asyncio
async def test_general_query_answers_when_explicitly_allowed() -> None:
    answer = await build_service().answer("如何制定一周的健身计划", allow_general=True)

    assert answer.route is RouteMode.GENERAL
    assert answer.content == "通用回答内容"
    assert answer.suggest_human is False


@pytest.mark.asyncio
async def test_strict_scope_refusal_suggests_human() -> None:
    answer = await build_service().answer("介绍信用卡产品", strict_scope=True)

    assert answer.suggest_human is True


@pytest.mark.asyncio
async def test_stream_money_refusal_carries_escalation_flag() -> None:
    events = [event async for event in build_service().stream_answer("年费怎么收")]

    deltas = [event for event in events if isinstance(event, StreamDeltaEvent)]
    completed = [event for event in events if isinstance(event, StreamCompletedEvent)]
    assert deltas and deltas[0].delta == MONEY_REFUSAL_ANSWER
    assert completed and completed[0].suggest_human is True
