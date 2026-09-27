from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.index_service import IndexService
from app.services.knowledge_service import KnowledgeSearchService, KnowledgeService
from app.services.model_service import ModelService
from app.services.session_service import SessionService
from app.services.settings_service import SettingsService


def get_db(request: Request) -> Iterator[Session]:
    with request.app.state.database.session() as session:
        yield session


def get_knowledge_service(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> KnowledgeService:
    return KnowledgeService(session, vector_store=request.app.state.vector_store)


def get_settings_service(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> SettingsService:
    return SettingsService(session, request.app.state.settings.data_dir)


def get_document_service(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> DocumentService:
    return DocumentService(
        session=session,
        database=request.app.state.database,
        vector_store=request.app.state.vector_store,
        embedding_provider_factory=request.app.state.embedding_provider_factory,
        data_dir=request.app.state.settings.data_dir,
        llm_provider_factory=request.app.state.llm_provider_factory,
    )


def get_chat_service(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> ChatService:
    app_settings = SettingsService(session, request.app.state.settings.data_dir).get()
    return ChatService(
        session=session,
        vector_store=request.app.state.vector_store,
        embedding_provider_factory=request.app.state.embedding_provider_factory,
        llm_provider_factory=request.app.state.llm_provider_factory,
        similarity_threshold=app_settings.retrieval.similarity_threshold,
        reranker_enabled=app_settings.retrieval.reranker_enabled,
        reranker_backend=request.app.state.settings.reranker_backend,
        data_dir=request.app.state.settings.data_dir,
        session_service=SessionService(session),
    )


def get_session_service(
    session: Annotated[Session, Depends(get_db)],
) -> SessionService:
    return SessionService(session)


def get_knowledge_search_service(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> KnowledgeSearchService:
    return KnowledgeSearchService(
        session=session,
        vector_store=request.app.state.vector_store,
        embedding_provider_factory=request.app.state.embedding_provider_factory,
    )


def get_model_service(
    session: Annotated[Session, Depends(get_db)],
) -> ModelService:
    return ModelService(session)


def get_index_service(
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> IndexService:
    return IndexService(
        session=session,
        database=request.app.state.database,
        data_dir=request.app.state.settings.data_dir,
        embedding_provider_factory=request.app.state.embedding_provider_factory,
        store_factory=request.app.state.index_store_factory,
        llm_provider_factory=request.app.state.llm_provider_factory,
    )
