from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_model_service, get_settings_service
from app.schemas.settings import (
    ModelTestRequest,
    ModelTestResponse,
    SettingsRead,
    SettingsUpdate,
)
from app.services.model_service import ModelService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])
ServiceDependency = Annotated[SettingsService, Depends(get_settings_service)]
ModelServiceDependency = Annotated[ModelService, Depends(get_model_service)]


@router.get("", response_model=SettingsRead)
def get_app_settings(service: ServiceDependency) -> SettingsRead:
    return service.get()


@router.put("", response_model=SettingsRead)
def update_app_settings(payload: SettingsUpdate, service: ServiceDependency) -> SettingsRead:
    return service.update(payload)


@router.post("/test-model", response_model=ModelTestResponse)
async def test_model_connection(
    payload: ModelTestRequest,
    service: ModelServiceDependency,
) -> ModelTestResponse:
    return await service.test_connection(payload)
