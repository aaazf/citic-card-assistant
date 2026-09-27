from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_knowledge_service
from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.schemas.common import ErrorResponse
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseRead
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
ServiceDependency = Annotated[KnowledgeService, Depends(get_knowledge_service)]


@router.get("", response_model=list[KnowledgeBaseRead])
def list_knowledge_bases(service: ServiceDependency) -> list[KnowledgeBaseRead]:
    return service.list()


@router.post(
    "",
    response_model=KnowledgeBaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    service: ServiceDependency,
) -> KnowledgeBaseRead:
    try:
        return service.create(payload)
    except ResourceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{knowledge_base_id}", response_model=ErrorResponse)
def delete_knowledge_base(
    knowledge_base_id: str,
    service: ServiceDependency,
) -> ErrorResponse:
    try:
        service.delete(knowledge_base_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ErrorResponse(detail="Knowledge base deleted.")
