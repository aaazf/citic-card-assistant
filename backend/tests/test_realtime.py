from datetime import datetime

import pytest

from app.rag.realtime import build_realtime_system_prompt, detect_realtime_category
from app.rag.router import RelevanceRouter
from app.rag.types import RouteMode, StreamCompletedEvent, StreamDeltaEvent
from app.services.rag_service import RAGService
from app.services.retrieval_service import RetrievalService
from tests.fakes import FakeEmbeddingProvider, FakeLLMProvider, InMemoryVectorStore


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("今天星期几", "datetime"),
        ("现在几点了", "datetime"),
        ("国庆节放假安排出来了吗", "datetime"),
        ("北京明天天气怎么样", "weather"),
        ("今天空气质量好吗", "weather"),
        ("现在美元兑人民币汇率是多少", "exchange_rate"),
        ("LPR 最近降了吗", "market_rate"),
        ("最新存款基准利率是多少", "market_rate"),
        ("现在金价多少钱一克", "gold"),
        ("今天股市大盘怎么样", "stock"),
        ("95号汽油现在什么油价", "fuel"),
        ("今天有什么财经新闻", "news"),
        # 业务问题不能误判为实时信息
        ("信用卡年费怎么减免", None),
        ("账单日是几号", None),
        ("自动还款几点扣款", None),
        ("取现手续费是多少", None),
    ],
)
def test_detect_realtime_category(query: str, expected: str | None) -> None:
    category = detect_realtime_category(query)
    assert (category.key if category else None) == expected


def test_realtime_prompt_carries_server_time() -> None:
    category = detect_realtime_category("今天星期几")
    assert category is not None
    prompt = build_realtime_system_prompt(category, now=datetime(2026, 9, 22, 10, 30))

    assert "2026年09月22日" in prompt
    assert "星期二" in prompt
    assert "通用信息" in prompt
    assert "95558" in prompt


def build_service() -> tuple[RAGService, FakeLLMProvider]:
    llm = FakeLLMProvider()
    service = RAGService(
        retrieval_service=RetrievalService(FakeEmbeddingProvider(), InMemoryVectorStore()),
        llm_provider=llm,
        router=RelevanceRouter(0.5),
    )
    return service, llm


@pytest.mark.asyncio
async def test_realtime_query_gets_general_answer_by_default() -> None:
    service, llm = build_service()

    answer = await service.answer("今天星期几")

    assert answer.route is RouteMode.GENERAL
    assert answer.content == "测试回答"
    assert answer.suggest_human is False
    assert "通用信息" in llm.last_messages[0].content
    assert "95558" in llm.last_messages[0].content


@pytest.mark.asyncio
async def test_stream_realtime_query_flows_to_llm() -> None:
    service, _ = build_service()

    events = [event async for event in service.stream_answer("北京今天天气怎么样")]

    deltas = [event for event in events if isinstance(event, StreamDeltaEvent)]
    completed = [event for event in events if isinstance(event, StreamCompletedEvent)]
    assert "".join(event.delta for event in deltas) == "测试回答"
    assert completed and completed[0].route is RouteMode.GENERAL
    assert completed[0].suggest_human is False


@pytest.mark.asyncio
async def test_realtime_market_rate_takes_precedence_over_money_refusal() -> None:
    service, llm = build_service()

    answer = await service.answer("最近 LPR 利率有调整吗")

    assert answer.content == "测试回答"
    assert "市场利率" in llm.last_messages[0].content
