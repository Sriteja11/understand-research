import { DocumentItem } from '../types';

export async function fetchDocuments(): Promise<DocumentItem[]> {
  const res = await fetch('/documents', {
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function uploadDocument(file: File): Promise<{ document_id: string; job_id: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch('/documents/upload', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(err.detail || 'Upload failed');
  }
  return res.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`/documents/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete document');
}

export function subscribeToDocumentEvents(
  documentId: string,
  onStatus: (status: string, progress: number) => void,
  onComplete: () => void,
  onError: (err: string) => void
): () => void {
  const es = new EventSource(`/documents/${documentId}/events`);

  es.addEventListener('status', (e) => {
    try {
      const data = JSON.parse(e.data);
      onStatus(data.status, data.progress);
    } catch {
      // ignore
    }
  });

  es.addEventListener('complete', () => {
    onComplete();
    es.close();
  });

  es.addEventListener('error', (e: any) => {
    try {
      const data = JSON.parse(e.data || '{}');
      onError(data.error || 'Indexing failed');
    } catch {
      onError('Indexing event stream closed');
    }
    es.close();
  });

  return () => es.close();
}

