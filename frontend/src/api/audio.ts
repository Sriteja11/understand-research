import { AudioTranscriptionResponse, AudioStatusResponse } from '../types';

export interface TranscribeOptions {
  language?: string;
  keywords?: string[];
  wordTimestamps?: boolean;
}

export async function getAudioStatus(): Promise<AudioStatusResponse> {
  const res = await fetch('/audio/status');
  if (!res.ok) {
    throw new Error(`Failed to fetch audio engine status: ${res.statusText}`);
  }
  return res.json();
}

export async function transcribeAudio(
  fileOrBlob: Blob | File,
  options?: TranscribeOptions
): Promise<AudioTranscriptionResponse> {
  const formData = new FormData();
  
  const filename = fileOrBlob instanceof File ? fileOrBlob.name : 'audio_recording.wav';
  formData.append('file', fileOrBlob, filename);

  if (options?.language) {
    formData.append('language', options.language);
  }

  if (options?.keywords && options.keywords.length > 0) {
    formData.append('keywords', options.keywords.join(','));
  }

  if (options?.wordTimestamps) {
    formData.append('word_timestamps', 'true');
  }

  const res = await fetch('/audio/transcribe', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({ detail: 'Failed to transcribe audio' }));
    throw new Error(errorJson.detail || `Transcription failed with code ${res.status}`);
  }

  return res.json();
}
