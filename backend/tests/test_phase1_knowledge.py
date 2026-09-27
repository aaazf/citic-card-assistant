from fastapi.testclient import TestClient


def test_knowledge_base_crud(client: TestClient) -> None:
    created = client.post(
        "/api/v1/knowledge",
        json={"name": "AI技术", "description": "AI-related notes"},
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["name"] == "AI技术"

    listed = client.get("/api/v1/knowledge")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [payload["id"]]

    deleted = client.delete(f"/api/v1/knowledge/{payload['id']}")
    assert deleted.status_code == 200
    assert client.get("/api/v1/knowledge").json() == []


def test_duplicate_knowledge_base_returns_conflict(client: TestClient) -> None:
    payload = {"name": "Python"}
    assert client.post("/api/v1/knowledge", json=payload).status_code == 201

    duplicate = client.post("/api/v1/knowledge", json=payload)

    assert duplicate.status_code == 409


def test_delete_missing_knowledge_base_returns_not_found(client: TestClient) -> None:
    response = client.delete("/api/v1/knowledge/missing")

    assert response.status_code == 404
