from typing import List, Optional
from pydantic import BaseModel

class EvaluationResultItem(BaseModel):
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
    created_at: str


class EvaluationSummaryResponse(BaseModel):
    run_id: str
    total_questions: int
    retrieval_hit_rate: float
    citation_accuracy: float
    groundedness_rate: float
    refusal_accuracy: float
    avg_latency_ms: float
    results: List[EvaluationResultItem]

