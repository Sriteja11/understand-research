import { EvidenceItem, Citation } from '../types';

export interface ChatStreamCallbacks {
  onToken: (token: string) => void;
  onEvidence: (evidence: EvidenceItem[]) => void;
  onCitation: (citations: Citation[]) => void;
  onComplete: (data: {
    answer: string;
    evidence: EvidenceItem[];
    citations: Citation[];
    grounded: boolean;
    latency_ms: number;
    session_id: string;
  }) => void;
  onError: (error: string) => void;
}

export async function streamChat(
  message: string,
  sessionId?: string,
  topK: number = 10,
  callbacks?: Partial<ChatStreamCallbacks>
): Promise<void> {
  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        top_k: topK,
      }),
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({ detail: 'Network error' }));
      throw new Error(errJson.detail || `Request failed with status ${res.status}`);
    }

    if (!res.body) {
      throw new Error('Response body is empty.');
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const block of lines) {
        if (!block.trim()) continue;

        let eventType = 'message';
        let eventData = '';

        const eventLines = block.split('\n');
        for (const line of eventLines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            eventData = line.slice(6).trim();
          }
        }

        if (!eventData) continue;

        try {
          const parsed = JSON.parse(eventData);

          if (eventType === 'token' && callbacks?.onToken) {
            callbacks.onToken(parsed.text || '');
          } else if (eventType === 'evidence' && callbacks?.onEvidence) {
            callbacks.onEvidence(parsed.evidence || []);
          } else if (eventType === 'citation' && callbacks?.onCitation) {
            callbacks.onCitation(parsed.citations || []);
          } else if (eventType === 'complete' && callbacks?.onComplete) {
            callbacks.onComplete(parsed);
          } else if (eventType === 'error' && callbacks?.onError) {
            callbacks.onError(parsed.error || 'Chat processing error');
          }
        } catch {
          // ignore non-json line
        }
      }
    }
  } catch (err: any) {
    if (callbacks?.onError) {
      callbacks.onError(err.message || 'Stream connection error');
    }
  }
}

