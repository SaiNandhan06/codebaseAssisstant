/**
 * Codebase Assistant API Client
 */

export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export interface RepoInfo {
  repo_id: string;
  url?: string;
  status: 'indexing' | 'ready' | 'error';
  stage?: 'starting' | 'cloning' | 'parsing' | 'embedding' | 'storing' | 'done' | 'error';
  percent: number;
  chunk_count: number;
  file_count: number;
  head_sha?: string;
  error?: string;
  languages?: Record<string, number>;
}

export interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  raw: string;
}

export interface SourceChunk {
  id: string;
  file_path: string;
  language: string;
  kind: string;
  name: string;
  parent?: string;
  start_line: number;
  end_line: number;
  code: string;
  rrf_score?: number;
  rerank_score?: number;
  bm25_rank?: number;
  dense_rank?: number;
  commits?: Array<{ hash: string; author: string; date: string; message: string }>;
}

export interface AskResponse {
  answer: string;
  sources: SourceChunk[];
  low_confidence: boolean;
  citations: Citation[];
  invalid_citations: Citation[];
  search_query: string;
}

export interface ChunkDetail extends SourceChunk {
  github_url?: string;
}

export async function getHealth(): Promise<{ status: string; timestamp: number }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function getRepos(): Promise<RepoInfo[]> {
  const res = await fetch(`${API_BASE}/repos`);
  if (!res.ok) throw new Error('Failed to fetch repositories');
  const data = await res.json();
  return data.repos || [];
}

export async function getRepoInfo(repoId: string): Promise<RepoInfo> {
  const res = await fetch(`${API_BASE}/repos/${repoId}`);
  if (!res.ok) throw new Error(`Repository not found: ${repoId}`);
  return res.json();
}

export async function ingestRepo(url: string): Promise<{ repo_id: string; job_id: string }> {
  const res = await fetch(`${API_BASE}/repos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Ingestion failed' }));
    throw new Error(err.detail || 'Failed to start ingestion');
  }
  return res.json();
}

export async function deleteRepo(repoId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/repos/${repoId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete repository');
}

export async function getChunkDetail(repoId: string, chunkId: string): Promise<ChunkDetail> {
  const res = await fetch(`${API_BASE}/repos/${repoId}/chunks/${encodeURIComponent(chunkId)}`);
  if (!res.ok) throw new Error(`Chunk not found: ${chunkId}`);
  return res.json();
}

export function streamAsk(
  repoId: string,
  question: string,
  history: Array<{ role: string; content: string }>,
  onToken: (token: string) => void,
  onFinal: (final: AskResponse) => void,
  onError: (err: string) => void
): () => void {
  const controller = new AbortController();

  fetch(`${API_BASE}/repos/${repoId}/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Ask request failed' }));
        onError(errorData.detail || 'Ask failed');
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        onError('Streaming not supported by browser');
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;
          const payload = trimmed.replace('data: ', '').trim();
          if (payload === '[DONE]') break;

          try {
            const parsed = JSON.parse(payload);
            if (parsed.type === 'token') {
              onToken(parsed.content);
            } else if (parsed.type === 'final') {
              onFinal(parsed.content);
            } else if (parsed.type === 'error') {
              onError(parsed.content);
            }
          } catch {
            // ignore partial JSON parse errors
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err.message || 'Stream error occurred');
      }
    });

  return () => controller.abort();
}

