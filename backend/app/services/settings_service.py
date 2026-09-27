from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.settings import ModelKind
from app.repositories.settings_repository import SettingsRepository
from app.schemas.settings import (
    PricingSettingsRead,
    ProviderConfigRead,
    ProviderConfigUpdate,
    RetrievalSettingsRead,
    SettingsRead,
    SettingsUpdate,
    SystemSettingsRead,
)
from app.services.usage_service import DEFAULT_PRICING

DEFAULT_RETRIEVAL = {
    "top_k": 5,
    "similarity_threshold": 0.5,
    "reranker_enabled": False,
}


class SettingsService:
    def __init__(self, session: Session, data_dir: Path) -> None:
        self.session = session
        self.data_dir = data_dir
        self.repository = SettingsRepository(session)

    def get(self) -> SettingsRead:
        retrieval = self.repository.get_system_setting("retrieval")
        retrieval_values = DEFAULT_RETRIEVAL | (retrieval.value if retrieval else {})
        pricing = self.repository.get_system_setting("pricing")
        pricing_values = DEFAULT_PRICING | (pricing.value if pricing else {})
        return SettingsRead(
            llm=self._provider_read(ModelKind.LLM),
            embedding=self._provider_read(ModelKind.EMBEDDING),
            retrieval=RetrievalSettingsRead.model_validate(retrieval_values),
            pricing=PricingSettingsRead.model_validate(pricing_values),
            system=SystemSettingsRead(data_dir=str(self.data_dir)),
        )

    def update(self, payload: SettingsUpdate) -> SettingsRead:
        if payload.llm is not None:
            self._update_provider(ModelKind.LLM, payload.llm)
        if payload.embedding is not None:
            self._update_provider(ModelKind.EMBEDDING, payload.embedding)
        if payload.retrieval is not None:
            self._update_retrieval(payload.retrieval.model_dump(exclude_none=True))
        if payload.pricing is not None:
            self._update_pricing(payload.pricing.model_dump(exclude_none=True))
        self.session.commit()
        return self.get()

    def _update_pricing(self, values: dict[str, Any]) -> None:
        setting = self.repository.get_system_setting("pricing")
        merged = DEFAULT_PRICING | (setting.value if setting else {}) | values
        if setting is None:
            self.repository.create_system_setting("pricing", merged)
        else:
            setting.value = merged

    def _provider_read(self, kind: ModelKind) -> ProviderConfigRead:
        config = self.repository.get_model_config(kind)
        if config is None:
            return ProviderConfigRead()
        return ProviderConfigRead(
            provider=config.provider or None,
            model=config.model or None,
            base_url=config.base_url,
            api_key_configured=bool(config.api_key),
            enabled=config.enabled,
        )

    def _update_provider(self, kind: ModelKind, payload: ProviderConfigUpdate) -> None:
        config = self.repository.get_model_config(kind)
        if config is None:
            config = self.repository.create_model_config(kind)

        for field in ("provider", "model", "base_url", "enabled"):
            value = getattr(payload, field)
            if value is not None:
                setattr(config, field, value)
        if payload.api_key is not None:
            config.api_key = payload.api_key or None

    def _update_retrieval(self, values: dict[str, Any]) -> None:
        setting = self.repository.get_system_setting("retrieval")
        merged = DEFAULT_RETRIEVAL | (setting.value if setting else {}) | values
        if setting is None:
            self.repository.create_system_setting("retrieval", merged)
        else:
            setting.value = merged
