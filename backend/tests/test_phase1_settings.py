from fastapi.testclient import TestClient


def test_settings_defaults_and_update(client: TestClient) -> None:
    initial = client.get("/api/v1/settings")
    assert initial.status_code == 200
    assert initial.json()["llm"]["enabled"] is False
    assert initial.json()["retrieval"]["top_k"] == 5

    updated = client.put(
        "/api/v1/settings",
        json={
            "llm": {
                "provider": "custom",
                "model": "local-model",
                "base_url": "http://127.0.0.1:11434/v1",
                "api_key": "secret",
                "enabled": True,
            },
            "retrieval": {
                "top_k": 8,
                "similarity_threshold": 0.65,
                "reranker_enabled": True,
            },
        },
    )

    assert updated.status_code == 200
    body = updated.json()
    assert body["llm"]["provider"] == "custom"
    assert body["llm"]["api_key_configured"] is True
    assert body["retrieval"] == {
        "top_k": 8,
        "similarity_threshold": 0.65,
        "reranker_enabled": True,
    }

    status_response = client.get("/api/v1/model/status")
    assert status_response.json()["providers"][0]["connected"] is True
