from fastapi.testclient import TestClient


def test_health_checks_database(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
        "database": "ok",
    }


def test_model_status_defaults_to_disconnected(client: TestClient) -> None:
    response = client.get("/api/v1/model/status")

    assert response.status_code == 200
    assert response.json()["providers"] == [
        {"kind": "llm", "connected": False, "provider": None, "model": None},
        {"kind": "embedding", "connected": False, "provider": None, "model": None},
    ]
