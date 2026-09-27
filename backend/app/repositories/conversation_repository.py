from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[Conversation]:
        statement = select(Conversation).order_by(Conversation.updated_at.desc())
        return list(self.session.scalars(statement).all())

    def get(self, conversation_id: str, include_messages: bool = False) -> Conversation | None:
        if not include_messages:
            return self.session.get(Conversation, conversation_id)
        statement = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return self.session.scalar(statement)

    def create(
        self,
        title: str,
        knowledge_base_id: str | None = None,
        channel: str = "customer",
    ) -> Conversation:
        conversation = Conversation(
            title=title,
            knowledge_base_id=knowledge_base_id,
            channel=channel,
        )
        self.session.add(conversation)
        return conversation

    def delete(self, conversation: Conversation) -> None:
        self.session.delete(conversation)
