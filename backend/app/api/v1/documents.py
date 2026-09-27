from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from app.api.deps import get_document_service
from app.core.exceptions import ResourceNotFoundError
from app.schemas.common import ErrorResponse
from app.schemas.document import DocumentChunkRead, DocumentRead
from app.services.document_service import DocumentService, DocumentUpload

router = APIRouter(prefix="/documents", tags=["documents"])
ServiceDependency = Annotated[DocumentService, Depends(get_document_service)]


@router.get("", response_model=list[DocumentRead])
def list_documents(
    service: ServiceDependency,
    knowledge_base_id: str | None = None,
) -> list[DocumentRead]:
    return service.list_documents(knowledge_base_id)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: str, service: ServiceDependency) -> DocumentRead:
    try:
        return service.get_document(document_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{document_id}/content")
def get_document_content(document_id: str, service: ServiceDependency) -> FileResponse:
    try:
        document = service.get_document(document_id)
        path = service.get_content_path(document_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    media_types = {
        ".pdf": "application/pdf",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/plain; charset=utf-8",
        ".markdown": "text/plain; charset=utf-8",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".epub": "application/epub+zip",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }
    return FileResponse(
        path,
        media_type=media_types.get(path.suffix.lower(), "application/octet-stream"),
        filename=document.filename,
        content_disposition_type="inline",
    )


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkRead])
def list_document_chunks(
    document_id: str,
    service: ServiceDependency,
) -> list[DocumentChunkRead]:
    try:
        return service.list_chunks(document_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{document_id}/chunks/{chunk_id}", response_model=DocumentChunkRead)
def get_document_chunk(
    document_id: str,
    chunk_id: str,
    service: ServiceDependency,
) -> DocumentChunkRead:
    try:
        return service.get_chunk(document_id, chunk_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    service: ServiceDependency,
    file: UploadFile = File(...),
    knowledge_base_id: str = Form(...),
) -> DocumentRead:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required.")
    try:
        document = service.upload(
            DocumentUpload(
                knowledge_base_id=knowledge_base_id,
                filename=file.filename,
                content_type=file.content_type,
                content=await file.read(),
            )
        )
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    background_tasks.add_task(service.process, document.id)
    return document


@router.delete("/{document_id}", response_model=ErrorResponse)
def delete_document(document_id: str, service: ServiceDependency) -> ErrorResponse:
    try:
        service.delete(document_id)
    except ResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ErrorResponse(detail="Document deleted.")
