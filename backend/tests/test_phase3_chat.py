from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.fakes import FakeEmbeddingProvider, FakeLLMProvider, InMemoryVectorStore


def create_knowledge_base(client: TestClient, name: str = "Phase 3") -> str:
    response = client.post("/api/v1/knowledge", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def test_chat_uses_retrieved_personal_knowledge(
    client: TestClient,
    llm_provider: FakeLLMProvider,
) -> None:
    knowledge_base_id = create_knowledge_base(client)
    content = b"Reranker improves RAG result ordering after initial retrieval."
    client.post(
        "/api/v1/documents/upload",
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": ("rag.txt", content, "text/plain")},
    )

    response = client.post(
        "/api/v1/chat",
        json={"message": "Why is a reranker useful?", "top_k": 3},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "测试回答"
    assert body["route"] == "knowledge"
    assert body["conversation_id"]
    assert body["citations"][0]["filename"] == "rag.txt"
    assert any(
        "Reranker improves" in call[0].content for call in llm_provider.all_messages
    )


def test_chat_without_knowledge_uses_general_answer(
    client: TestClient,
    llm_provider: FakeLLMProvider,
) -> None:
    response = client.post(
        "/api/v1/chat",
        json={"message": "What is Python?", "allow_general_fallback": True},
    )

    assert response.status_code == 200
    assert response.json()["route"] == "general"
    assert response.json()["citations"] == []
    assert "通用回答" in llm_provider.last_messages[0].content


def test_chat_returns_503_when_llm_is_not_configured(
    test_settings: Settings,
    vector_store: InMemoryVectorStore,
) -> None:
    app: FastAPI = create_app(
        test_settings,
        vector_store=vector_store,
        embedding_provider_factory=lambda _: FakeEmbeddingProvider(),
    )
    with TestClient(app) as client:
        response = client.post("/api/v1/chat", json={"message": "hello"})

    assert response.status_code == 503
    assert response.json()["detail"] == "LLM provider is not configured."


def test_single_character_query_does_not_call_retrieval_or_llm(
    client: TestClient,
    llm_provider: FakeLLMProvider,
) -> None:
    llm_provider.last_messages = []

    response = client.post("/api/v1/chat", json={"message": "1"}).json()

    assert response["answer"].startswith("您好，我是中信银行信用卡智能客服")
    assert response["route"] == "guidance"
    assert response["citations"] == []
    assert llm_provider.last_messages == []
