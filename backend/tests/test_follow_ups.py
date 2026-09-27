import pytest

from app.providers.base import ChatResult
from app.rag.follow_ups import FollowUpSuggester
from app.rag.router import RelevanceRouter
from app.rag.types import RouteMode, StreamCompletedEvent
from app.services.rag_service import RAGService
from app.services.retrieval_service import RetrievalService
from tests.fakes import FakeEmbeddingProvider, FakeLLMProvider, InMemoryVectorStore


class StubFollowUpLLM:
    def __init__(self, content: str) -> None:
        self.content = content

    async def chat(self, messages: object) -> ChatResult:
        del messages
        return ChatResult(content=self.content, model="stub")


class FailingLLM:
    async def chat(self, messages: object) -> ChatResult:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_suggester_parses_and_cleans_lines() -> None:
    overlong = "太长" + "长" * 60
    suggester = FollowUpSuggester(
        StubFollowUpLLM(  # type: ignore[arg-type]
            "1. 刷几次卡可以免年费？\n"
            "2. 逾期一天会上征信吗\n"
            "- 如何提升固定额度？\n\n" + overlong
        )
    )

    suggestions = await suggester.suggest("年费怎么减免", "首年免年费……")

    assert suggestions == ["刷几次卡可以免年费？", "逾期一天会上征信吗", "如何提升固定额度？"]


@pytest.mark.asyncio
async def test_suggester_falls_back_to_empty_on_failure() -> None:
    suggester = FollowUpSuggester(FailingLLM())  # type: ignore[arg-type]

    assert await suggester.suggest("q", "a") == []


class StubSuggester:
    def __init__(self, items: list[str]) -> None:
        self.items = items
        self.calls = 0

    async def suggest(self, query: str, answer: str) -> list[str]:
        del query, answer
        self.calls += 1
        return self.items


def build_service(suggester: StubSuggester) -> tuple[RAGService, InMemoryVectorStore]:
    store = InMemoryVectorStore()
    service = RAGService(
        retrieval_service=RetrievalService(FakeEmbeddingProvider(), store),
        llm_provider=FakeLLMProvider(),
        router=RelevanceRouter(0.5),
        follow_up_suggester=suggester,  # type: ignore[arg-type]
    )
    return service, store


@pytest.mark.asyncio
async def test_knowledge_answer_carries_follow_ups() -> None:
    service, store = build_service(StubSuggester(["如何提升额度？"]))
    from app.models.chunk import ChunkRecord

    store.add(
        [
            ChunkRecord(
                id="c1",
                document_id="d1",
                knowledge_base_id="kb-1",
                content="信用卡年费可以通过刷卡次数减免",
                metadata={"filename": "fee.txt"},
            )
        ]
    )

    answer = await service.answer("年费怎么减免")

    assert answer.route is RouteMode.KNOWLEDGE
    assert answer.follow_ups == ["如何提升额度？"]


@pytest.mark.asyncio
async def test_general_answer_skips_follow_ups() -> None:
    suggester = StubSuggester(["不应出现"])
    service, _ = build_service(suggester)

    answer = await service.answer("今天星期几")

    assert answer.route is RouteMode.GENERAL
    assert answer.follow_ups == []
    assert suggester.calls == 0


@pytest.mark.asyncio
async def test_stream_completed_event_carries_follow_ups() -> None:
    service, store = build_service(StubSuggester(["如何提升额度？"]))
    from app.models.chunk import ChunkRecord

    store.add(
        [
            ChunkRecord(
                id="c1",
                document_id="d1",
                knowledge_base_id="kb-1",
                content="信用卡年费可以通过刷卡次数减免",
                metadata={"filename": "fee.txt"},
            )
        ]
    )

    events = [event async for event in service.stream_answer("年费怎么减免")]

    completed = [event for event in events if isinstance(event, StreamCompletedEvent)]
    assert completed and completed[0].follow_ups == ["如何提升额度？"]
