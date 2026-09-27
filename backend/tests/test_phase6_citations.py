from fastapi.testclient import TestClient

from tests.fakes import FakeLLMProvider


def test_chat_citation_can_open_original_chunk(
    client: TestClient,
    llm_provider: FakeLLMProvider,
) -> None:
    llm_provider.content = "回答内容 [1]"
    knowledge = client.post("/api/v1/knowledge", json={"name": "Citation"}).json()
    uploaded = client.post(
        "/api/v1/documents/upload",
        data={"knowledge_base_id": knowledge["id"]},
        files={"file": ("citation.txt", b"original source text", "text/plain")},
    ).json()

    chat = client.post("/api/v1/chat", json={"message": "source?"}).json()
    citation = chat["citations"][0]
    chunk = client.get(
        f"/api/v1/documents/{uploaded['id']}/chunks/{citation['chunk_id']}"
    )

    assert chunk.status_code == 200
    assert chunk.json()["document_id"] == uploaded["id"]
    assert chunk.json()["content"] == "original source text"
    assert "[1]" in chat["answer"]


def test_missing_chunk_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/documents/missing/chunks/missing")

    assert response.status_code == 404


def test_legacy_nested_citation_is_accepted() -> None:
    from app.schemas.chat import Citation

    citation = Citation.model_validate(
        {
            "document_id": "document",
            "chunk_id": "chunk",
            "content": "text",
            "score": 0.8,
            "metadata": {"filename": "resume.pdf", "page": 2},
        }
    )

    assert citation.filename == "resume.pdf"
    assert citation.page == 2
