from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_chat_service
from app.core.exceptions import (
    ProviderConfigurationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.rag.types import (
    StreamCitationEvent,
    StreamCompletedEvent,
    StreamDeltaEvent,
    StreamStatusEvent,
)
from app.schemas.chat import (
    AnswerDeltaEvent,
    ChatRequest,
    ChatResponse,
    Citation,
    CitationEvent,
    CompletedEvent,
    ErrorEvent,
    RouteMode,
    SearchStatus,
    SearchStatusEvent,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])
ServiceDependency = Annotated[ChatService, Depends(get_chat_service)]


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    payload: ChatRequest,
    service: ServiceDependency,
    accept: Annotated[str | None, Header()] = None,
) -> ChatResponse | StreamingResponse:
    if accept and "text/event-stream" in accept.lower():
        try:
            stream_result = await service.stream_answer(
                message=payload.message,
                conversation_id=payload.conversation_id,
                knowledge_base_id=payload.knowledge_base_id,
                allow_general_fallback=payload.allow_general_fallback,
                channel=payload.channel,
                purpose=payload.purpose,
                top_k=payload.top_k,
            )
        except ProviderConfigurationError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except ResourceNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except ResourceConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

        return StreamingResponse(
            _encode_stream(
                stream_result.events,
                stream_result.conversation_id,
                stream_result.knowledge_base_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        result = await service.answer(
            message=payload.message,
            conversation_id=payload.conversation_id,
            knowledge_base_id=payload.knowledge_base_id,
            allow_general_fallback=payload.allow_general_fallback,
            channel=payload.channel,
            purpose=payload.purpose,
            top_k=payload.top_k,
        )
    except ProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ResourceConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return ChatResponse(
        conversation_id=result.conversation_id,
        knowledge_base_id=result.knowledge_base_id,
        answer=result.answer.content,
        route=RouteMode(result.answer.route.value),
        citations=[_to_citation(item) for item in result.answer.citations],
        suggest_human=result.answer.suggest_human,
        follow_ups=result.answer.follow_ups,
    )


async def _encode_stream(
    events: AsyncIterator[object],
    conversation_id: str,
    knowledge_base_id: str | None,
) -> AsyncIterator[str]:
    try:
        async for event in events:
            if isinstance(event, StreamStatusEvent):
                data: BaseModel = SearchStatusEvent(
                    status=SearchStatus(event.status.value),
                    message=event.message,
                    count=event.count,
                )
            elif isinstance(event, StreamDeltaEvent):
                data = AnswerDeltaEvent(delta=event.delta)
            elif isinstance(event, StreamCitationEvent):
                data = CitationEvent(citation=_to_citation(event.citation))
            elif isinstance(event, StreamCompletedEvent):
                data = CompletedEvent(
                    conversation_id=conversation_id,
                    knowledge_base_id=knowledge_base_id,
                    route=RouteMode(event.route.value),
                    citations=[_to_citation(item) for item in event.citations],
                    suggest_human=event.suggest_human,
                    follow_ups=event.follow_ups,
                )
            else:
                continue
            yield f"event: {data.type}\ndata: {data.model_dump_json()}\n\n"
    except Exception as exc:
        error = ErrorEvent(detail=str(exc))
        yield f"event: {error.type}\ndata: {error.model_dump_json()}\n\n"


def _to_citation(item: object) -> Citation:
    chunk_id = str(item.chunk_id)
    document_id = str(item.document_id)
    score = float(item.score)
    metadata = item.metadata
    page = metadata.get("page")
    return Citation(
        document_id=document_id,
        filename=str(metadata.get("filename", "未知文件")),
        page=page if isinstance(page, int) else None,
        chunk_id=chunk_id,
        score=score,
    )
