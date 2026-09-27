from typing import Any

from pydantic import BaseModel, ConfigDict


class ChunkRecord(BaseModel):
    """Vector-store contract. Chunk content is owned by Chroma, not SQLite."""

    model_config = ConfigDict(extra="forbid")

    id: str
    document_id: str
    knowledge_base_id: str
    content: str
    metadata: dict[str, Any]
    embedding: list[float] | None = None
