from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.fakes import FakeEmbeddingProvider, FakeLLMProvider, InMemoryVectorStore


@pytest.fixture
def dist_dir(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id='root'></div>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('app')", encoding="utf-8")
    (dist / "citic-logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "secret.txt").write_text("do-not-serve", encoding="utf-8")
    return dist


@pytest.fixture
def spa_client(tmp_path: Path, dist_dir: Path) -> Iterator[TestClient]:
    settings = Settings(
        data_dir=tmp_path,
        database_url=f"sqlite:///{(tmp_path / 'app.db').as_posix()}",
        cors_origins=[],
        frontend_dist_dir=dist_dir,
        serve_frontend=True,
    )
    app: FastAPI = create_app(
        settings,
        vector_store=InMemoryVectorStore(),
        embedding_provider_factory=lambda _: FakeEmbeddingProvider(),
        llm_provider_factory=lambda _: FakeLLMProvider(),
    )
    with TestClient(app) as client:
        yield client


def test_root_serves_index_html(spa_client: TestClient) -> None:
    response = spa_client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "id='root'" in response.text


def test_head_root_is_supported(spa_client: TestClient) -> None:
    assert spa_client.head("/").status_code == 200


def test_assets_are_served_from_dist(spa_client: TestClient) -> None:
    response = spa_client.get("/assets/app.js")

    assert response.status_code == 200
    assert "console.log" in response.text


def test_unknown_route_falls_back_to_spa(spa_client: TestClient) -> None:
    response = spa_client.get("/admin/knowledge")

    assert response.status_code == 200
    assert "id='root'" in response.text


def test_unknown_api_route_stays_a_json_404(spa_client: TestClient) -> None:
    response = spa_client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"] == "Not found."


def test_path_traversal_cannot_escape_dist(spa_client: TestClient) -> None:
    for attempt in ("/../secret.txt", "/..%2Fsecret.txt", "/..%5Csecret.txt"):
        response = spa_client.get(attempt)

        assert response.status_code == 200
        assert "do-not-serve" not in response.text
        assert "id='root'" in response.text


def test_frontend_is_not_served_when_disabled(client: TestClient) -> None:
    assert client.get("/").status_code == 404