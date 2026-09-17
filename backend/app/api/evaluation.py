from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from backend.app.schemas.evaluation import EvaluationSummaryResponse
from backend.app.services.evaluation_service import get_evaluation_service

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

@router.get("", response_model=Optional[EvaluationSummaryResponse])
async def get_evaluation_results():
    """Retrieve latest evaluation metrics and test results."""
    eval_service = get_evaluation_service()
    data = eval_service.get_latest_results()
    if not data:
        return None
    return EvaluationSummaryResponse(**data)

@router.post("/run", response_model=EvaluationSummaryResponse)
async def run_evaluation(limit: Optional[int] = Query(None, description="Optional limit of test cases")):
    """Run evaluation suite against benchmark dataset."""
    eval_service = get_evaluation_service()
    try:
        summary = await eval_service.run_evaluation(limit=limit)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

