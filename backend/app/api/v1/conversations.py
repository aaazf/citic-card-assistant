from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_session_service
from app.core.exceptions import ResourceNotFoundError
from app.schemas.common import ErrorResponse
from app.schemas.conversation import ConversationRead, ConversationSummary
from app.services.session_service import SessionService

router = APIRouter(prefix="/conversations", tags=["conversations"])
ServiceDependency = Annotated[SessionService, Depends(get_session_service)]


@router.get("", response_model=list[ConversationSummary])
def list_conversations(service: ServiceDependency) -> list[ConversationSummary]:
    return service.list_conversations()


@router.get("/hot-questions")
def hot_questions(service: ServiceDependency, limit: int = 4) -> list[dict[str, object]]:
    return service.hot_questions(limit=limit)


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(
    conversation_id: str,
    service: ServiceDependency,
) -> ConversationRead:
    try:
        return service.get_conversation(conversation_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{conversation_id}", response_model=ErrorResponse)
def delete_conversation(
    conversation_id: str,
    service: ServiceDependency,
) -> ErrorResponse:
    try:
        service.delete_conversation(conversation_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ErrorResponse(detail="Conversation deleted.")
