from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.chat_service import get_chat_service

router = APIRouter(tags=["chat"])

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Stream evidence-grounded chat response via SSE."""
    service = get_chat_service()
    try:
        generator = service.chat_stream(
            query=request.message,
            session_id=request.session_id,
            top_k=request.top_k or 10
        )
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")

@router.post("/chat/sync", response_model=ChatResponse)
async def chat_sync_endpoint(request: ChatRequest):
    """Synchronous chat endpoint for non-streaming clients and testing."""
    service = get_chat_service()
    try:
        return await service.execute_chat(
            query=request.message,
            session_id=request.session_id,
            top_k=request.top_k or 10
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")

