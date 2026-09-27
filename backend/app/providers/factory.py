from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.exceptions import ProviderConfigurationError
from app.models.settings import ModelKind
from app.providers.embedding import EmbeddingProvider
from app.providers.llm import LLMProvider
from app.providers.openai_compatible import (
    OpenAICompatibleEmbeddingProvider,
    OpenAICompatibleLLMProvider,
)
from app.repositories.settings_repository import SettingsRepository

SUPPORTED_PROVIDERS = {"openai", "qwen", "deepseek", "custom"}
EmbeddingProviderFactory = Callable[[Session], EmbeddingProvider]
LLMProviderFactory = Callable[[Session], LLMProvider]


def build_embedding_provider(session: Session) -> EmbeddingProvider:
    config = SettingsRepository(session).get_model_config(ModelKind.EMBEDDING)
    if config is None or not config.enabled:
        raise ProviderConfigurationError("Embedding provider is not configured.")

    provider = config.provider.lower().strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise ProviderConfigurationError(f"Unsupported embedding provider: {provider}")
    if not config.model or not config.base_url:
        raise ProviderConfigurationError(
            "Embedding provider requires both model and base URL."
        )

    return OpenAICompatibleEmbeddingProvider(
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
    )


def build_llm_provider(session: Session) -> LLMProvider:
    config = SettingsRepository(session).get_model_config(ModelKind.LLM)
    if config is None or not config.enabled:
        raise ProviderConfigurationError("LLM provider is not configured.")

    provider = config.provider.lower().strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise ProviderConfigurationError(f"Unsupported LLM provider: {provider}")
    if not config.model or not config.base_url:
        raise ProviderConfigurationError("LLM provider requires both model and base URL.")

    return OpenAICompatibleLLMProvider(
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
    )


def build_embedding_provider_from_values(
    *,
    provider: str,
    model: str,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float = 20.0,
) -> EmbeddingProvider:
    normalized = provider.lower().strip()
    if normalized not in SUPPORTED_PROVIDERS:
        raise ProviderConfigurationError(f"Unsupported embedding provider: {provider}")
    if not model or not base_url:
        raise ProviderConfigurationError("Embedding provider requires both model and base URL.")
    return OpenAICompatibleEmbeddingProvider(
        base_url=base_url,
        model=model,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )


def build_llm_provider_from_values(
    *,
    provider: str,
    model: str,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float = 30.0,
) -> LLMProvider:
    normalized = provider.lower().strip()
    if normalized not in SUPPORTED_PROVIDERS:
        raise ProviderConfigurationError(f"Unsupported LLM provider: {provider}")
    if not model or not base_url:
        raise ProviderConfigurationError("LLM provider requires both model and base URL.")
    return OpenAICompatibleLLMProvider(
        base_url=base_url,
        model=model,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
