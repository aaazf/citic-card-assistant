from collections.abc import AsyncIterator
from typing import Protocol

from app.providers.base import ChatMessage, ChatResult


class LLMProvider(Protocol):
    async def chat(self, messages: list[ChatMessage]) -> ChatResult: ...

    def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]: ...
