from datetime import datetime

from app.models.conversation import MessageRole
from app.schemas.chat import Citation
from app.schemas.common import APIModel


class MessageRead(APIModel):
    id: str
    role: MessageRole
    content: str
    citations: list[Citation]
    created_at: datetime


class ConversationSummary(APIModel):
    id: str
    channel: str = "customer"
    knowledge_base_id: str | None = None
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationRead(ConversationSummary):
    messages: list[MessageRead]
