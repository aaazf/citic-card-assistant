from fastapi.testclient import TestClient


def ask(client: TestClient, message: str, channel: str = "customer") -> None:
    client.post(
        "/api/v1/chat",
        json={"message": message, "channel": channel, "allow_general_fallback": True},
    )


def test_hot_questions_rank_customer_first_questions(client: TestClient) -> None:
    ask(client, "年费怎么减免？")
    ask(client, "年费怎么减免")
    ask(client, "额度如何提升")
    ask(client, "年费怎么减免", channel="staff")  # 测试会话不计入

    questions = client.get("/api/v1/conversations/hot-questions").json()

    assert questions[0]["text"] in {"年费怎么减免？", "年费怎么减免"}
    assert questions[0]["count"] == 2
    assert any(item["text"] == "额度如何提升" for item in questions)
    assert sum(item["count"] for item in questions) == 3


def test_hot_questions_empty_when_no_customer_chat(client: TestClient) -> None:
    ask(client, "内部测试问题", channel="staff")

    assert client.get("/api/v1/conversations/hot-questions").json() == []
