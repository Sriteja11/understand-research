from typing import Optional
from pydantic import BaseModel

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    is_seed: bool
    error: Optional[str] = None
    created_at: str
    updated_at: str


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    job_id: str
    message: str


class IndexingStatusResponse(BaseModel):
    document_id: str
    job_id: str
    status: str
    progress: int
    error: Optional[str] = None

