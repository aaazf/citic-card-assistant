import json

from fastapi.testclient import TestClient

from tests.fakes import FakeLLMProvider


def parse_sse(body: str) -> list[dict[str, object]]:
    events = []
    for block in body.strip().split("\n\n"):
        data_line = next(line for line in block.splitlines() if line.startswith("data: "))
        events.append(json.loads(data_line.removeprefix("data: ")))
    return events


def test_json_chat_persists_messages_and_restores_context(
    client: TestClient,
    llm_provider: FakeLLMProvider,
) -> None:
    first = client.post(
        "/api/v1/chat",
        json={"message": "First question", "allow_general_fallback": True},
    ).json()
    conversation_id = first["conversation_id"]

    listed = client.get("/api/v1/conversations").json()
    assert listed[0]["id"] == conversation_id
    assert listed[0]["title"] == "First question"
    detail = client.get(f"/api/v1/conversations/{conversation_id}").json()
    assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]

    second = client.post(
        "/api/v1/chat",
        json={
            "message": "Second question",
            "conversation_id": conversation_id,
            "allow_general_fallback": True,
        },
    )
    assert second.status_code == 200
    assert llm_provider.last_messages[1].content == "First question"
    assert llm_provider.last_messages[2].content == "测试回答"

    updated = client.get(f"/api/v1/conversations/{conversation_id}").json()
    assert [message["role"] for message in updated["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_stream_chat_persists_completed_answer(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat",
        json={"message": "Streaming question", "allow_general_fallback": True},
        headers={"Accept": "text/event-stream"},
    )
    events = parse_sse(response.text)
    conversation_id = events[-1]["conversation_id"]

    detail = client.get(f"/api/v1/conversations/{conversation_id}").json()

    assert [message["content"] for message in detail["messages"]] == [
        "Streaming question",
        "测试回答",
    ]


def test_delete_conversation(client: TestClient) -> None:
    conversation_id = client.post("/api/v1/chat", json={"message": "Delete me"}).json()[
        "conversation_id"
    ]

    response = client.delete(f"/api/v1/conversations/{conversation_id}")

    assert response.status_code == 200
    assert client.get(f"/api/v1/conversations/{conversation_id}").status_code == 404
    assert client.get("/api/v1/conversations").json() == []


def test_missing_conversation_returns_not_found(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat",
        json={"message": "hello", "conversation_id": "missing"},
    )

    assert response.status_code == 404


def test_scoped_chat_filters_retrieval_and_persists_scope(client: TestClient) -> None:
    first_kb = client.post("/api/v1/knowledge", json={"name": "Scoped A"}).json()
    second_kb = client.post("/api/v1/knowledge", json={"name": "Scoped B"}).json()
    client.post(
        "/api/v1/documents/upload",
        data={"knowledge_base_id": first_kb["id"]},
        files={"file": ("alpha.txt", b"alpha project", "text/plain")},
    )
    client.post(
        "/api/v1/documents/upload",
        data={"knowledge_base_id": second_kb["id"]},
        files={"file": ("beta.txt", b"beta project", "text/plain")},
    )

    response = client.post(
        "/api/v1/chat",
        json={"message": "project", "knowledge_base_id": first_kb["id"]},
    ).json()
    detail = client.get(f"/api/v1/conversations/{response['conversation_id']}").json()

    assert response["knowledge_base_id"] == first_kb["id"]
    assert response["citations"][0]["filename"] == "alpha.txt"
    assert detail["knowledge_base_id"] == first_kb["id"]


def test_strict_scoped_chat_returns_no_evidence_without_llm_fallback(
    client: TestClient,
    llm_provider: FakeLLMProvider,
) -> None:
    knowledge_base = client.post("/api/v1/knowledge", json={"name": "Empty"}).json()
    llm_provider.last_messages = []

    response = client.post(
        "/api/v1/chat",
        json={"message": "anything", "knowledge_base_id": knowledge_base["id"]},
    ).json()

    assert response["route"] == "general"
    assert response["answer"] == "当前知识库中没有找到足够依据。"
    assert response["citations"] == []
    assert llm_provider.last_messages == []


def test_conversation_channel_defaults_to_customer_and_accepts_staff(
    client: TestClient,
) -> None:
    customer = client.post(
        "/api/v1/chat",
        json={"message": "年费怎么收", "allow_general_fallback": True},
    ).json()
    staff = client.post(
        "/api/v1/chat",
        json={"message": "额度怎么提升", "channel": "staff", "allow_general_fallback": True},
    ).json()

    listed = {item["id"]: item for item in client.get("/api/v1/conversations").json()}

    assert listed[customer["conversation_id"]]["channel"] == "customer"
    assert listed[staff["conversation_id"]]["channel"] == "staff"
