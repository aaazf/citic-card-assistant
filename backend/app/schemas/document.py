from datetime import datetime

from app.models.document import DocumentStatus
from app.schemas.common import APIModel


class DocumentRead(APIModel):
    id: str
    knowledge_base_id: str
    filename: str
    file_type: str
    file_size: int
    status: DocumentStatus
    chunk_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentChunkRead(APIModel):
    chunk_id: str
    document_id: str
    content: str
    metadata: dict[str, object]
