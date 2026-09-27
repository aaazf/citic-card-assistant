from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.fakes import FakeEmbeddingProvider, InMemoryVectorStore


def test_agent_search_returns_structured_results_without_llm(
    test_settings: Settings,
    vector_store: InMemoryVectorStore,
) -> None:
    app: FastAPI = create_app(
        test_settings,
        vector_store=vector_store,
        embedding_provider_factory=lambda _: FakeEmbeddingProvider(),
    )
    with TestClient(app) as client:
        knowledge = client.post("/api/v1/knowledge", json={"name": "Agent"}).json()
        client.post(
            "/api/v1/documents/upload",
            data={"knowledge_base_id": knowledge["id"]},
            files={"file": ("agent.txt", b"structured retrieval content", "text/plain")},
        )

        response = client.post(
            "/api/v1/knowledge/search",
            json={"query": "retrieval", "top_k": 5},
        )
        conversations = client.get("/api/v1/conversations").json()

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "retrieval"
    assert body["results"][0]["content"] == "structured retrieval content"
    assert body["results"][0]["metadata"]["filename"] == "agent.txt"
    assert body["results"][0]["metadata"]["chunk_id"]
    assert conversations == []


def test_agent_search_returns_503_without_embedding_provider(
    test_settings: Settings,
    vector_store: InMemoryVectorStore,
) -> None:
    app = create_app(test_settings, vector_store=vector_store)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/knowledge/search",
            json={"query": "retrieval"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Embedding provider is not configured."
