from typing import Protocol

from app.models.chunk import ChunkRecord
from app.rag.types import RetrievedChunk


class VectorStore(Protocol):
    def add(self, records: list[ChunkRecord]) -> None: ...

    def get_chunk(self, chunk_id: str) -> ChunkRecord | None: ...

    def list_chunks(self, document_id: str) -> list[ChunkRecord]: ...

    def keyword_search(
        self,
        terms: list[str],
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]: ...

    def delete_document(self, document_id: str) -> None: ...

    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]: ...
