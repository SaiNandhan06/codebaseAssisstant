import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Send,
  Loader2,
  HelpCircle,
  BookOpen,
} from 'lucide-react';
import {
  getRepoInfo,
  getChunkDetail,
  streamAsk,
  type RepoInfo,
  type SourceChunk,
  type ChunkDetail,
  type AskResponse,
} from '../api';
import { AnswerCard } from '../components/AnswerCard';
import { SourcePanel } from '../components/SourcePanel';
import { ProgressBar } from '../components/ProgressBar';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceChunk[];
  lowConfidence?: boolean;
}

const DEFAULT_SUGGESTIONS = [
  'How does the hybrid search combine BM25 and dense vectors?',
  'Where and how are tree-sitter AST chunks parsed?',
  'How are citations extracted and verified against code chunks?',
  'What noise filters are applied during ingestion?',
];

export const WorkspacePage: React.FC = () => {
  const { id: repoId } = useParams<{ id: string }>();
  const [repo, setRepo] = useState<RepoInfo | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingToken, setStreamingToken] = useState('');

  // Source panel state
  const [selectedChunk, setSelectedChunk] = useState<ChunkDetail | null>(null);
  const [highlightRange, setHighlightRange] = useState<{ start: number; end: number } | undefined>();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingToken]);

  // Load repo info & poll if indexing
  useEffect(() => {
    if (!repoId) return;

    let isMounted = true;
    const fetchInfo = async () => {
      try {
        const info = await getRepoInfo(repoId);
        if (isMounted) {
          setRepo(info);
          setFetchError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          setFetchError(err.message || 'Failed to connect to backend');
        }
      }
    };

    fetchInfo();
    const interval = setInterval(() => {
      if (repo?.status === 'indexing' || !repo) {
        fetchInfo();
      }
    }, 2000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [repoId, repo?.status]);

  const handleCitationClick = async (filePath: string, startLine: number, endLine: number) => {
    if (!repoId) return;
    try {
      // Find chunk in current messages' sources if possible
      let matched: SourceChunk | undefined;
      for (const m of messages) {
        if (m.sources) {
          matched = m.sources.find(
            (s) =>
              s.file_path === filePath &&
              startLine >= s.start_line &&
              endLine <= s.end_line
          );
          if (matched) break;
        }
      }

      if (matched) {
        const detail = await getChunkDetail(repoId, matched.id).catch(() => matched as ChunkDetail);
        setSelectedChunk(detail);
      } else {
        // Fallback: synthesized minimal chunk
        setSelectedChunk({
          id: `${filePath}::${startLine}`,
          file_path: filePath,
          language: filePath.split('.').pop() || 'text',
          kind: 'code',
          name: filePath.split('/').pop() || filePath,
          start_line: startLine,
          end_line: endLine,
          code: `// File: ${filePath} (lines ${startLine}-${endLine})\n// Viewing source citation...`,
        });
      }

      setHighlightRange({ start: startLine, end: endLine });
    } catch (err) {
      console.error('Failed to load chunk:', err);
    }
  };

  const handleSend = (textToSend?: string) => {
    const question = (textToSend || input).trim();
    if (!question || !repoId || isStreaming) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
    };

    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput('');
    setIsStreaming(true);
    setStreamingToken('');

    const history = newMessages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    let accumulated = '';

    streamAsk(
      repoId,
      question,
      history.slice(0, -1),
      (token) => {
        accumulated += token;
        setStreamingToken(accumulated);
      },
      (finalData: AskResponse) => {
        setIsStreaming(false);
        setStreamingToken('');
        setMessages((prev) => [
          ...prev,
          {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: finalData.answer,
            sources: finalData.sources,
            lowConfidence: finalData.low_confidence,
          },
        ]);
      },
      (err) => {
        setIsStreaming(false);
        setStreamingToken('');
        setMessages((prev) => [
          ...prev,
          {
            id: `assistant-err-${Date.now()}`,
            role: 'assistant',
            content: err.startsWith('Error:') ? err : `Error: ${err}`,
            lowConfidence: false,
          },
        ]);
      }
    );
  };

  return (
    <div className="h-screen flex flex-col bg-paper text-ink overflow-hidden font-sans">
      {/* Workspace Header */}
      <header className="h-14 border-b border-line bg-surface px-5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="p-1.5 rounded-lg text-ink-muted hover:text-ink hover:bg-sunken transition-colors"
            title="Back to Repositories"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-ink">{repoId}</span>
            {repo && (
              <span
                className="badge font-mono"
                data-status={
                  repo.status === 'ready'
                    ? 'ready'
                    : repo.status === 'error'
                    ? 'failed'
                    : 'indexing'
                }
              >
                {repo.status}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-ink-muted">
          {repo?.chunk_count ? (
            <span className="font-mono">{repo.chunk_count} chunks indexed</span>
          ) : null}
        </div>
      </header>

      {/* Main 3-column Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Repo Metadata & Suggested Questions */}
        <aside className="w-64 border-r border-line bg-surface hidden md:flex flex-col p-4 space-y-5 shrink-0 overflow-y-auto">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted mb-2">
              Repository Info
            </div>
            {repo ? (
              <div className="space-y-2 text-xs text-ink">
                <div className="panel-sunken p-3 space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-ink-muted">Files:</span>
                    <span className="font-mono">{repo.file_count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-muted">Chunks:</span>
                    <span className="font-mono">{repo.chunk_count}</span>
                  </div>
                  {repo.head_sha && (
                    <div className="flex justify-between">
                      <span className="text-ink-muted">Commit:</span>
                      <span className="font-mono text-accent-strong">{repo.head_sha.substring(0, 7)}</span>
                    </div>
                  )}
                </div>

                {repo.languages && Object.keys(repo.languages).length > 0 && (
                  <div className="space-y-1 pt-1">
                    <span className="text-[11px] text-ink-muted font-medium">Languages</span>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(repo.languages).map(([lang, count]) => (
                        <span
                          key={lang}
                          className="px-2 py-0.5 rounded bg-sunken text-[10px] font-mono text-ink-muted border border-line"
                        >
                          {lang}: {count}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-ink-muted">Loading repository info…</div>
            )}
          </div>

          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted flex items-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5 text-accent-strong" />
              <span>Suggested Questions</span>
            </div>
            <div className="space-y-1.5">
              {DEFAULT_SUGGESTIONS.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(q)}
                  disabled={isStreaming || repo?.status === 'indexing'}
                  className="w-full text-left p-2.5 rounded-lg bg-surface hover:bg-sunken border border-line text-xs text-ink hover:text-accent-strong transition-colors cursor-pointer leading-snug"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </aside>

        {/* Center: Chat Thread */}
        <section className="flex-1 flex flex-col h-full overflow-hidden bg-paper">
          {/* Indexing status banner if not ready */}
          {repo && repo.status === 'indexing' && (
            <div className="p-4 border-b border-line bg-surface">
              <ProgressBar info={repo} />
            </div>
          )}

          {/* Connection Error Banner */}
          {fetchError && (
            <div className="p-3 mx-4 sm:mx-6 mt-4 notice" data-tone="danger">
              <div className="flex items-center justify-between text-xs text-danger font-medium">
                <span>⚠️ {fetchError}. Ensure FastAPI backend is running on http://127.0.0.1:8000</span>
                <button
                  type="button"
                  onClick={() => window.location.reload()}
                  className="underline cursor-pointer ml-3 font-semibold hover:text-ink"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* Messages scroll area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-4 text-ink-muted py-12">
                <div className="w-12 h-12 rounded-2xl bg-sunken border border-line flex items-center justify-center text-accent-strong">
                  <BookOpen className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-ink">
                    Ask a question about {repoId}
                  </h3>
                  <p className="text-xs text-ink-muted mt-1">
                    Every answer is grounded in retrieved AST chunks with verified citations.
                  </p>
                </div>
                <div className="grid grid-cols-1 gap-2 w-full pt-2">
                  {DEFAULT_SUGGESTIONS.slice(0, 3).map((q, i) => (
                    <button
                      key={i}
                      onClick={() => handleSend(q)}
                      disabled={isStreaming || repo?.status === 'indexing'}
                      className="p-3 rounded-xl panel text-xs text-ink hover:border-accent-strong text-left transition-all cursor-pointer"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m) => (
                <div key={m.id} className="space-y-2 flex flex-col">
                  {m.role === 'user' ? (
                    <div className="msg-user text-ink text-sm font-sans shadow-sm">
                      {m.content}
                    </div>
                  ) : (
                    <AnswerCard
                      answer={m.content}
                      sources={m.sources}
                      lowConfidence={m.lowConfidence}
                      onCitationClick={handleCitationClick}
                    />
                  )}
                </div>
              ))
            )}

            {/* Live Streaming Token Output with .caret */}
            {isStreaming && (
              <div className="panel p-5 space-y-3">
                <div className="flex items-center gap-2 text-xs text-accent-strong font-medium">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Analyzing code chunks and generating answer…</span>
                </div>
                <div className="answer text-ink whitespace-pre-wrap leading-relaxed">
                  {streamingToken || '…'}
                  <span className="caret" aria-hidden="true"></span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <footer className="p-4 border-t border-line bg-surface shrink-0">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="max-w-4xl mx-auto flex gap-2"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  repo?.status === 'indexing'
                    ? 'Waiting for repository to finish indexing…'
                    : 'Ask a question about this repository…'
                }
                disabled={isStreaming || repo?.status === 'indexing'}
                className="input flex-1 py-2.5 px-4 font-sans text-sm disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isStreaming || !input.trim() || repo?.status === 'indexing'}
                className="btn btn-primary px-5 py-2.5"
              >
                {isStreaming ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>
          </footer>
        </section>

        {/* Right Sidebar: Source Code Viewer */}
        {selectedChunk && (
          <SourcePanel
            chunk={selectedChunk}
            highlightRange={highlightRange}
            onClose={() => setSelectedChunk(null)}
          />
        )}
      </div>
    </div>
  );
};
