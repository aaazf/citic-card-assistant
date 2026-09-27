from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.common import APIModel


class RouteMode(StrEnum):
    KNOWLEDGE = "knowledge"
    HYBRID = "hybrid"
    GENERAL = "general"
    GUIDANCE = "guidance"


class SearchStatus(StrEnum):
    UNDERSTANDING = "understanding"
    SEARCHING = "searching"
    FOUND = "found"
    EVALUATING = "evaluating"
    GENERATING = "generating"
    COMPLETED = "completed"


class Citation(APIModel):
    document_id: str
    filename: str
    page: int | None = None
    chunk_id: str
    score: float

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_citation(cls, value: object) -> object:
        if not isinstance(value, dict) or "filename" in value:
            return value
        metadata = value.get("metadata")
        if not isinstance(metadata, dict):
            return value
        return {
            **value,
            "filename": metadata.get("filename", "未知文件"),
            "page": metadata.get("page"),
        }


class ChatRequest(APIModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None
    knowledge_base_id: str | None = None
    allow_general_fallback: bool = False
    channel: Literal["customer", "staff"] = "customer"
    purpose: Literal["chat", "eval"] = "chat"
    top_k: int = Field(default=5, ge=1, le=50)


class ChatResponse(APIModel):
    conversation_id: str
    knowledge_base_id: str | None = None
    answer: str
    route: RouteMode
    citations: list[Citation]
    suggest_human: bool = False
    follow_ups: list[str] = []


class SearchStatusEvent(APIModel):
    type: Literal["search_status"] = "search_status"
    status: SearchStatus
    message: str
    count: int | None = None


class AnswerDeltaEvent(APIModel):
    type: Literal["answer_delta"] = "answer_delta"
    delta: str


class CitationEvent(APIModel):
    type: Literal["citation"] = "citation"
    citation: Citation


class CompletedEvent(APIModel):
    type: Literal["completed"] = "completed"
    conversation_id: str
    knowledge_base_id: str | None = None
    route: RouteMode
    citations: list[Citation]
    suggest_human: bool = False
    follow_ups: list[str] = []


class ErrorEvent(APIModel):
    type: Literal["error"] = "error"
    detail: str


ChatStreamEvent = Annotated[
    SearchStatusEvent | AnswerDeltaEvent | CitationEvent | CompletedEvent | ErrorEvent,
    Field(discriminator="type"),
]
