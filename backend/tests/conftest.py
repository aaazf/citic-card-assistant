from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.fakes import FakeEmbeddingProvider, FakeLLMProvider, InMemoryVectorStore


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        database_url=f"sqlite:///{(tmp_path / 'app.db').as_posix()}",
        cors_origins=[],
        serve_frontend=False,
    )


@pytest.fixture
def vector_store() -> InMemoryVectorStore:
    return InMemoryVectorStore()


@pytest.fixture
def llm_provider() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def test_app(
    test_settings: Settings,
    vector_store: InMemoryVectorStore,
    llm_provider: FakeLLMProvider,
) -> FastAPI:
    return create_app(
        test_settings,
        vector_store=vector_store,
        embedding_provider_factory=lambda _: FakeEmbeddingProvider(),
        llm_provider_factory=lambda _: llm_provider,
    )


@pytest.fixture
def client(test_app: FastAPI) -> Iterator[TestClient]:
    with TestClient(test_app) as test_client:
        yield test_client
