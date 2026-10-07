from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from backend.app.schemas.audio import AudioTranscriptionResponse, AudioStatusResponse
from backend.app.services.audio_service import get_audio_service

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("/status", response_model=AudioStatusResponse)
async def audio_status():
    """Get the current status and capabilities of the Whistle speech engine."""
    service = get_audio_service()
    return service.get_status()


@router.post("/transcribe", response_model=AudioTranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file in WAV format (at most 30s)"),
    language: Optional[str] = Form(None, description="Optional ISO language code (e.g., 'en', 'de', 'fr')"),
    keywords: Optional[str] = Form(None, description="Optional comma-separated keyword biasing list"),
    word_timestamps: bool = Form(False, description="Whether to include word-level timestamps")
):
    """Transcribe an audio clip using the on-device Cactus Compute Whistle model."""
    service = get_audio_service()
    if not service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Speech-to-text service is unavailable. 'cactus-needle' is not installed or initialized."
        )

    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else None

        result = service.transcribe(
            audio_bytes=audio_bytes,
            language=language if language and language.strip() else None,
            keywords=keyword_list,
            word_timestamps=word_timestamps
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio transcription error: {str(e)}")
