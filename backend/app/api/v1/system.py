from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.settings import ModelConfig, ModelKind
from app.schemas.system import HealthResponse, ModelStatusResponse, ProviderStatus

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    try:
        request.app.state.database.ping()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database health check failed.",
        ) from exc
    return HealthResponse(status="ok", version=settings.app_version, database="ok")


@router.get("/model/status", response_model=ModelStatusResponse)
def model_status(request: Request) -> ModelStatusResponse:
    with request.app.state.database.session() as session:
        configs = {
            config.kind: config
            for config in session.scalars(select(ModelConfig)).all()
        }

    providers = []
    for kind in (ModelKind.LLM, ModelKind.EMBEDDING):
        config = configs.get(kind)
        providers.append(
            ProviderStatus(
                kind=kind.value,
                connected=bool(config and config.enabled),
                provider=config.provider if config else None,
                model=config.model if config else None,
            )
        )
    return ModelStatusResponse(providers=providers)
