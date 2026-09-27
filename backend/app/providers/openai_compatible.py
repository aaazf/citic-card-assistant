import json
from collections.abc import AsyncIterator

import httpx

from app.core.exceptions import ProviderConfigurationError
from app.providers.base import ChatMessage, ChatResult


class OpenAICompatibleEmbeddingProvider:
    batch_size = 10

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        embeddings: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for start in range(0, len(texts), self.batch_size):
                batch = texts[start : start + self.batch_size]
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json={"model": self.model, "input": batch},
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    detail = response.text.strip()
                    suffix = f": {detail[:400]}" if detail else "."
                    raise ProviderConfigurationError(
                        f"Embedding provider returned HTTP {response.status_code}{suffix}"
                    ) from exc

                payload = response.json()
                rows = sorted(payload["data"], key=lambda row: row["index"])
                batch_embeddings = [row["embedding"] for row in rows]
                if len(batch_embeddings) != len(batch):
                    raise ProviderConfigurationError(
                        "Embedding provider returned an unexpected number of vectors."
                    )
                embeddings.extend(batch_embeddings)
        return embeddings


class OpenAICompatibleLLMProvider:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.last_stream_usage: tuple[int, int] | None = None

    @staticmethod
    def _parse_usage(payload: dict) -> tuple[int | None, int | None]:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return None, None
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        return (
            prompt if isinstance(prompt, int) else None,
            completion if isinstance(completion, int) else None,
        )

    async def chat(self, messages: list[ChatMessage]) -> ChatResult:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": message.role, "content": message.content}
                        for message in messages
                    ],
                    "temperature": 0.0,
                },
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderConfigurationError(
                f"LLM provider returned HTTP {response.status_code}."
            ) from exc

        payload = response.json()
        if isinstance(payload.get("error"), dict):
            message = str(payload["error"].get("message", "Unknown provider error"))
            if "overload" in message.lower():
                raise ProviderConfigurationError("模型服务暂时繁忙，请稍后重试。")
            raise ProviderConfigurationError(f"LLM provider error: {message}")

        choices = payload.get("choices")
        if not choices:
            raise ProviderConfigurationError("LLM provider returned no completion choices.")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise ProviderConfigurationError("LLM provider returned an empty completion.")
        prompt_tokens, completion_tokens = self._parse_usage(payload)
        return ChatResult(
            content=content,
            model=payload.get("model", self.model),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        self.last_stream_usage = None
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": message.role, "content": message.content}
                        for message in messages
                    ],
                    "temperature": 0.0,
                    "stream": True,
                    "stream_options": {"include_usage": True},
                },
            ) as response:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise ProviderConfigurationError(
                        f"LLM provider returned HTTP {response.status_code}."
                    ) from exc

                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if not data or data == "[DONE]":
                        continue
                    payload = json.loads(data)
                    usage = payload.get("usage")
                    if isinstance(usage, dict):
                        prompt = usage.get("prompt_tokens")
                        completion = usage.get("completion_tokens")
                        if isinstance(prompt, int) and isinstance(completion, int):
                            self.last_stream_usage = (prompt, completion)
                    choices = payload.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {}).get("content")
                    if delta:
                        yield delta
