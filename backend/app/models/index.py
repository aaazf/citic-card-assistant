from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_uuid


class IndexVersionStatus(StrEnum):
    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"


class IndexDocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class IndexVersion(TimestampMixin, Base):
    __tablename__ = "index_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    collection_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimension: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_size: Mapped[int] = mapped_column(Integer, default=800, nullable=False)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    status: Mapped[IndexVersionStatus] = mapped_column(
        SQLAlchemyEnum(IndexVersionStatus, native_enum=False, length=20),
        default=IndexVersionStatus.BUILDING,
        index=True,
        nullable=False,
    )
    total_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_documents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IndexDocument(TimestampMixin, Base):
    __tablename__ = "index_documents"

    index_version_id: Mapped[str] = mapped_column(
        ForeignKey("index_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[IndexDocumentStatus] = mapped_column(
        SQLAlchemyEnum(IndexDocumentStatus, native_enum=False, length=20),
        default=IndexDocumentStatus.PENDING,
        nullable=False,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
