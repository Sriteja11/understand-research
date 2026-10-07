from typing import List, Optional
from pydantic import BaseModel, Field


class AudioWordTimestamp(BaseModel):
    word: str
    start: float
    end: float
    probability: float = 1.0


class AudioTranscriptionResponse(BaseModel):
    text: str = Field(..., description="Transcribed text content")
    language: str = Field(default="", description="Detected or specified ISO language code")
    ttft_ms: float = Field(default=0.0, description="Time to first token in milliseconds")
    decode_tps: float = Field(default=0.0, description="Tokens per second during decoding")
    duration_s: float = Field(default=0.0, description="Audio duration in seconds")
    words: Optional[List[AudioWordTimestamp]] = Field(default=None, description="Optional word-level timestamps")
    silence: bool = Field(default=False, description="True if input audio was detected as silence")


class AudioStatusResponse(BaseModel):
    available: bool = Field(..., description="Whether Whistle engine is initialized and available")
    model_name: str = Field(default="Whistle", description="Name of the speech model")
    engine: str = Field(default="cactus-needle", description="Inference engine runtime")
    model_size_mb: float = Field(default=16.9, description="Model file size in megabytes")
    supported_languages: List[str] = Field(default_factory=list, description="Supported language ISO codes")
    default_keywords_count: int = Field(default=0, description="Number of built-in domain keywords configured")
