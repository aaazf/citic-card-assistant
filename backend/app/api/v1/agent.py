from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_knowledge_search_service
from app.core.exceptions import ProviderConfigurationError, ResourceConflictError
from app.schemas.search import KnowledgeSearchRequest, KnowledgeSearchResponse
from app.services.knowledge_service import KnowledgeSearchService

router = APIRouter(prefix="/knowledge", tags=["agent"])
ServiceDependency = Annotated[KnowledgeSearchService, Depends(get_knowledge_search_service)]


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    payload: KnowledgeSearchRequest,
    service: ServiceDependency,
) -> KnowledgeSearchResponse:
    try:
        results = await service.search(payload.query, payload.top_k)
    except ProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ResourceConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return KnowledgeSearchResponse(query=payload.query, results=results)
