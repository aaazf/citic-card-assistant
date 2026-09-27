import asyncio

import pytest

from app.providers.base import ChatMessage, ChatResult
from app.rag.query_rewrite import QueryRewriter
from app.rag.router import RelevanceRouter
from app.rag.types import RouteMode
from app.services.rag_service import RAGService
from app.services.retrieval_service import RetrievalService
from tests.fakes import FakeEmbeddingProvider, InMemoryVectorStore
from tests.test_retrieval_core import make_record


class RewriteLLM:
    def __init__(self, rewritten: str = "信用卡额度提升需要什么条件") -> None:
        self.rewritten = rewritten
        self.last_messages: list[ChatMessage] = []

    async def chat(self, messages: list[ChatMessage]) -> ChatResult:
        self.last_messages = messages
        return ChatResult(content=self.rewritten, model="stub")


class SlowLLM:
    async def chat(self, messages: list[ChatMessage]) -> ChatResult:
        del messages
        await asyncio.sleep(5)
        return ChatResult(content="太慢了", model="stub")


class FailingLLM:
    async def chat(self, messages: list[ChatMessage]) -> ChatResult:
        del messages
        raise RuntimeError("llm down")


HISTORY = [ChatMessage(role="user", content="信用卡额度怎么提升")]


class TestQueryRewriter:
    @pytest.mark.asyncio
    async def test_no_history_returns_original(self) -> None:
        llm = RewriteLLM()
        rewriter = QueryRewriter(llm)  # type: ignore[arg-type]

        assert await rewriter.rewrite("需要什么条件") == "需要什么条件"
        assert llm.last_messages == []

    @pytest.mark.asyncio
    async def test_rewrites_with_history(self) -> None:
        llm = RewriteLLM()
        rewriter = QueryRewriter(llm)  # type: ignore[arg-type]

        result = await rewriter.rewrite("需要什么条件", HISTORY)

        assert result == "信用卡额度提升需要什么条件"
        assert "信用卡额度怎么提升" in llm.last_messages[-1].content

    @pytest.mark.asyncio
    async def test_failure_falls_back_to_original(self) -> None:
        rewriter = QueryRewriter(FailingLLM())  # type: ignore[arg-type]

        assert await rewriter.rewrite("需要什么条件", HISTORY) == "需要什么条件"

    @pytest.mark.asyncio
    async def test_timeout_falls_back_to_original(self) -> None:
        rewriter = QueryRewriter(SlowLLM(), timeout_seconds=0.05)  # type: ignore[arg-type]

        assert await rewriter.rewrite("需要什么条件", HISTORY) == "需要什么条件"

    @pytest.mark.asyncio
    async def test_empty_or_oversized_rewrite_falls_back(self) -> None:
        rewriter = QueryRewriter(RewriteLLM('""'))  # type: ignore[arg-type]

        assert await rewriter.rewrite("需要什么条件", HISTORY) == "需要什么条件"


class RecordingEmbeddingProvider(FakeEmbeddingProvider):
    def __init__(self) -> None:
        self.embedded_texts: list[str] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.embedded_texts.extend(texts)
        return await super().embed(texts)


class AnsweringLLM:
    def __init__(self) -> None:
        self.last_messages: list[ChatMessage] = []

    async def chat(self, messages: list[ChatMessage]) -> ChatResult:
        self.last_messages = messages
        return ChatResult(content="回答", model="stub")


@pytest.mark.asyncio
async def test_rag_retrieves_with_rewritten_query_but_answers_original() -> None:
    store = InMemoryVectorStore()
    store.add([make_record("c1", "信用卡额度提升需要保持良好还款记录并满足用卡时长要求。")])
    embedding = RecordingEmbeddingProvider()
    llm = AnsweringLLM()
    rewriter_llm = RewriteLLM("信用卡额度提升需要什么条件")
    service = RAGService(
        retrieval_service=RetrievalService(embedding, store),
        llm_provider=llm,  # type: ignore[arg-type]
        router=RelevanceRouter(0.5),
        query_rewriter=QueryRewriter(rewriter_llm),  # type: ignore[arg-type]
    )

    answer = await service.answer("需要什么条件", history=HISTORY)

    assert answer.route is RouteMode.KNOWLEDGE
    assert embedding.embedded_texts[0] == "信用卡额度提升需要什么条件"
    assert llm.last_messages[-1].content == "需要什么条件"
