import React, { useEffect } from 'react';
import { X, ExternalLink, GitCommit, FileCode, Layers } from 'lucide-react';
import type { ChunkDetail } from '../api';

interface SourcePanelProps {
  chunk: ChunkDetail | null;
  highlightRange?: { start: number; end: number };
  onClose: () => void;
}

export const SourcePanel: React.FC<SourcePanelProps> = ({ chunk, highlightRange, onClose }) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!chunk) return null;

  const lines = chunk.code.split('\n');
  const startLine = chunk.start_line;

  return (
    <aside
      className="w-full lg:w-[480px] h-full bg-surface border-l border-line flex flex-col z-20 shadow-2xl"
      aria-label="Source code viewer"
    >
      {/* Header */}
      <div className="p-4 border-b border-line flex items-center justify-between bg-surface">
        <div className="flex items-center gap-2 overflow-hidden">
          <FileCode className="w-5 h-5 text-accent-strong shrink-0" />
          <div className="truncate">
            <h3 className="text-sm font-semibold text-ink truncate">{chunk.file_path}</h3>
            <span className="text-xs text-ink-muted flex items-center gap-1.5">
              <span className="px-1.5 py-0.5 rounded bg-sunken text-accent-strong font-mono text-[10px] uppercase">
                {chunk.language}
              </span>
              <span>{chunk.kind}</span>
              {chunk.parent && <span>• {chunk.parent}</span>}
              <span>• lines {chunk.start_line}–{chunk.end_line}</span>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {chunk.github_url && (
            <a
              href={chunk.github_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 text-ink-muted hover:text-accent-strong hover:bg-sunken rounded transition-colors"
              title="Open on GitHub"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
          <button
            onClick={onClose}
            className="p-1.5 text-ink-muted hover:text-ink hover:bg-sunken rounded transition-colors flex items-center gap-1 cursor-pointer"
            title="Close"
          >
            <span className="kbd text-[10px] hidden sm:inline">Esc</span>
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Code Viewer with .code-block, .code-line, .code-line--hit */}
      <div className="flex-1 overflow-auto p-4 bg-paper">
        <div className="code-block">
          {lines.map((line, idx) => {
            const lineNum = startLine + idx;
            const isHighlighted =
              highlightRange &&
              lineNum >= highlightRange.start &&
              lineNum <= highlightRange.end;

            return (
              <div
                key={idx}
                className={`code-line ${isHighlighted ? 'code-line--hit' : ''}`}
              >
                <div className="code-line__no font-mono">{lineNum}</div>
                <div className="code-line__text font-mono text-ink">{line || ' '}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Commit History using .commit, .commit__hash */}
      {chunk.commits && chunk.commits.length > 0 && (
        <div className="border-t border-line bg-surface p-3.5 max-h-48 overflow-y-auto">
          <div className="flex items-center gap-1.5 text-xs font-medium text-ink-muted mb-2">
            <GitCommit className="w-3.5 h-3.5 text-accent-strong" />
            <span>Recent Commits on this File</span>
          </div>
          <div className="space-y-1">
            {chunk.commits.map((c, i) => (
              <div key={i} className="commit">
                <span className="commit__hash">{c.hash.substring(0, 7)}</span>
                <span className="truncate text-ink">{c.message}</span>
                <time className="text-[11px] font-mono">{c.date}</time>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Retrieval Scores footer if present */}
      {(chunk.rrf_score !== undefined || chunk.rerank_score !== undefined) && (
        <div className="px-4 py-2 border-t border-line bg-sunken text-[11px] text-ink-muted flex items-center justify-between">
          <span className="flex items-center gap-1 font-sans">
            <Layers className="w-3.5 h-3.5 text-accent-strong" />
            Scores:
          </span>
          <div className="flex gap-3 font-mono">
            {chunk.rrf_score !== undefined && <span>RRF: {chunk.rrf_score.toFixed(4)}</span>}
            {chunk.rerank_score !== undefined && (
              <span className="text-accent-strong font-medium">Rerank: {chunk.rerank_score.toFixed(2)}</span>
            )}
          </div>
        </div>
      )}
    </aside>
  );
};
