import { EvaluationSummary } from '../types';

export async function fetchLatestEvaluation(): Promise<EvaluationSummary | null> {
  const res = await fetch('/evaluation', {
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data;
}

export async function runEvaluation(limit?: number): Promise<EvaluationSummary> {
  const url = limit ? `/evaluation/run?limit=${limit}` : '/evaluation/run';
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Evaluation run failed' }));
    throw new Error(err.detail || 'Evaluation run failed');
  }
  return res.json();
}

