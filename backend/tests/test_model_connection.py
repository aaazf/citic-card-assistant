from fastapi.testclient import TestClient

from tests.fakes import FakeEmbeddingProvider, FakeLLMProvider


def test_llm_connection_test_uses_submitted_values(
    client: TestClient,
    monkeypatch,
) -> None:
    captured = {}

    def fake_builder(**kwargs):
        captured.update(kwargs)
        return FakeLLMProvider(content="OK")

    monkeypatch.setattr(
        "app.services.model_service.build_llm_provider_from_values",
        fake_builder,
    )

    response = client.post(
        "/api/v1/settings/test-model",
        json={
            "kind": "llm",
            "provider": "custom",
            "model": "test-model",
            "base_url": "http://localhost:9999/v1",
            "api_key": "test-key",
        },
    )

    assert response.status_code == 200
    assert response.json()["connected"] is True
    assert response.json()["message"] == "连接成功"
    assert captured["api_key"] == "test-key"


def test_embedding_connection_test(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.model_service.build_embedding_provider_from_values",
        lambda **_: FakeEmbeddingProvider(),
    )

    response = client.post(
        "/api/v1/settings/test-model",
        json={
            "kind": "embedding",
            "provider": "custom",
            "model": "embedding-model",
            "base_url": "http://localhost:9999/v1",
            "api_key": "test-key",
        },
    )

    assert response.status_code == 200
    assert response.json()["connected"] is True


def test_connection_test_returns_failure_without_raising(
    client: TestClient,
    monkeypatch,
) -> None:
    def failing_builder(**kwargs):
        del kwargs
        raise RuntimeError("upstream unavailable")

    monkeypatch.setattr(
        "app.services.model_service.build_llm_provider_from_values",
        failing_builder,
    )

    response = client.post(
        "/api/v1/settings/test-model",
        json={
            "kind": "llm",
            "provider": "custom",
            "model": "test-model",
            "base_url": "http://localhost:9999/v1",
        },
    )

    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert "upstream unavailable" in response.json()["message"]
