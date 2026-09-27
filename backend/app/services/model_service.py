import logging
import time

from sqlalchemy.orm import Session

from app.models.settings import ModelKind
from app.providers.base import ChatMessage
from app.providers.factory import (
    build_embedding_provider_from_values,
    build_llm_provider_from_values,
)
from app.repositories.settings_repository import SettingsRepository
from app.schemas.settings import ModelTestRequest, ModelTestResponse

logger = logging.getLogger(__name__)


class ModelService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = SettingsRepository(session)

    async def test_connection(self, payload: ModelTestRequest) -> ModelTestResponse:
        stored = self.repository.get_model_config(ModelKind(payload.kind))
        api_key = payload.api_key or (stored.api_key if stored else None)
        started_at = time.perf_counter()
        dimension: int | None = None

        try:
            if payload.kind == "llm":
                provider = build_llm_provider_from_values(
                    provider=payload.provider,
                    model=payload.model,
                    base_url=payload.base_url,
                    api_key=api_key,
                )
                result = await provider.chat(
                    [ChatMessage(role="user", content="请只回复 OK")]
                )
                connected = bool(result.content.strip())
            else:
                provider = build_embedding_provider_from_values(
                    provider=payload.provider,
                    model=payload.model,
                    base_url=payload.base_url,
                    api_key=api_key,
                )
                vectors = await provider.embed(["connection test"])
                connected = bool(vectors and vectors[0])
                dimension = len(vectors[0]) if vectors and vectors[0] else None

            latency = round((time.perf_counter() - started_at) * 1000, 2)
            return ModelTestResponse(
                kind=payload.kind,
                connected=connected,
                message="连接成功" if connected else "服务已响应，但返回内容为空",
                latency_ms=latency,
                model=payload.model,
                dimension=dimension if payload.kind == "embedding" else None,
            )
        except Exception as exc:
            logger.exception("model connection test failed kind=%s", payload.kind)
            message = str(exc).strip() or "连接失败"
            return ModelTestResponse(
                kind=payload.kind,
                connected=False,
                message=f"连接失败：{message}",
                latency_ms=round((time.perf_counter() - started_at) * 1000, 2),
                model=payload.model,
            )
