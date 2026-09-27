import asyncio

from app.providers.openai_compatible import OpenAICompatibleEmbeddingProvider


def test_embedding_provider_splits_large_inputs_into_batches(monkeypatch) -> None:
    batches: list[list[str]] = []

    class FakeResponse:
        status_code = 200
        text = ""

        def __init__(self, inputs: list[str]) -> None:
            self.inputs = inputs

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {"index": index, "embedding": [float(index)]}
                    for index in reversed(range(len(self.inputs)))
                ]
            }

    class FakeAsyncClient:
        def __init__(self, **kwargs) -> None:
            del kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            del args

        async def post(self, url: str, headers: dict, json: dict) -> FakeResponse:
            del url, headers
            inputs = json["input"]
            batches.append(inputs)
            return FakeResponse(inputs)

    monkeypatch.setattr(
        "app.providers.openai_compatible.httpx.AsyncClient",
        FakeAsyncClient,
    )
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://example.test/v1",
        model="embedding-model",
        api_key="test-key",
    )

    embeddings = asyncio.run(provider.embed([f"text-{index}" for index in range(33)]))

    assert [len(batch) for batch in batches] == [10, 10, 10, 3]
    assert len(embeddings) == 33
    assert embeddings[0] == [0.0]
    assert embeddings[-1] == [2.0]
