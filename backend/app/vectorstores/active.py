from collections.abc import Callable

from app.core.database import Database
from app.core.exceptions import ResourceConflictError
from app.models.chunk import ChunkRecord
from app.models.index import IndexVersion, IndexVersionStatus
from app.models.settings import ModelKind
from app.rag.types import RetrievedChunk
from app.repositories.index_repository import IndexRepository
from app.repositories.settings_repository import SettingsRepository
from app.vectorstores.base import VectorStore

LEGACY_COLLECTION_NAME = "knowledge_chunks"


class ActiveVectorStore:
    """Routes vector operations to the active index version.

    Rebuilds write to a separate collection, so the active version remains
    queryable until an explicit, validated switch.
    """

    def __init__(
        self,
        database: Database,
        store_factory: Callable[[str], VectorStore],
    ) -> None:
        self.database = database
        self.store_factory = store_factory
        self._stores: dict[str, VectorStore] = {}

    def add(self, records: list[ChunkRecord]) -> None:
        version = self._active_version()
        self._validate_embedding(version, records[0].embedding if records else None)
        self._store(version).add(records)

    def get_chunk(self, chunk_id: str) -> ChunkRecord | None:
        return self._store(self._active_version()).get_chunk(chunk_id)

    def list_chunks(self, document_id: str) -> list[ChunkRecord]:
        return self._store(self._active_version()).list_chunks(document_id)

    @property
    def collection_name(self) -> str:
        version = self._active_version()
        return version.collection_name if version else LEGACY_COLLECTION_NAME

    def count(self) -> int:
        store = self._store(self._active_version())
        counter = getattr(store, "count", None)
        return int(counter()) if callable(counter) else 0

    def list_all_chunks(self) -> list[RetrievedChunk]:
        store = self._store(self._active_version())
        lister = getattr(store, "list_all_chunks", None)
        return list(lister()) if callable(lister) else []

    def keyword_search(
        self,
        terms: list[str],
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        return self._store(self._active_version()).keyword_search(terms, top_k, where)

    def delete_document(self, document_id: str) -> None:
        with self.database.session() as session:
            versions = IndexRepository(session).list_versions()
        ready_versions = [
            version for version in versions if version.status is IndexVersionStatus.READY
        ]
        stores = [self._store(version) for version in ready_versions]
        if not stores:
            stores = [self._store(None)]
        for store in stores:
            store.delete_document(document_id)

    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        version = self._active_version()
        self._validate_embedding(version, embedding)
        return self._store(version).query(embedding, top_k, where)

    def _active_version(self) -> IndexVersion | None:
        with self.database.session() as session:
            return IndexRepository(session).get_active_version()

    def _store(self, version: IndexVersion | None) -> VectorStore:
        collection_name = version.collection_name if version else LEGACY_COLLECTION_NAME
        if collection_name not in self._stores:
            self._stores[collection_name] = self.store_factory(collection_name)
        return self._stores[collection_name]

    def _validate_embedding(
        self,
        version: IndexVersion | None,
        embedding: list[float] | None,
    ) -> None:
        if version is None or embedding is None:
            return
        if version.dimension and len(embedding) != version.dimension:
            raise ResourceConflictError(
                "当前索引由 "
                f"{version.model}（{version.dimension} 维）建立，"
                f"当前查询向量为 {len(embedding)} 维。"
                "请恢复原 Embedding 模型，或在设置中重建索引。"
            )
        if version.provider == "legacy" or version.model == "unknown":
            return

        with self.database.session() as session:
            config = SettingsRepository(session).get_model_config(ModelKind.EMBEDDING)
        if config is None:
            raise ResourceConflictError("Embedding 模型未配置，无法使用当前索引。")
        current_provider = config.provider.strip().lower()
        current_base_url = (config.base_url or "").rstrip("/")
        version_base_url = (version.base_url or "").rstrip("/")
        if (
            current_provider != version.provider.strip().lower()
            or config.model != version.model
            or current_base_url != version_base_url
        ):
            raise ResourceConflictError(
                "当前 Embedding 配置与激活索引不一致。"
                "请恢复建索引时使用的模型，或在设置中重建索引后再切换。"
            )
