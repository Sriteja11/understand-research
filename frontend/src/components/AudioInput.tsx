import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, Square, X, Loader2, Upload, Sparkles, Volume2 } from 'lucide-react';
import { AudioRecorder } from '../utils/audioRecorder';
import { transcribeAudio, getAudioStatus } from '../api/audio';
import { AudioTranscriptionResponse, AudioStatusResponse } from '../types';

interface AudioInputProps {
  onTranscription: (text: string, metadata: AudioTranscriptionResponse) => void;
  disabled?: boolean;
}

export const AudioInput: React.FC<AudioInputProps> = ({ onTranscription, disabled = false }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [status, setStatus] = useState<AudioStatusResponse | null>(null);
  const [showLanguageSelect, setShowLanguageSelect] = useState(false);

  const recorderRef = useRef<AudioRecorder | null>(null);
  const timerRef = useRef<number | null>(null);
  const levelIntervalRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Fetch Whistle engine status on mount
  useEffect(() => {
    getAudioStatus()
      .then((st) => setStatus(st))
      .catch((err) => console.warn('Could not fetch audio status:', err));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (levelIntervalRef.current) clearInterval(levelIntervalRef.current);
      if (recorderRef.current) recorderRef.current.cancel();
    };
  }, []);

  const startRecording = async () => {
    if (disabled || isProcessing) return;
    setErrorMsg(null);

    try {
      const recorder = new AudioRecorder();
      recorderRef.current = recorder;
      await recorder.start();

      setIsRecording(true);
      setRecordingSeconds(0);

      // 1-second interval timer (max 30s per Whistle model)
      timerRef.current = window.setInterval(() => {
        setRecordingSeconds((prev) => {
          if (prev >= 29) {
            // Auto-stop at 30 seconds
            stopAndTranscribe();
            return 30;
          }
          return prev + 1;
        });
      }, 1000);

      // Audio level polling for waveform pulse
      levelIntervalRef.current = window.setInterval(() => {
        if (recorderRef.current) {
          setAudioLevel(recorderRef.current.getAudioLevel());
        }
      }, 100);
    } catch (err: any) {
      console.error('Failed to start recording:', err);
      setErrorMsg(err.message || 'Microphone access denied or unavailable.');
      setIsRecording(false);
    }
  };

  const stopAndTranscribe = async () => {
    if (!recorderRef.current || !isRecording) return;

    if (timerRef.current) clearInterval(timerRef.current);
    if (levelIntervalRef.current) clearInterval(levelIntervalRef.current);

    setIsRecording(false);
    setIsProcessing(true);
    setErrorMsg(null);

    try {
      const wavBlob = await recorderRef.current.stop();
      recorderRef.current = null;

      const resp = await transcribeAudio(wavBlob, {
        language: selectedLanguage || undefined,
        wordTimestamps: true,
      });

      if (resp.silence || !resp.text.trim()) {
        setErrorMsg('Silence detected. No speech was recognized.');
      } else {
        onTranscription(resp.text, resp);
      }
    } catch (err: any) {
      console.error('Transcription error:', err);
      setErrorMsg(err.message || 'Transcription failed.');
    } finally {
      setIsProcessing(false);
      setRecordingSeconds(0);
      setAudioLevel(0);
    }
  };

  const cancelRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (levelIntervalRef.current) clearInterval(levelIntervalRef.current);

    if (recorderRef.current) {
      recorderRef.current.cancel();
      recorderRef.current = null;
    }

    setIsRecording(false);
    setRecordingSeconds(0);
    setAudioLevel(0);
    setErrorMsg(null);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsProcessing(true);
    setErrorMsg(null);

    try {
      const resp = await transcribeAudio(file, {
        language: selectedLanguage || undefined,
        wordTimestamps: true,
      });

      if (resp.silence || !resp.text.trim()) {
        setErrorMsg('Silence detected or empty audio clip.');
      } else {
        onTranscription(resp.text, resp);
      }
    } catch (err: any) {
      console.error('File transcription error:', err);
      setErrorMsg(err.message || 'Failed to transcribe uploaded audio file.');
    } finally {
      setIsProcessing(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="relative flex items-center">
      {/* Hidden file input for WAV uploads */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".wav,audio/wav"
        onChange={handleFileUpload}
        className="hidden"
      />

      {/* Active Recording Overlay Bar */}
      {isRecording ? (
        <div className="flex items-center space-x-2 bg-red-50 border border-red-200 rounded-xl px-3 py-1.5 shadow-sm text-xs text-red-700 animate-fadeIn">
          <div className="relative flex items-center justify-center">
            <span
              className="w-2.5 h-2.5 rounded-full bg-red-600 animate-ping absolute"
              style={{ opacity: 0.4 + audioLevel * 0.6 }}
            />
            <span className="w-2 h-2 rounded-full bg-red-600" />
          </div>

          <span className="font-mono font-medium">
            00:{recordingSeconds < 10 ? `0${recordingSeconds}` : recordingSeconds} / 00:30
          </span>

          {/* Simple dynamic audio meter bars */}
          <div className="flex items-center space-x-0.5 h-3">
            {[0.2, 0.5, 0.8, 0.4, 0.9, 0.6].map((scale, i) => (
              <div
                key={i}
                className="w-0.5 bg-red-500 rounded-full transition-all duration-75"
                style={{
                  height: `${Math.max(3, Math.min(12, 3 + audioLevel * 14 * scale))}px`,
                }}
              />
            ))}
          </div>

          <button
            type="button"
            onClick={stopAndTranscribe}
            className="flex items-center space-x-1 px-2 py-0.5 bg-red-600 hover:bg-red-700 text-white rounded-md font-medium text-[11px] transition-colors"
            title="Stop and transcribe speech"
          >
            <Square className="w-3 h-3 fill-current" />
            <span>Done</span>
          </button>

          <button
            type="button"
            onClick={cancelRecording}
            className="p-1 hover:bg-red-200/60 rounded-md text-red-600 transition-colors"
            title="Cancel recording"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : isProcessing ? (
        /* Processing / Transcribing Spinner */
        <div className="flex items-center space-x-1.5 px-3 py-1 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs shadow-xs">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-600" />
          <span className="font-medium">Whistle transcribing...</span>
        </div>
      ) : (
        /* Idle State Controls */
        <div className="flex items-center space-x-1">
          {/* Microphone Record Button */}
          <button
            type="button"
            onClick={startRecording}
            disabled={disabled}
            className="p-2 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            title="Voice Input (Whistle STT · 16.9 MB)"
          >
            <Mic className="w-4 h-4" />
          </button>

          {/* Audio File Upload Button */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            title="Upload audio clip (.wav)"
          >
            <Upload className="w-4 h-4" />
          </button>

          {/* Language / Whistle Options Selector Toggle */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowLanguageSelect(!showLanguageSelect)}
              className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-slate-200 text-slate-500 hover:text-slate-700 hover:bg-slate-50 transition-colors"
              title="Select speech language"
            >
              {selectedLanguage ? selectedLanguage.toUpperCase() : 'AUTO'}
            </button>

            {showLanguageSelect && (
              <div className="absolute bottom-full mb-1 right-0 w-36 bg-white border border-slate-200 rounded-lg shadow-lg p-1.5 text-xs z-50 animate-fadeIn">
                <div className="px-1.5 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                  Language
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedLanguage('');
                    setShowLanguageSelect(false);
                  }}
                  className={`w-full text-left px-2 py-1 rounded text-xs ${
                    !selectedLanguage ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  Auto-detect
                </button>
                {status?.supported_languages?.map((lang) => (
                  <button
                    key={lang}
                    type="button"
                    onClick={() => {
                      setSelectedLanguage(lang);
                      setShowLanguageSelect(false);
                    }}
                    className={`w-full text-left px-2 py-1 rounded text-xs capitalize ${
                      selectedLanguage === lang
                        ? 'bg-indigo-50 text-indigo-700 font-semibold'
                        : 'hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    {lang === 'en'
                      ? 'English'
                      : lang === 'de'
                      ? 'German'
                      : lang === 'fr'
                      ? 'French'
                      : lang === 'es'
                      ? 'Spanish'
                      : lang === 'it'
                      ? 'Italian'
                      : lang === 'nl'
                      ? 'Dutch'
                      : lang === 'pl'
                      ? 'Polish'
                      : lang}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Floating Error Toast */}
      {errorMsg && (
        <div className="absolute bottom-full mb-2 right-0 bg-red-600 text-white text-xs px-2.5 py-1 rounded-md shadow-md flex items-center space-x-1.5 z-50">
          <span>{errorMsg}</span>
          <button
            type="button"
            onClick={() => setErrorMsg(null)}
            className="hover:opacity-75"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
};
