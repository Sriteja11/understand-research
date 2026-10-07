import io
import os
import wave
import tempfile
import threading
from typing import List, Optional, Tuple
import numpy as np

try:
    import needle
    from needle.agent.whistle import LANGUAGES as WHISTLE_LANGUAGES
except ImportError:
    needle = None
    WHISTLE_LANGUAGES = ("en", "de", "fr", "es", "it", "nl", "pl")

from backend.app.schemas.audio import AudioTranscriptionResponse, AudioWordTimestamp, AudioStatusResponse


DEFAULT_RESEARCH_KEYWORDS = [
    "Attention is all you need",
    "Transformer",
    "Multi-Head Attention",
    "Self-Attention",
    "Scaled Dot-Product",
    "Positional Encoding",
    "Feed Forward",
    "Retrieval-Augmented Generation",
    "RAG",
    "Dense Passage Retrieval",
    "ChromaDB",
    "Vector Database",
    "Cosine Similarity",
    "Cross-Encoder",
    "Reranker",
    "Sentence Transformers",
    "ReAct",
    "Reasoning and Acting",
    "Prompt Injection",
    "Jailbreak",
    "BLEU",
    "ROUGE",
    "Perplexity",
    "Hallucination",
    "Grounding",
    "Temperature",
    "Top-p",
    "Context Window",
    "Tokenization",
    "Embeddings"
]


class AudioService:
    """Service wrapping Cactus Compute Whistle for on-device speech-to-text."""

    def __init__(self):
        self._lock = threading.Lock()
        self._initialized = needle is not None

    def is_available(self) -> bool:
        return self._initialized

    def get_status(self) -> AudioStatusResponse:
        return AudioStatusResponse(
            available=self.is_available(),
            model_name="Whistle (16.9 MB)",
            engine="cactus-needle",
            model_size_mb=16.9,
            supported_languages=list(WHISTLE_LANGUAGES),
            default_keywords_count=len(DEFAULT_RESEARCH_KEYWORDS)
        )

    def _process_audio_bytes_to_16k_mono_wav(self, audio_bytes: bytes) -> Tuple[bytes, float]:
        """Convert arbitrary WAV audio bytes into standard 16 kHz mono 16-bit PCM WAV.

        Returns (wav_bytes, duration_seconds).
        """
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                n_channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                raw_frames = wf.readframes(n_frames)
        except Exception as e:
            raise ValueError(f"Invalid or unsupported WAV audio format: {e}")

        # Decode samples to int16 numpy array
        if sample_width == 2:
            samples = np.frombuffer(raw_frames, dtype=np.int16)
        elif sample_width == 1:
            # 8-bit unsigned to 16-bit signed
            samples = (np.frombuffer(raw_frames, dtype=np.uint8).astype(np.int16) - 128) * 256
        elif sample_width == 4:
            # 32-bit int to 16-bit int
            samples = (np.frombuffer(raw_frames, dtype=np.int32) >> 16).astype(np.int16)
        else:
            raise ValueError(f"Unsupported audio sample width: {sample_width} bytes")

        # Downmix multi-channel to mono
        if n_channels > 1:
            samples = samples.reshape(-1, n_channels).mean(axis=1).astype(np.int16)

        # Resample to 16,000 Hz if needed
        if framerate != 16000 and len(samples) > 0:
            target_length = max(1, int(len(samples) * 16000 / framerate))
            orig_indices = np.arange(len(samples))
            target_indices = np.linspace(0, len(samples) - 1, target_length)
            samples = np.interp(target_indices, orig_indices, samples).astype(np.int16)

        # Enforce Whistle's maximum 30-second audio window (30s * 16,000 samples = 480,000 samples)
        max_samples = 16000 * 30
        if len(samples) > max_samples:
            samples = samples[:max_samples]

        duration_s = round(len(samples) / 16000.0, 2)

        # Write clean 16 kHz mono WAV
        out_buf = io.BytesIO()
        with wave.open(out_buf, "wb") as out_wf:
            out_wf.setnchannels(1)
            out_wf.setsampwidth(2)
            out_wf.setframerate(16000)
            out_wf.writeframes(samples.tobytes())

        return out_buf.getvalue(), duration_s

    def transcribe(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        word_timestamps: bool = False
    ) -> AudioTranscriptionResponse:
        """Transcribe audio bytes using Cactus Compute Whistle."""
        if not self._initialized:
            raise RuntimeError("Cactus Needle / Whistle is not available in the current environment.")

        # Validate language parameter if provided
        if language:
            language = language.lower().strip()
            if language not in WHISTLE_LANGUAGES:
                raise ValueError(
                    f"Unsupported language code '{language}'. Supported languages: {', '.join(WHISTLE_LANGUAGES)}"
                )

        # Combine default AI research keywords with any custom keywords provided
        merged_keywords = list(DEFAULT_RESEARCH_KEYWORDS)
        if keywords:
            for kw in keywords:
                cleaned = kw.strip()
                if cleaned and cleaned not in merged_keywords:
                    merged_keywords.append(cleaned)

        # Convert/standardize audio to 16 kHz mono WAV
        processed_wav, duration_s = self._process_audio_bytes_to_16k_mono_wav(audio_bytes)

        # Whistle model is not thread-safe, so serialize inference calls
        with self._lock:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(processed_wav)
                tmp_path = tmp.name

            try:
                raw_result = needle.transcribe(
                    tmp_path,
                    language=language,
                    keywords=merged_keywords if merged_keywords else None,
                    word_timestamps=word_timestamps
                )
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

        text = raw_result.get("text", "").strip()
        detected_lang = raw_result.get("language", "")
        ttft_ms = float(raw_result.get("ttft_ms", 0.0))
        decode_tps = float(raw_result.get("decode_tps", 0.0))

        # Build word timestamps if present
        words_out = None
        if word_timestamps and "words" in raw_result:
            words_out = [
                AudioWordTimestamp(
                    word=w.get("word", ""),
                    start=float(w.get("start", 0.0)),
                    end=float(w.get("end", 0.0)),
                    probability=float(w.get("prob", w.get("probability", 1.0)))
                )
                for w in raw_result["words"]
            ]

        is_silence = (len(text) == 0 and duration_s > 0)

        return AudioTranscriptionResponse(
            text=text,
            language=detected_lang or (language or "unknown"),
            ttft_ms=ttft_ms,
            decode_tps=decode_tps,
            duration_s=duration_s,
            words=words_out,
            silence=is_silence
        )


_audio_service: Optional[AudioService] = None


def get_audio_service() -> AudioService:
    global _audio_service
    if _audio_service is None:
        _audio_service = AudioService()
    return _audio_service
