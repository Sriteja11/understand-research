/**
 * Utility for recording browser audio and encoding directly to standard 16 kHz mono 16-bit PCM WAV.
 * Matches Cactus Compute Whistle's required input format without external transcoding dependencies.
 */

export class AudioRecorder {
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private pcmChunks: Float32Array[] = [];
  private isRecording: boolean = false;
  private analyser: AnalyserNode | null = null;
  private dataArray: Uint8Array | null = null;

  async start(): Promise<void> {
    if (this.isRecording) return;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Audio recording is not supported in this browser.');
    }

    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    this.audioContext = new AudioContextClass();

    this.source = this.audioContext.createMediaStreamSource(this.mediaStream);
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

    // ScriptProcessor with buffer size 4096 (1 input channel, 1 output channel)
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    this.pcmChunks = [];

    this.processor.onaudioprocess = (e) => {
      if (!this.isRecording) return;
      const inputBuffer = e.inputBuffer.getChannelData(0);
      // Copy slice of input channel
      this.pcmChunks.push(new Float32Array(inputBuffer));
    };

    this.source.connect(this.analyser);
    this.analyser.connect(this.processor);
    this.processor.connect(this.audioContext.destination);

    this.isRecording = true;
  }

  getAudioLevel(): number {
    if (!this.analyser || !this.dataArray || !this.isRecording) return 0;
    this.analyser.getByteFrequencyData(this.dataArray as any);
    let sum = 0;
    for (let i = 0; i < this.dataArray.length; i++) {
      sum += this.dataArray[i];
    }
    return Math.min(1, (sum / this.dataArray.length) / 128);
  }

  async stop(): Promise<Blob> {
    if (!this.isRecording) {
      throw new Error('Not recording.');
    }

    this.isRecording = false;

    // Disconnect audio nodes
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.analyser) {
      this.analyser.disconnect();
      this.analyser = null;
    }
    if (this.source) {
      this.source.disconnect();
      this.source = null;
    }

    const currentSampleRate = this.audioContext ? this.audioContext.sampleRate : 44100;

    if (this.audioContext && this.audioContext.state !== 'closed') {
      await this.audioContext.close();
      this.audioContext = null;
    }

    // Stop all media tracks
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    // Merge recorded PCM chunks into single Float32Array
    let totalLength = 0;
    for (const chunk of this.pcmChunks) {
      totalLength += chunk.length;
    }

    const mergedPcm = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of this.pcmChunks) {
      mergedPcm.set(chunk, offset);
      offset += chunk.length;
    }
    this.pcmChunks = [];

    // Resample merged buffer down to 16,000 Hz for Whistle
    const targetSampleRate = 16000;
    const resampledPcm = this.resampleAudio(mergedPcm, currentSampleRate, targetSampleRate);

    // Limit to max 30 seconds (30 * 16,000 samples)
    const maxSamples = targetSampleRate * 30;
    const finalPcm = resampledPcm.length > maxSamples ? resampledPcm.slice(0, maxSamples) : resampledPcm;

    // Encode to 16-bit PCM WAV Blob
    return this.encodeWav(finalPcm, targetSampleRate);
  }

  cancel(): void {
    this.isRecording = false;
    this.pcmChunks = [];

    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.analyser) {
      this.analyser.disconnect();
      this.analyser = null;
    }
    if (this.source) {
      this.source.disconnect();
      this.source = null;
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
  }

  get recording(): boolean {
    return this.isRecording;
  }

  private resampleAudio(
    audioData: Float32Array,
    origSampleRate: number,
    targetSampleRate: number
  ): Float32Array {
    if (origSampleRate === targetSampleRate || audioData.length === 0) {
      return audioData;
    }

    const ratio = targetSampleRate / origSampleRate;
    const newLength = Math.round(audioData.length * ratio);
    const result = new Float32Array(newLength);

    for (let i = 0; i < newLength; i++) {
      const origIndex = i / ratio;
      const lower = Math.floor(origIndex);
      const upper = Math.min(lower + 1, audioData.length - 1);
      const weight = origIndex - lower;
      result[i] = audioData[lower] * (1 - weight) + audioData[upper] * weight;
    }

    return result;
  }

  private encodeWav(samples: Float32Array, sampleRate: number): Blob {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    // RIFF chunk descriptor
    this.writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    this.writeString(view, 8, 'WAVE');

    // FMT sub-chunk
    this.writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
    view.setUint16(20, 1, true); // AudioFormat (1 for PCM)
    view.setUint16(22, 1, true); // NumChannels (1 mono)
    view.setUint32(24, sampleRate, true); // SampleRate (16000)
    view.setUint32(28, sampleRate * 2, true); // ByteRate (SampleRate * NumChannels * BitsPerSample/8)
    view.setUint16(32, 2, true); // BlockAlign (NumChannels * BitsPerSample/8)
    view.setUint16(34, 16, true); // BitsPerSample (16 bits)

    // Data sub-chunk
    this.writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    // Write PCM 16-bit integer samples
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }

    return new Blob([view], { type: 'audio/wav' });
  }

  private writeString(view: DataView, offset: number, string: string): void {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }
}
