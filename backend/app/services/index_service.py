import logging
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Database
from app.core.exceptions import (
    ProviderConfigurationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.models.base import utcnow
from app.models.chunk import ChunkRecord
from app.models.document import Document
from app.models.index import (
    IndexDocument,
    IndexDocumentStatus,
    IndexVersion,
    IndexVersionStatus,
)
from app.models.settings import ModelKind
from app.providers.factory import EmbeddingProviderFactory, LLMProviderFactory
from app.rag.loader import LocalDocumentLoader
from app.rag.semantic import SmartSplitter
from app.rag.splitter import RecursiveTextSplitter
from app.repositories.index_repository import IndexRepository
from app.repositories.settings_repository import SettingsRepository
from app.schemas.index import IndexListResponse, IndexVersionRead
from app.vectorstores.active import LEGACY_COLLECTION_NAME
from app.vectorstores.base import VectorStore

logger = logging.getLogger(__name__)

StoreFactory = Callable[[str], VectorStore]


class IndexService:
    def __init__(
        self,
        session: Session,
        database: Database,
        data_dir: Path,
        embedding_provider_factory: EmbeddingProviderFactory,
        store_factory: StoreFactory,
        llm_provider_factory: LLMProviderFactory | None = None,
    ) -> None:
        self.session = session
        self.database = database
        self.data_dir = data_dir
        self.embedding_provider_factory = embedding_provider_factory
        self.store_factory = store_factory
        self.llm_provider_factory = llm_provider_factory
        self.repository = IndexRepository(session)
        self.loader = LocalDocumentLoader()
        self.splitter = RecursiveTextSplitter()

    def list_versions(self) -> IndexListResponse:
        self._ensure_legacy_version()
        active_version_id = self.repository.get_active_version_id()
        return IndexListResponse(
            active_version_id=active_version_id,
            versions=[
                self._read_version(version, active_version_id)
                for version in self.repository.list_versions()
            ],
        )

    def create_rebuild(self) -> IndexVersionRead:
        if self.repository.get_building_version() is not None:
            raise ResourceConflictError("已有索引正在重建，请等待当前任务完成。")
        config = SettingsRepository(self.session).get_model_config(ModelKind.EMBEDDING)
        if config is None or not config.enabled:
            raise ResourceConflictError("请先启用 Embedding 模型并完成连接测试。")
        if not config.provider.strip() or not config.model.strip() or not config.base_url:
            raise ResourceConflictError("Embedding Provider、Model 和 Base URL 不能为空。")
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        version = IndexVersion(
            collection_name=f"knowledge_chunks_{timestamp}_{uuid4().hex[:8]}",
            provider=config.provider.strip(),
            model=config.model,
            base_url=config.base_url,
            status=IndexVersionStatus.BUILDING,
            chunk_size=self.splitter.chunk_size,
            chunk_overlap=self.splitter.chunk_overlap,
        )
        self.session.add(version)
        self.session.commit()
        self.session.refresh(version)
        return self._read_version(version, self.repository.get_active_version_id())

    async def run_rebuild(self, version_id: str) -> None:
        try:
            await self._run_rebuild(version_id)
        except Exception as exc:
            logger.exception("index rebuild failed version_id=%s", version_id)
            with self.database.session() as session:
                version = session.get(IndexVersion, version_id)
                if version is not None:
                    version.status = IndexVersionStatus.FAILED
                    version.error_message = str(exc)
                    session.commit()

    async def _run_rebuild(self, version_id: str) -> None:
        with self.database.session() as session:
            version = session.get(IndexVersion, version_id)
            if version is None:
                raise ResourceNotFoundError("Index version", version_id)
            config = SettingsRepository(session).get_model_config(ModelKind.EMBEDDING)
            if config is None or not config.enabled:
                raise ResourceConflictError("Embedding 模型已不可用。")
            if (
                config.provider.strip().lower() != version.provider.lower()
                or config.model != version.model
                or (config.base_url or "").rstrip("/") != (version.base_url or "").rstrip("/")
            ):
                raise ResourceConflictError("重建期间 Embedding 配置发生变化，已停止任务。")
            documents = list(session.scalars(select(Document).order_by(Document.created_at)))
            version.total_documents = len(documents)
            collection_name = version.collection_name
            for document in documents:
                session.add(
                    IndexDocument(
                        index_version_id=version.id,
                        document_id=document.id,
                        status=IndexDocumentStatus.PENDING,
                    )
                )
            session.commit()
            provider = self.embedding_provider_factory(session)

        probes = await provider.embed(["index dimension probe"])
        if not probes or not probes[0]:
            raise ValueError("Embedding provider returned an empty dimension probe.")
        dimension = len(probes[0])
        store = self.store_factory(collection_name)
        collection = getattr(store, "collection", None)
        if collection is not None:
            metadata = {
                key: value
                for key, value in (collection.metadata or {}).items()
                if key != "hnsw:space"
            }
            metadata.update(
                {
                    "embedding_provider": version.provider,
                    "embedding_model": version.model,
                    "embedding_dimension": dimension,
                    "chunk_size": version.chunk_size,
                    "chunk_overlap": version.chunk_overlap,
                    "index_schema_version": 1,
                }
            )
            collection.modify(metadata=metadata)

        with self.database.session() as session:
            version = session.get(IndexVersion, version_id)
            if version is None:
                raise ResourceNotFoundError("Index version", version_id)
            version.dimension = dimension
            session.commit()

        for item in self._pending_items(version_id):
            await self._rebuild_document(version_id, item.document_id, provider, store)

        with self.database.session() as session:
            version = session.get(IndexVersion, version_id)
            if version is None:
                raise ResourceNotFoundError("Index version", version_id)
            version.status = (
                IndexVersionStatus.FAILED
                if version.failed_documents
                else IndexVersionStatus.READY
            )
            if version.failed_documents:
                version.error_message = f"{version.failed_documents} 份资料处理失败。"
            session.commit()

    async def activate(self, version_id: str) -> IndexVersionRead:
        version = self.repository.get_version(version_id)
        if version is None:
            raise ResourceNotFoundError("Index version", version_id)
        if version.status is not IndexVersionStatus.READY:
            raise ResourceConflictError("只有构建完成的索引才能切换。")
        store = self.store_factory(version.collection_name)
        count = getattr(store, "count", lambda: None)()
        dimension = getattr(store, "dimension", lambda: None)()
        expected_chunks = version.total_chunks
        if isinstance(count, int) and count != expected_chunks:
            raise ResourceConflictError(
                f"索引校验失败：记录片段数 {count}，期望 {expected_chunks}。"
            )
        if isinstance(dimension, int) and version.dimension and dimension != version.dimension:
            raise ResourceConflictError(
                f"索引校验失败：向量维度 {dimension}，期望 {version.dimension}。"
            )
        self.repository.set_active_version(version.id)
        version.activated_at = utcnow()
        self.session.commit()
        return self._read_version(version, version.id)

    def assert_uploads_allowed(self) -> None:
        if self.repository.get_building_version() is not None:
            raise ResourceConflictError("索引正在重建，当前暂不能上传新资料。")

    async def _rebuild_document(
        self,
        version_id: str,
        document_id: str,
        provider,
        store: VectorStore,
    ) -> None:
        with self.database.session() as session:
            document = session.get(Document, document_id)
            item = session.get(IndexDocument, (version_id, document_id))
            if document is None or item is None:
                return
            item.status = IndexDocumentStatus.PROCESSING
            item.error_message = None
            storage_path = Path(document.storage_path)
            session.commit()

        try:
            loaded = self.loader.load(storage_path)
            llm_provider = None
            if self.llm_provider_factory is not None:
                with self.database.session() as llm_session:
                    try:
                        llm_provider = self.llm_provider_factory(llm_session)
                    except ProviderConfigurationError:
                        llm_provider = None
            smart_splitter = SmartSplitter(llm_provider=llm_provider, guard=self.splitter)
            outcomes = [
                await smart_splitter.split(section.content, section.metadata)
                for section in loaded.sections
            ]
            chunks = [
                chunk
                for outcome in outcomes
                for chunk in outcome.chunks
            ]
            if not chunks:
                raise ValueError("No extractable text was found in the document.")
            embeddings = await provider.embed([chunk.content for chunk in chunks])
            if len(embeddings) != len(chunks):
                raise ValueError("Embedding count does not match chunk count.")
            records = [
                ChunkRecord(
                    id=f"{document_id}:{index}",
                    document_id=document_id,
                    knowledge_base_id=document.knowledge_base_id,
                    content=chunk.content,
                    metadata={
                        "filename": document.filename,
                        "file_type": document.file_type,
                        "chunk_index": index,
                        "index_version_id": version_id,
                        **chunk.metadata,
                    },
                    embedding=embedding,
                )
                for index, (chunk, embedding) in enumerate(
                    zip(chunks, embeddings, strict=True)
                )
            ]
            store.add(records)
            with self.database.session() as session:
                item = session.get(IndexDocument, (version_id, document_id))
                version = session.get(IndexVersion, version_id)
                if item is not None:
                    item.status = IndexDocumentStatus.READY
                    item.chunk_count = len(records)
                if version is not None:
                    version.processed_documents += 1
                    version.total_chunks += len(records)
                session.commit()
        except Exception as exc:
            logger.exception("document rebuild failed document_id=%s", document_id)
            with self.database.session() as session:
                item = session.get(IndexDocument, (version_id, document_id))
                version = session.get(IndexVersion, version_id)
                if item is not None:
                    item.status = IndexDocumentStatus.FAILED
                    item.error_message = str(exc)
                if version is not None:
                    version.processed_documents += 1
                    version.failed_documents += 1
                session.commit()

    def _pending_items(self, version_id: str) -> list[IndexDocument]:
        with self.database.session() as session:
            return IndexRepository(session).list_index_documents(version_id)

    def _ensure_legacy_version(self) -> None:
        if self.repository.list_versions() or self.repository.get_active_version_id():
            return
        store = self.store_factory(LEGACY_COLLECTION_NAME)
        count = getattr(store, "count", lambda: 0)()
        dimension = getattr(store, "dimension", lambda: None)()
        if not count:
            return
        total_documents = len(list(self.session.scalars(select(Document))))
        version = IndexVersion(
            collection_name=LEGACY_COLLECTION_NAME,
            provider="legacy",
            model="unknown",
            dimension=dimension or 0,
            status=IndexVersionStatus.READY,
            total_documents=total_documents,
            processed_documents=total_documents,
            total_chunks=int(count),
            activated_at=utcnow(),
        )
        self.session.add(version)
        self.session.flush()
        self.repository.set_active_version(version.id)
        self.session.commit()

    @staticmethod
    def _read_version(version: IndexVersion, active_version_id: str | None) -> IndexVersionRead:
        return IndexVersionRead(
            id=version.id,
            collection_name=version.collection_name,
            provider=version.provider,
            model=version.model,
            base_url=version.base_url,
            dimension=version.dimension,
            chunk_size=version.chunk_size,
            chunk_overlap=version.chunk_overlap,
            status=version.status,
            total_documents=version.total_documents,
            processed_documents=version.processed_documents,
            failed_documents=version.failed_documents,
            total_chunks=version.total_chunks,
            error_message=version.error_message,
            is_active=version.id == active_version_id,
            created_at=version.created_at,
            updated_at=version.updated_at,
            activated_at=version.activated_at,
        )
