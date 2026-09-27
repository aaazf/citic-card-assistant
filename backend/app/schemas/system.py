from typing import Literal

from app.schemas.common import APIModel


class HealthResponse(APIModel):
    status: Literal["ok"]
    version: str
    database: Literal["ok"]


class ProviderStatus(APIModel):
    kind: Literal["llm", "embedding"]
    connected: bool
    provider: str | None = None
    model: str | None = None


class ModelStatusResponse(APIModel):
    providers: list[ProviderStatus]
