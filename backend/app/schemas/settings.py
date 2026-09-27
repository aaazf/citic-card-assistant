from typing import Literal

from pydantic import Field

from app.schemas.common import APIModel


class ProviderConfigUpdate(APIModel):
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    enabled: bool | None = None


class RetrievalSettingsUpdate(APIModel):
    top_k: int | None = Field(default=None, ge=1, le=50)
    similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    reranker_enabled: bool | None = None


class PricingSettingsUpdate(APIModel):
    input_per_million: float | None = Field(default=None, ge=0.0)
    output_per_million: float | None = Field(default=None, ge=0.0)


class SettingsUpdate(APIModel):
    llm: ProviderConfigUpdate | None = None
    embedding: ProviderConfigUpdate | None = None
    retrieval: RetrievalSettingsUpdate | None = None
    pricing: PricingSettingsUpdate | None = None


class ProviderConfigRead(APIModel):
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key_configured: bool = False
    enabled: bool = False


class RetrievalSettingsRead(APIModel):
    top_k: int = 5
    similarity_threshold: float = 0.5
    reranker_enabled: bool = False


class PricingSettingsRead(APIModel):
    input_per_million: float = 2.0
    output_per_million: float = 8.0


class SystemSettingsRead(APIModel):
    data_dir: str


class SettingsRead(APIModel):
    llm: ProviderConfigRead
    embedding: ProviderConfigRead
    retrieval: RetrievalSettingsRead
    pricing: PricingSettingsRead
    system: SystemSettingsRead


class ModelTestRequest(APIModel):
    kind: Literal["llm", "embedding"]
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    api_key: str | None = None


class ModelTestResponse(APIModel):
    kind: Literal["llm", "embedding"]
    connected: bool
    message: str
    latency_ms: float | None = None
    model: str | None = None
    dimension: int | None = None
