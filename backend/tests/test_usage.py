from fastapi.testclient import TestClient

from tests.fakes import FakeLLMProvider


def test_usage_summary_is_empty_initially(client: TestClient) -> None:
    summary = client.get("/api/v1/usage/summary").json()

    assert summary["total"] == {
        "calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cost_cny": 0.0,
    }
    assert summary["recent"] == []
    assert summary["pricing"]["input_per_million"] > 0


def test_chat_tokens_are_recorded_and_priced(
    client: TestClient,
    llm_provider: FakeLLMProvider,
) -> None:
    llm_provider.prompt_tokens = 1_000_000
    llm_provider.completion_tokens = 500_000

    client.post(
        "/api/v1/chat",
        json={"message": "What is Python?", "allow_general_fallback": True},
    )

    summary = client.get("/api/v1/usage/summary").json()
    assert summary["total"]["calls"] == 1
    assert summary["total"]["prompt_tokens"] == 1_000_000
    assert summary["total"]["completion_tokens"] == 500_000
    # 默认单价：输入 2 元/百万，输出 8 元/百万 -> 2 + 4 = 6 元
    assert summary["total"]["cost_cny"] == 6.0
    assert summary["recent"][0]["source"] == "chat"
    assert summary["recent"][0]["model"] == "fake-model"


def test_pricing_update_changes_cost(client: TestClient, llm_provider: FakeLLMProvider) -> None:
    llm_provider.prompt_tokens = 1_000_000
    llm_provider.completion_tokens = 0
    client.put("/api/v1/settings", json={"pricing": {"input_per_million": 4.0}})
    client.post(
        "/api/v1/chat",
        json={"message": "hello world", "allow_general_fallback": True},
    )

    summary = client.get("/api/v1/usage/summary").json()

    assert summary["pricing"]["input_per_million"] == 4.0
    assert summary["total"]["cost_cny"] == 4.0


def test_eval_purpose_is_recorded_separately(
    client: TestClient,
    llm_provider: FakeLLMProvider,
) -> None:
    llm_provider.prompt_tokens = 10
    llm_provider.completion_tokens = 5

    client.post(
        "/api/v1/chat",
        json={"message": "eval case", "purpose": "eval", "allow_general_fallback": True},
    )

    summary = client.get("/api/v1/usage/summary").json()
    assert summary["recent"][0]["source"] == "eval"


def test_no_record_when_provider_omits_usage(client: TestClient) -> None:
    client.post(
        "/api/v1/chat",
        json={"message": "What is Python?", "allow_general_fallback": True},
    )

    summary = client.get("/api/v1/usage/summary").json()
    assert summary["total"]["calls"] == 0
