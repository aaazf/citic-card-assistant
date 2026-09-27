from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.usage_service import UsageService

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/summary")
def get_usage_summary(session: Annotated[Session, Depends(get_db)]) -> dict:
    return UsageService(session).summary()
