from fastapi import HTTPException, status

from app.schemas.common import ErrorResponse

NOT_IMPLEMENTED_RESPONSES = {
    status.HTTP_501_NOT_IMPLEMENTED: {
        "model": ErrorResponse,
        "description": "Feature is reserved for a later implementation phase.",
    }
}


def not_implemented(feature: str, phase: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"{feature} is reserved for {phase}.",
    )
