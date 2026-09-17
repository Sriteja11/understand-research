from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SessionModel(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MessageModel(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    metadata_json: Optional[str] = None
    created_at: Optional[datetime] = None


class DocumentModel(BaseModel):
    id: str
    filename: str
    path: str
    file_type: str
    file_size: int = 0
    status: str
    is_seed: bool = False
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IndexingJobModel(BaseModel):
    id: str
    document_id: str
    status: str
    progress: int = 0
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class EvaluationResultModel(BaseModel):
    id: str
    run_id: str
    question_id: str
    question_text: str
    question_type: str
    retrieval_hit: bool
    citation_correct: bool
    grounded: bool
    refusal_correct: bool
    latency_ms: float
    answer_preview: Optional[str] = None
    details_json: Optional[str] = None
    created_at: Optional[datetime] = None

