import io
import wave
import struct
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.audio_service import get_audio_service, AudioService


def create_sine_wav(sample_rate: int = 16000, channels: int = 1, duration_s: float = 1.0) -> bytes:
    """Helper to generate an in-memory PCM 16-bit WAV file."""
    buf = io.BytesIO()
    num_samples = int(sample_rate * duration_s)
    t = np.linspace(0, duration_s, num_samples, endpoint=False)
    # Generate 440 Hz tone
    samples = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)

    if channels == 2:
        interleaved = np.column_stack([samples, samples]).flatten()
        frames = interleaved.tobytes()
    else:
        frames = samples.tobytes()

    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)

    return buf.getvalue()


def test_audio_status_endpoint():
    client = TestClient(app)
    res = client.get("/audio/status")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is True
    assert "Whistle" in data["model_name"]
    assert data["engine"] == "cactus-needle"
    assert "en" in data["supported_languages"]
    assert data["default_keywords_count"] > 0


def test_audio_service_resampling():
    service = AudioService()
    # Generate 44.1kHz stereo WAV
    wav_44k = create_sine_wav(sample_rate=44100, channels=2, duration_s=0.5)
    processed_wav, duration_s = service._process_audio_bytes_to_16k_mono_wav(wav_44k)

    # Inspect the converted header
    with wave.open(io.BytesIO(processed_wav), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16000
        assert wf.getsampwidth() == 2

    assert 0.4 <= duration_s <= 0.6


def test_audio_transcribe_endpoint_valid_wav():
    client = TestClient(app)
    wav_bytes = create_sine_wav(sample_rate=16000, channels=1, duration_s=1.0)

    files = {"file": ("test.wav", wav_bytes, "audio/wav")}
    data = {"language": "en"}
    res = client.post("/audio/transcribe", files=files, data=data)

    assert res.status_code == 200
    resp_json = res.json()
    assert "text" in resp_json
    assert "language" in resp_json
    assert "ttft_ms" in resp_json
    assert "decode_tps" in resp_json
    assert resp_json["duration_s"] == 1.0


def test_audio_transcribe_unsupported_language():
    client = TestClient(app)
    wav_bytes = create_sine_wav(sample_rate=16000, channels=1, duration_s=0.5)

    files = {"file": ("test.wav", wav_bytes, "audio/wav")}
    data = {"language": "invalid_lang"}
    res = client.post("/audio/transcribe", files=files, data=data)

    assert res.status_code == 400
    assert "Unsupported language" in res.json()["detail"]


def test_audio_transcribe_invalid_data():
    client = TestClient(app)
    files = {"file": ("corrupt.wav", b"not-a-wav-file", "audio/wav")}
    res = client.post("/audio/transcribe", files=files)
    assert res.status_code == 400
