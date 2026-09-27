from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.providers.factory import EmbeddingProviderFactory
from app.repositories.knowledge_repository import KnowledgeRepository
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseRead
from app.schemas.search import KnowledgeSearchResult
from app.services.retrieval_service import RetrievalService
from app.vectorstores.base import VectorStore


class KnowledgeService:
    def __init__(
        self,
        session: Session,
        repository: KnowledgeRepository | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or KnowledgeRepository(session)
        self.vector_store = vector_store

    def list(self) -> list[KnowledgeBaseRead]:
        return [
            KnowledgeBaseRead.model_validate(knowledge_base)
            for knowledge_base in self.repository.list_all()
        ]

    def create(self, payload: KnowledgeBaseCreate) -> KnowledgeBaseRead:
        knowledge_base = self.repository.create(payload.name, payload.description)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ResourceConflictError(
                f"Knowledge base '{payload.name}' already exists."
            ) from exc
        self.session.refresh(knowledge_base)
        return KnowledgeBaseRead.model_validate(knowledge_base)

    def delete(self, knowledge_base_id: str) -> None:
        knowledge_base = self.repository.get(knowledge_base_id)
        if knowledge_base is None:
            raise ResourceNotFoundError("Knowledge base", knowledge_base_id)

        for document in self.repository.list_documents(knowledge_base_id):
            if self.vector_store is not None:
                self.vector_store.delete_document(document.id)
            storage_path = Path(document.storage_path)
            if storage_path.exists():
                storage_path.unlink()
            self.session.delete(document)

        self.repository.delete(knowledge_base)
        self.session.commit()


class KnowledgeSearchService:
    """Structured retrieval service used by the Agent API and MCP adapter."""

    def __init__(
        self,
        session: Session,
        vector_store: VectorStore,
        embedding_provider_factory: EmbeddingProviderFactory,
    ) -> None:
        self.session = session
        self.vector_store = vector_store
        self.embedding_provider_factory = embedding_provider_factory

    async def search(self, query: str, top_k: int) -> list[KnowledgeSearchResult]:
        provider = self.embedding_provider_factory(self.session)
        retrieval = RetrievalService(provider, self.vector_store)
        results = await retrieval.retrieve(query, top_k)
        return [
            KnowledgeSearchResult(
                document_id=result.document_id,
                content=result.content,
                score=result.score,
                metadata={**result.metadata, "chunk_id": result.chunk_id},
            )
            for result in results
        ]
