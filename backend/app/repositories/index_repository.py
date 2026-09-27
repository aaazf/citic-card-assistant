from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.index import IndexDocument, IndexVersion, IndexVersionStatus
from app.models.settings import SystemSetting

ACTIVE_INDEX_KEY = "active_index_version_id"


class IndexRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_versions(self) -> list[IndexVersion]:
        statement = select(IndexVersion).order_by(IndexVersion.created_at.desc())
        return list(self.session.scalars(statement))

    def get_version(self, version_id: str) -> IndexVersion | None:
        return self.session.get(IndexVersion, version_id)

    def get_building_version(self) -> IndexVersion | None:
        statement = select(IndexVersion).where(
            IndexVersion.status == IndexVersionStatus.BUILDING
        )
        return self.session.scalar(statement)

    def get_active_version_id(self) -> str | None:
        setting = self.session.get(SystemSetting, ACTIVE_INDEX_KEY)
        if setting is None:
            return None
        value = setting.value.get("version_id")
        return str(value) if value else None

    def set_active_version(self, version_id: str) -> None:
        setting = self.session.get(SystemSetting, ACTIVE_INDEX_KEY)
        value = {"version_id": version_id}
        if setting is None:
            self.session.add(SystemSetting(key=ACTIVE_INDEX_KEY, value=value))
        else:
            setting.value = value

    def get_active_version(self) -> IndexVersion | None:
        version_id = self.get_active_version_id()
        return self.get_version(version_id) if version_id else None

    def list_index_documents(self, version_id: str) -> list[IndexDocument]:
        statement = select(IndexDocument).where(IndexDocument.index_version_id == version_id)
        return list(self.session.scalars(statement))

    def get_index_document(self, version_id: str, document_id: str) -> IndexDocument | None:
        return self.session.get(IndexDocument, (version_id, document_id))
