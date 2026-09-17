from typing import List, Optional
from pydantic import BaseModel, Field

class Citation(BaseModel):
    document: str
    chunk_id: str
    page: int


class EvidenceItem(BaseModel):
    document: str
    chunk_id: str
    page: int
    section: str = "General"
    text: str
    score: float


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=2000)
    top_k: Optional[int] = Field(default=10, ge=1, le=50)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    evidence: List[EvidenceItem] = Field(default_factory=list)
    inference: str = ""
    citations: List[Citation] = Field(default_factory=list)
    grounded: bool = True
    latency_ms: float = 0.0

