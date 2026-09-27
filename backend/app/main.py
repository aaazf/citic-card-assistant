from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.logging import configure_logging
from app.providers.factory import (
    EmbeddingProviderFactory,
    LLMProviderFactory,
    build_embedding_provider,
    build_llm_provider,
)
from app.vectorstores.active import ActiveVectorStore
from app.vectorstores.base import VectorStore
from app.vectorstores.chroma import ChromaVectorStore


def create_app(
    settings: Settings | None = None,
    vector_store: VectorStore | None = None,
    embedding_provider_factory: EmbeddingProviderFactory | None = None,
    llm_provider_factory: LLMProviderFactory | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    app_settings.ensure_directories()
    configure_logging()

    database = Database(app_settings.database_url)
    if vector_store is not None:
        def index_store_factory(collection_name: str) -> VectorStore:
            del collection_name
            return vector_store

        active_vector_store = vector_store
    else:
        def index_store_factory(collection_name: str) -> VectorStore:
            return ChromaVectorStore(app_settings.data_dir / "chroma", collection_name)

        active_vector_store = ActiveVectorStore(database, index_store_factory)
    active_embedding_provider_factory = embedding_provider_factory or build_embedding_provider
    active_llm_provider_factory = llm_provider_factory or build_llm_provider

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.init_schema()
        yield
        database.dispose()

    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description="Local-first RAG knowledge assistant API.",
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.state.database = database
    application.state.vector_store = active_vector_store
    application.state.index_store_factory = index_store_factory
    application.state.embedding_provider_factory = active_embedding_provider_factory
    application.state.llm_provider_factory = active_llm_provider_factory

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=app_settings.api_v1_prefix)
    register_frontend(application, app_settings)
    return application


def register_frontend(application: FastAPI, app_settings: Settings) -> None:
    """Serve the built single-page app from the same origin as the API.

    Reaching the app through a tunnel gives it a public hostname, so the browser
    must not need a separate origin for the API.
    """

    dist_dir = Path(app_settings.frontend_dist_dir).resolve()
    index_file = dist_dir / "index.html"
    if not app_settings.serve_frontend or not index_file.is_file():
        return

    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        application.mount(
            "/assets",
            StaticFiles(directory=assets_dir),
            name="frontend-assets",
        )

    api_prefix = app_settings.api_v1_prefix.strip("/")

    @application.api_route(
        "/{full_path:path}",
        methods=["GET", "HEAD"],
        include_in_schema=False,
    )
    def serve_spa(full_path: str) -> FileResponse:
        if full_path == api_prefix or full_path.startswith(f"{api_prefix}/"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not found.",
            )

        if full_path:
            candidate = (dist_dir / full_path).resolve()
            if candidate.is_file() and dist_dir in candidate.parents:
                return FileResponse(candidate)
        return FileResponse(index_file)


app = create_app()
