import { Session, Message } from '../types';

export async function fetchSessions(): Promise<Session[]> {
  const res = await fetch('/sessions', {
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to fetch sessions');
  return res.json();
}

export async function createSession(title: string = 'New Research Session'): Promise<Session> {
  const res = await fetch('/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error('Failed to create session');
  return res.json();
}

export async function fetchSession(id: string): Promise<{ id: string; title: string; messages: Message[] }> {
  const res = await fetch(`/sessions/${id}`, {
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to load session');
  const data = await res.json();
  const formattedMessages: Message[] = (data.messages || []).map((m: any) => {
    let meta: any = {};
    if (m.metadata_json) {
      try {
        meta = JSON.parse(m.metadata_json);
      } catch {
        // ignore
      }
    }
    return {
      id: m.id,
      role: m.role,
      content: m.content,
      evidence: meta.evidence || [],
      citations: meta.citations || [],
      grounded: meta.grounded !== undefined ? meta.grounded : true,
      latency_ms: meta.latency_ms,
    };
  });
  return { id: data.id, title: data.title, messages: formattedMessages };
}

export async function deleteSession(id: string): Promise<void> {
  const res = await fetch(`/sessions/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete session');
}

