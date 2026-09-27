from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models.chunk import ChunkRecord
from app.rag.types import RetrievedChunk
from tests.fakes import FakeEmbeddingProvider, FakeLLMProvider


@dataclass
class StaticVectorStore:
    results: list[RetrievedChunk]

    def add(self, records: list[ChunkRecord]) -> None:
        del records

    def delete_document(self, document_id: str) -> None:
        del document_id

    def keyword_search(
        self,
        terms: list[str],
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        del terms, top_k
        return []

    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        del embedding, where
        return self.results[:top_k]


def make_app(
    settings: Settings,
    score: float,
    llm: FakeLLMProvider | None = None,
) -> tuple[FastAPI, FakeLLMProvider]:
    provider = llm or FakeLLMProvider()
    result = RetrievedChunk(
        chunk_id="chunk-1",
        document_id="document-1",
        content="Partially related personal knowledge",
        score=score,
        metadata={"filename": "notes.md"},
    )
    app = create_app(
        settings,
        vector_store=StaticVectorStore([result]),
        embedding_provider_factory=lambda _: FakeEmbeddingProvider(),
        llm_provider_factory=lambda _: provider,
    )
    return app, provider


def test_chat_routes_partial_match_to_hybrid(
    test_settings: Settings,
) -> None:
    app, provider = make_app(test_settings, score=0.25)

    with TestClient(app) as client:
        response = client.post("/api/v1/chat", json={"message": "question"})

    assert response.status_code == 200
    assert response.json()["route"] == "hybrid"
    assert len(response.json()["citations"]) == 1
    assert any("暂未说明" in call[0].content for call in provider.all_messages)


def test_chat_routes_low_match_to_general(
    test_settings: Settings,
) -> None:
    app, provider = make_app(test_settings, score=0.1)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            json={"message": "question", "allow_general_fallback": True},
        )

    assert response.status_code == 200
    assert response.json()["route"] == "general"
    assert response.json()["citations"] == []
    assert "没有足够相关" in provider.last_messages[0].content


def test_chat_uses_configured_similarity_threshold(
    test_settings: Settings,
) -> None:
    app, _ = make_app(test_settings, score=0.4)

    with TestClient(app) as client:
        settings_response = client.put(
            "/api/v1/settings",
            json={"retrieval": {"similarity_threshold": 0.3}},
        )
        assert settings_response.status_code == 200
        response = client.post("/api/v1/chat", json={"message": "question"})

    assert response.status_code == 200
    assert response.json()["route"] == "knowledge"

