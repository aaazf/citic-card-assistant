from typing import Protocol

from app.rag.types import RetrievedChunk


class Retriever(Protocol):
    async def retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]: ...
