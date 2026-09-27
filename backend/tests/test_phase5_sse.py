import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.fakes import FakeEmbeddingProvider, InMemoryVectorStore


def parse_sse(body: str) -> list[dict[str, object]]:
    events = []
    for block in body.strip().split("\n\n"):
        data_line = next(line for line in block.splitlines() if line.startswith("data: "))
        events.append(json.loads(data_line.removeprefix("data: ")))
    return events


def test_sse_chat_emits_status_deltas_and_completion(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat",
        json={"message": "What is Python?", "allow_general_fallback": True},
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    assert [event["type"] for event in events] == [
        "search_status",
        "search_status",
        "search_status",
        "search_status",
        "search_status",
        "answer_delta",
        "answer_delta",
        "completed",
    ]
    statuses = [event["status"] for event in events if event["type"] == "search_status"]
    assert statuses == [
        "understanding",
        "searching",
        "found",
        "evaluating",
        "generating",
    ]
    answer = "".join(
        str(event["delta"]) for event in events if event["type"] == "answer_delta"
    )
    assert answer == "测试回答"
    assert events[-1]["route"] == "general"


def test_sse_chat_includes_citations_for_knowledge(client: TestClient) -> None:
    knowledge = client.post("/api/v1/knowledge", json={"name": "SSE"}).json()
    client.post(
        "/api/v1/documents/upload",
        data={"knowledge_base_id": knowledge["id"]},
        files={"file": ("sse.txt", b"event stream knowledge", "text/plain")},
    )

    response = client.post(
        "/api/v1/chat",
        json={"message": "event stream?"},
        headers={"Accept": "text/event-stream"},
    )
    events = parse_sse(response.text)

    assert any(event["type"] == "citation" for event in events)
    assert events[-1]["type"] == "completed"
    assert events[-1]["route"] == "knowledge"
    assert events[-1]["citations"][0]["filename"] == "sse.txt"


def test_sse_chat_returns_503_before_streaming_when_llm_is_missing(
    test_settings: Settings,
    vector_store: InMemoryVectorStore,
) -> None:
    app: FastAPI = create_app(
        test_settings,
        vector_store=vector_store,
        embedding_provider_factory=lambda _: FakeEmbeddingProvider(),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat",
            json={"message": "hello"},
            headers={"Accept": "text/event-stream"},
        )

    assert response.status_code == 503
