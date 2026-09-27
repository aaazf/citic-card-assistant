from datetime import datetime

from app.models.index import IndexVersionStatus
from app.schemas.common import APIModel


class IndexVersionRead(APIModel):
    id: str
    collection_name: str
    provider: str
    model: str
    base_url: str | None
    dimension: int
    chunk_size: int
    chunk_overlap: int
    status: IndexVersionStatus
    total_documents: int
    processed_documents: int
    failed_documents: int
    total_chunks: int
    error_message: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None


class IndexListResponse(APIModel):
    active_version_id: str | None
    versions: list[IndexVersionRead]
