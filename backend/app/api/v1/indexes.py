from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.deps import get_index_service
from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.schemas.index import IndexListResponse, IndexVersionRead
from app.services.index_service import IndexService

router = APIRouter(prefix="/indexes", tags=["indexes"])
ServiceDependency = Annotated[IndexService, Depends(get_index_service)]


@router.get("", response_model=IndexListResponse)
def list_index_versions(service: ServiceDependency) -> IndexListResponse:
    return service.list_versions()


@router.post(
    "/rebuild",
    response_model=IndexVersionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def rebuild_index(
    background_tasks: BackgroundTasks,
    service: ServiceDependency,
) -> IndexVersionRead:
    try:
        version = service.create_rebuild()
    except ResourceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    background_tasks.add_task(service.run_rebuild, version.id)
    return version


@router.post("/{version_id}/activate", response_model=IndexVersionRead)
async def activate_index(
    version_id: str,
    service: ServiceDependency,
) -> IndexVersionRead:
    try:
        return await service.activate(version_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResourceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
