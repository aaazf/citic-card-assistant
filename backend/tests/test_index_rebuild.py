from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.fakes import FakeEmbeddingProvider, FakeLLMProvider


def create_client(settings: Settings, llm_provider: FakeLLMProvider) -> TestClient:
    app = create_app(
        settings,
        embedding_provider_factory=lambda _: FakeEmbeddingProvider(),
        llm_provider_factory=lambda _: llm_provider,
    )
    return TestClient(app)


def configure_embedding(client: TestClient, model: str = "embed-v1") -> None:
    response = client.put(
        "/api/v1/settings",
        json={
            "embedding": {
                "provider": "custom",
                "model": model,
                "base_url": "http://localhost:9999/v1",
                "api_key": "test-key",
                "enabled": True,
            }
        },
    )
    assert response.status_code == 200


def test_rebuild_creates_separate_index_and_activates_it(
    test_settings: Settings,
    llm_provider: FakeLLMProvider,
) -> None:
    with create_client(test_settings, llm_provider) as client:
        configure_embedding(client)
        knowledge_base_id = client.post(
            "/api/v1/knowledge",
            json={"name": "Index rebuild"},
        ).json()["id"]
        upload = client.post(
            "/api/v1/documents/upload",
            data={"knowledge_base_id": knowledge_base_id},
            files={"file": ("notes.txt", b"Python RAG evidence", "text/plain")},
        )
        assert upload.status_code == 202

        initial = client.get("/api/v1/indexes").json()
        assert initial["active_version_id"] is not None
        legacy = initial["versions"][0]
        assert legacy["collection_name"] == "knowledge_chunks"
        assert legacy["is_active"] is True

        rebuild = client.post("/api/v1/indexes/rebuild")
        assert rebuild.status_code == 202

        indexes = client.get("/api/v1/indexes").json()
        new_version = next(
            version
            for version in indexes["versions"]
            if version["collection_name"] != "knowledge_chunks"
        )
        assert new_version["status"] == "ready"
        assert new_version["dimension"] == 4
        assert new_version["total_chunks"] > 0
        assert new_version["is_active"] is False

        activated = client.post(f"/api/v1/indexes/{new_version['id']}/activate")
        assert activated.status_code == 200
        assert activated.json()["is_active"] is True

        answer = client.post(
            "/api/v1/chat",
            json={"message": "What is Python?"},
        )
        assert answer.status_code == 200
        assert answer.json()["route"] == "knowledge"
        assert answer.json()["citations"]


def test_active_index_rejects_mismatched_embedding_model(
    test_settings: Settings,
    llm_provider: FakeLLMProvider,
) -> None:
    with create_client(test_settings, llm_provider) as client:
        configure_embedding(client, model="embed-v1")
        knowledge_base_id = client.post(
            "/api/v1/knowledge",
            json={"name": "Mismatch"},
        ).json()["id"]
        client.post(
            "/api/v1/documents/upload",
            data={"knowledge_base_id": knowledge_base_id},
            files={"file": ("notes.txt", b"Python RAG evidence", "text/plain")},
        )
        client.post("/api/v1/indexes/rebuild")
        indexes = client.get("/api/v1/indexes").json()
        version = next(
            item
            for item in indexes["versions"]
            if item["collection_name"] != "knowledge_chunks"
        )
        client.post(f"/api/v1/indexes/{version['id']}/activate")

        configure_embedding(client, model="embed-v2")
        answer = client.post(
            "/api/v1/chat",
            json={"message": "What is Python?"},
        )

        assert answer.status_code == 409
        assert "不一致" in answer.json()["detail"]
