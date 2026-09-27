from typing import Any

from pydantic import Field

from app.schemas.common import APIModel


class KnowledgeSearchRequest(APIModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)


class KnowledgeSearchResult(APIModel):
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any]


class KnowledgeSearchResponse(APIModel):
    query: str
    results: list[KnowledgeSearchResult]
