from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.knowledge import KnowledgeBase


class KnowledgeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[KnowledgeBase]:
        statement = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
        return list(self.session.scalars(statement).all())

    def get(self, knowledge_base_id: str) -> KnowledgeBase | None:
        return self.session.get(KnowledgeBase, knowledge_base_id)

    def list_documents(self, knowledge_base_id: str) -> list[Document]:
        statement = select(Document).where(Document.knowledge_base_id == knowledge_base_id)
        return list(self.session.scalars(statement).all())

    def create(self, name: str, description: str | None) -> KnowledgeBase:
        knowledge_base = KnowledgeBase(name=name, description=description)
        self.session.add(knowledge_base)
        return knowledge_base

    def delete(self, knowledge_base: KnowledgeBase) -> None:
        self.session.delete(knowledge_base)
