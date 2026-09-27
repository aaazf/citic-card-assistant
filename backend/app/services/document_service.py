import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Database
from app.core.exceptions import ResourceNotFoundError
from app.models.base import new_uuid
from app.models.chunk import ChunkRecord
from app.models.document import Document, DocumentStatus
from app.models.knowledge import KnowledgeBase
from app.providers.factory import EmbeddingProviderFactory, LLMProviderFactory
from app.rag.loader import SUPPORTED_DOCUMENT_EXTENSIONS, LocalDocumentLoader
from app.rag.semantic import SmartSplitter
from app.rag.splitter import RecursiveTextSplitter
from app.repositories.index_repository import IndexRepository
from app.schemas.document import DocumentChunkRead, DocumentRead
from app.vectorstores.base import VectorStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentUpload:
    knowledge_base_id: str
    filename: str
    content_type: str | None
    content: bytes


class DocumentService:
    def __init__(
        self,
        session: Session,
        database: Database,
        vector_store: VectorStore,
        embedding_provider_factory: EmbeddingProviderFactory,
        data_dir: Path,
        llm_provider_factory: LLMProviderFactory | None = None,
    ) -> None:
        self.session = session
        self.database = database
        self.vector_store = vector_store
        self.embedding_provider_factory = embedding_provider_factory
        self.data_dir = data_dir
        self.llm_provider_factory = llm_provider_factory
        self.loader = LocalDocumentLoader()
        self.splitter = RecursiveTextSplitter()

    def _build_llm_provider(self, session: Session):
        if self.llm_provider_factory is None:
            return None
        try:
            return self.llm_provider_factory(session)
        except Exception:
            logger.info("llm provider unavailable; semantic split disabled", exc_info=True)
            return None

    def list_documents(self, knowledge_base_id: str | None = None) -> list[DocumentRead]:
        statement = select(Document).order_by(Document.created_at.desc())
        if knowledge_base_id:
            statement = statement.where(Document.knowledge_base_id == knowledge_base_id)
        documents = self.session.scalars(statement)
        return [DocumentRead.model_validate(document) for document in documents]

    def upload(self, payload: DocumentUpload) -> DocumentRead:
        if IndexRepository(self.session).get_building_version() is not None:
            raise ValueError("Index rebuild is in progress; new uploads are temporarily disabled.")
        suffix = Path(payload.filename).suffix.lower()
        if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
            raise ValueError(
                "Only PDF, TXT, Markdown, DOCX, EPUB and image files are supported."
            )
        if self.session.get(KnowledgeBase, payload.knowledge_base_id) is None:
            raise ResourceNotFoundError("Knowledge base", payload.knowledge_base_id)

        document_id = new_uuid()
        document = Document(
            id=document_id,
            knowledge_base_id=payload.knowledge_base_id,
            filename=Path(payload.filename).name,
            file_type=suffix.removeprefix("."),
            file_size=len(payload.content),
            storage_path="",
        )
        storage_path = (
            self.data_dir / "documents" / payload.knowledge_base_id / f"{document_id}{suffix}"
        )
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(payload.content)
        document.storage_path = str(storage_path)
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        logger.info(
            "document uploaded document_id=%s filename=%s size=%s",
            document.id,
            document.filename,
            document.file_size,
        )
        return DocumentRead.model_validate(document)

    async def process(self, document_id: str) -> None:
        with self.database.session() as session:
            document = session.get(Document, document_id)
            if document is None:
                return
            document.status = DocumentStatus.PROCESSING
            document.error_message = None
            session.commit()
            try:
                loaded = self.loader.load(Path(document.storage_path))
                smart_splitter = SmartSplitter(
                    llm_provider=self._build_llm_provider(session),
                    guard=self.splitter,
                )
                outcomes = [
                    await smart_splitter.split(section.content, section.metadata)
                    for section in loaded.sections
                ]
                text_chunks = [
                    chunk
                    for outcome in outcomes
                    for chunk in outcome.chunks
                ]
                if not text_chunks:
                    raise ValueError("No extractable text was found in the document.")

                provider = self.embedding_provider_factory(session)
                embeddings = await provider.embed([chunk.content for chunk in text_chunks])
                if len(embeddings) != len(text_chunks):
                    raise ValueError("Embedding count does not match chunk count.")

                records = [
                    ChunkRecord(
                        id=f"{document.id}:{index}",
                        document_id=document.id,
                        knowledge_base_id=document.knowledge_base_id,
                        content=chunk.content,
                        metadata={
                            "filename": document.filename,
                            "file_type": document.file_type,
                            "chunk_index": index,
                            **chunk.metadata,
                        },
                        embedding=embedding,
                    )
                    for index, (chunk, embedding) in enumerate(
                        zip(text_chunks, embeddings, strict=True)
                    )
                ]
                self.vector_store.add(records)
                document.status = DocumentStatus.READY
                document.chunk_count = len(records)
                session.commit()
                logger.info(
                    "document processed document_id=%s chunks=%s",
                    document.id,
                    document.chunk_count,
                )
            except Exception as exc:
                session.rollback()
                document = session.get(Document, document_id)
                if document is not None:
                    document.status = DocumentStatus.FAILED
                    document.error_message = str(exc)
                    session.commit()
                logger.exception("document processing failed document_id=%s", document_id)

    def get_document(self, document_id: str) -> DocumentRead:
        document = self.session.get(Document, document_id)
        if document is None:
            raise ResourceNotFoundError("Document", document_id)
        return DocumentRead.model_validate(document)

    def get_content_path(self, document_id: str) -> Path:
        document = self.session.get(Document, document_id)
        if document is None:
            raise ResourceNotFoundError("Document", document_id)
        path = Path(document.storage_path)
        if not path.exists():
            raise ResourceNotFoundError("Document file", document_id)
        return path

    def list_chunks(self, document_id: str) -> list[DocumentChunkRead]:
        if self.session.get(Document, document_id) is None:
            raise ResourceNotFoundError("Document", document_id)
        return [
            DocumentChunkRead(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                content=chunk.content,
                metadata=chunk.metadata,
            )
            for chunk in self.vector_store.list_chunks(document_id)
        ]

    def get_chunk(self, document_id: str, chunk_id: str) -> DocumentChunkRead:
        chunk = self.vector_store.get_chunk(chunk_id)
        if chunk is None or chunk.document_id != document_id:
            raise ResourceNotFoundError("Document chunk", chunk_id)
        return DocumentChunkRead(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            content=chunk.content,
            metadata=chunk.metadata,
        )

    def delete(self, document_id: str) -> None:
        document = self.session.get(Document, document_id)
        if document is None:
            raise ResourceNotFoundError("Document", document_id)
        self.vector_store.delete_document(document.id)
        storage_path = Path(document.storage_path)
        if storage_path.exists():
            storage_path.unlink()
        self.session.delete(document)
        self.session.commit()
