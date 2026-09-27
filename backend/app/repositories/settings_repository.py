from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.settings import ModelConfig, ModelKind, SystemSetting


class SettingsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_model_config(self, kind: ModelKind) -> ModelConfig | None:
        statement = select(ModelConfig).where(ModelConfig.kind == kind)
        return self.session.scalar(statement)

    def create_model_config(self, kind: ModelKind) -> ModelConfig:
        config = ModelConfig(kind=kind, provider="", model="", enabled=False)
        self.session.add(config)
        return config

    def get_system_setting(self, key: str) -> SystemSetting | None:
        return self.session.get(SystemSetting, key)

    def create_system_setting(self, key: str, value: dict[str, Any]) -> SystemSetting:
        setting = SystemSetting(key=key, value=value)
        self.session.add(setting)
        return setting
