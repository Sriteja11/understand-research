export interface Citation {
  document: string;
  chunk_id: string;
  page: number;
}

export interface EvidenceItem {
  document: string;
  chunk_id: string;
  page: number;
  section: string;
  text: string;
  score: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  evidence?: EvidenceItem[];
  citations?: Citation[];
  grounded?: boolean;
  latency_ms?: number;
  isStreaming?: boolean;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  is_seed: boolean;
  error?: string | null;
  progress?: number;
  created_at: string;
  updated_at: string;
}

export interface EvaluationResult {
  id: string;
  run_id: string;
  question_id: string;
  question_text: string;
  question_type: string;
  retrieval_hit: boolean;
  citation_correct: boolean;
  grounded: boolean;
  refusal_correct: boolean;
  latency_ms: number;
  answer_preview: string;
  created_at: string;
}

export interface EvaluationSummary {
  run_id: string;
  total_questions: number;
  retrieval_hit_rate: number;
  citation_accuracy: number;
  groundedness_rate: number;
  refusal_accuracy: number;
  avg_latency_ms: number;
  results: EvaluationResult[];
}

export interface AudioWordTimestamp {
  word: string;
  start: number;
  end: number;
  probability: number;
}

export interface AudioTranscriptionResponse {
  text: string;
  language: string;
  ttft_ms: number;
  decode_tps: number;
  duration_s: number;
  words?: AudioWordTimestamp[] | null;
  silence: boolean;
}

export interface AudioStatusResponse {
  available: boolean;
  model_name: string;
  engine: string;
  model_size_mb: number;
  supported_languages: string[];
  default_keywords_count: number;
}

