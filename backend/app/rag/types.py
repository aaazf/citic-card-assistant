from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


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


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RAGAnswer:
    content: str
    route: RouteMode
    citations: list[RetrievedChunk] = field(default_factory=list)
    suggest_human: bool = False
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    follow_ups: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StreamStatusEvent:
    status: SearchStatus
    message: str
    count: int | None = None


@dataclass(frozen=True)
class StreamDeltaEvent:
    delta: str


@dataclass(frozen=True)
class StreamCitationEvent:
    citation: RetrievedChunk


@dataclass(frozen=True)
class StreamCompletedEvent:
    route: RouteMode
    citations: list[RetrievedChunk]
    suggest_human: bool = False
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    follow_ups: list[str] = field(default_factory=list)


RAGStreamEvent = (
    StreamStatusEvent | StreamDeltaEvent | StreamCitationEvent | StreamCompletedEvent
)
