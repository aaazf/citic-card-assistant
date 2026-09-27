from collections.abc import AsyncIterator

from app.models.chunk import ChunkRecord
from app.providers.base import ChatMessage, ChatResult
from app.rag.types import RetrievedChunk


class FakeEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [
            [
                float((len(text) + index) % 11),
                float((index + 1) % 7),
                float((len(text) * 3) % 13),
                1.0,
            ]
            for index, text in enumerate(texts)
        ]


class FakeLLMProvider:
    def __init__(
        self,
        content: str = "测试回答",
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> None:
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.last_messages: list[ChatMessage] = []
        self.all_messages: list[list[ChatMessage]] = []

    async def chat(self, messages: list[ChatMessage]) -> ChatResult:
        self.last_messages = messages
        self.all_messages.append(messages)
        return ChatResult(
            content=self.content,
            model="fake-model",
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
        )

    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        self.last_messages = messages
        self.all_messages.append(messages)
        midpoint = max(1, len(self.content) // 2)
        yield self.content[:midpoint]
        yield self.content[midpoint:]


class InMemoryVectorStore:
    def __init__(self) -> None:
        self.records: dict[str, ChunkRecord] = {}

    def add(self, records: list[ChunkRecord]) -> None:
        self.records.update({record.id: record for record in records})

    def count(self) -> int:
        return len(self.records)

    def list_all_chunks(self) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id=record.id,
                document_id=record.document_id,
                content=record.content,
                score=0.0,
                metadata={
                    **record.metadata,
                    "document_id": record.document_id,
                    "knowledge_base_id": record.knowledge_base_id,
                },
            )
            for record in self.records.values()
        ]

    def get_chunk(self, chunk_id: str) -> ChunkRecord | None:
        return self.records.get(chunk_id)

    def list_chunks(self, document_id: str) -> list[ChunkRecord]:
        return sorted(
            [
                record
                for record in self.records.values()
                if record.document_id == document_id
            ],
            key=lambda record: int(record.metadata.get("chunk_index", 0)),
        )

    def keyword_search(
        self,
        terms: list[str],
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        matches = []
        for record in self.records.values():
            if where and any(getattr(record, key, None) != value for key, value in where.items()):
                continue
            count = sum(term.lower() in record.content.lower() for term in terms)
            if count:
                matches.append(
                    RetrievedChunk(
                        chunk_id=record.id,
                        document_id=record.document_id,
                        content=record.content,
                        score=min(1.0, 0.72 + count * 0.18),
                        metadata=record.metadata,
                    )
                )
        return sorted(matches, key=lambda item: item.score, reverse=True)[:top_k]

    def delete_document(self, document_id: str) -> None:
        self.records = {
            record_id: record
            for record_id, record in self.records.items()
            if record.document_id != document_id
        }

    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        matches = []
        for record in self.records.values():
            if where and any(getattr(record, key, None) != value for key, value in where.items()):
                continue
            matches.append(
                RetrievedChunk(
                    chunk_id=record.id,
                    document_id=record.document_id,
                    content=record.content,
                    score=1.0,
                    metadata=record.metadata,
                )
            )
        return matches[:top_k]
