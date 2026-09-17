import asyncio
from typing import List
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from backend.app.schemas.documents import DocumentResponse, DocumentUploadResponse, IndexingStatusResponse
from backend.app.services.document_service import get_document_service
from backend.app.services.indexing_service import get_indexing_service

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload document (.pdf, .txt, .md) and trigger background indexing."""
    doc_service = get_document_service()
    idx_service = get_indexing_service()

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    content = await file.read()
    try:
        doc_id, job_id, saved_path = doc_service.create_uploaded_document(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Trigger background indexing
    background_tasks.add_task(
        idx_service.index_document,
        document_id=doc_id,
        job_id=job_id,
        file_path=saved_path,
        filename=file.filename
    )

    return DocumentUploadResponse(
        document_id=doc_id,
        filename=file.filename,
        status="QUEUED",
        job_id=job_id,
        message="Document uploaded. Indexing in progress."
    )

@router.get("", response_model=List[DocumentResponse])
async def list_documents():
    """List all seed and uploaded documents."""
    doc_service = get_document_service()
    docs = doc_service.list_documents()
    return [
        DocumentResponse(
            id=d["id"],
            filename=d["filename"],
            file_type=d["file_type"],
            file_size=d["file_size"],
            status=d["status"],
            is_seed=bool(d.get("is_seed", 0)),
            error=d.get("error"),
            created_at=str(d.get("created_at", "")),
            updated_at=str(d.get("updated_at", ""))
        )
        for d in docs
    ]

@router.get("/{document_id}/status", response_model=IndexingStatusResponse)
async def get_document_status(document_id: str):
    """Retrieve indexing status and percentage progress."""
    doc_service = get_document_service()
    job = doc_service.get_indexing_job(document_id)
    if not job:
        raise HTTPException(status_code=404, detail="Document job not found.")
    return IndexingStatusResponse(
        document_id=document_id,
        job_id=job["id"],
        status=job["status"],
        progress=job["progress"],
        error=job.get("error")
    )

@router.get("/{document_id}/events")
async def stream_document_events(document_id: str):
    """Stream indexing progress updates via SSE."""
    idx_service = get_indexing_service()
    generator = idx_service.stream_indexing_progress(document_id)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document from vector index and database."""
    doc_service = get_document_service()
    success = doc_service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"message": f"Document {document_id} deleted successfully."}

