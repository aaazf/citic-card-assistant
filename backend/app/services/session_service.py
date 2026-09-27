import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.models.base import utcnow
from app.models.conversation import Conversation, Message, MessageRole
from app.models.knowledge import KnowledgeBase
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.conversation import ConversationRead, ConversationSummary


class SessionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ConversationRepository(session)

    def hot_questions(self, limit: int = 4) -> list[dict[str, object]]:
        """Most frequent first questions of customer conversations."""
        statement = (
            select(Conversation.id, Message.content)
            .join(Message, Message.conversation_id == Conversation.id)
            .where(Conversation.channel == "customer", Message.role == MessageRole.USER)
            .order_by(Conversation.id, Message.created_at)
        )
        first_by_conversation: dict[str, str] = {}
        for conversation_id, content in self.session.execute(statement):
            first_by_conversation.setdefault(conversation_id, content)

        counts: dict[str, int] = {}
        display: dict[str, str] = {}
        for content in first_by_conversation.values():
            text = " ".join(content.split()).strip()
            normalized = re.sub(r"[\s，。？！?!,.、~～…；;:：]+", "", text).lower()
            if not 4 <= len(normalized) <= 30:
                continue
            counts[normalized] = counts.get(normalized, 0) + 1
            display.setdefault(normalized, text)

        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
        return [{"text": display[key], "count": count} for key, count in ranked]

    def list_conversations(self) -> list[ConversationSummary]:
        return [
            ConversationSummary.model_validate(conversation)
            for conversation in self.repository.list_all()
        ]

    def get_conversation(self, conversation_id: str) -> ConversationRead:
        conversation = self.repository.get(conversation_id, include_messages=True)
        if conversation is None:
            raise ResourceNotFoundError("Conversation", conversation_id)
        return ConversationRead.model_validate(conversation)

    def delete_conversation(self, conversation_id: str) -> None:
        conversation = self.repository.get(conversation_id)
        if conversation is None:
            raise ResourceNotFoundError("Conversation", conversation_id)
        self.repository.delete(conversation)
        self.session.commit()

    def ensure_conversation(
        self,
        conversation_id: str | None,
        first_message: str,
        knowledge_base_id: str | None = None,
        channel: str = "customer",
    ) -> Conversation:
        if (
            knowledge_base_id is not None
            and self.session.get(KnowledgeBase, knowledge_base_id) is None
        ):
            raise ResourceNotFoundError("Knowledge base", knowledge_base_id)

        if conversation_id is not None:
            conversation = self.repository.get(conversation_id)
            if conversation is None:
                raise ResourceNotFoundError("Conversation", conversation_id)
            if (
                knowledge_base_id is not None
                and conversation.knowledge_base_id != knowledge_base_id
            ):
                raise ResourceConflictError("Conversation scope cannot be changed.")
            return conversation

        title = " ".join(first_message.split()).strip()[:60] or "新对话"
        conversation = self.repository.create(
            title,
            knowledge_base_id=knowledge_base_id,
            channel=channel,
        )
        self.session.flush()
        return conversation

    def list_history(self, conversation_id: str) -> list[Message]:
        conversation = self.repository.get(conversation_id, include_messages=True)
        if conversation is None:
            raise ResourceNotFoundError("Conversation", conversation_id)
        return list(conversation.messages)

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        citations: list[dict[str, object]] | None = None,
    ) -> Message:
        conversation = self.repository.get(conversation_id)
        if conversation is None:
            raise ResourceNotFoundError("Conversation", conversation_id)
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations or [],
        )
        conversation.updated_at = utcnow()
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message
