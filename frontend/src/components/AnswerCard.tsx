import React, { useState } from 'react';
import { Copy, Check, AlertTriangle, FileCode, ChevronDown, ChevronUp } from 'lucide-react';
import type { SourceChunk } from '../api';

interface AnswerCardProps {
  answer: string;
  sources?: SourceChunk[];
  lowConfidence?: boolean;
  onCitationClick: (filePath: string, startLine: number, endLine: number) => void;
}

export const AnswerCard: React.FC<AnswerCardProps> = ({
  answer,
  sources = [],
  lowConfidence = false,
  onCitationClick,
}) => {
  const [copied, setCopied] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Replace citations [path:start-end] with interactive .cite buttons
  const renderFormattedText = (text: string) => {
    const citationRegex = /\[([^\]]+?):(\d+)-(\d+)\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(text)) !== null) {
      const matchStart = match.index;
      const matchEnd = citationRegex.lastIndex;

      // Text before citation
      if (matchStart > lastIndex) {
        parts.push(text.substring(lastIndex, matchStart));
      }

      const filePath = match[1];
      const startLine = parseInt(match[2], 10);
      const endLine = parseInt(match[3], 10);
      const filename = filePath.split('/').pop() || filePath;

      parts.push(
        <button
          key={`${filePath}-${startLine}-${endLine}-${matchStart}`}
          onClick={() => onCitationClick(filePath, startLine, endLine)}
          className="cite"
          title={`Click to view ${filePath}:${startLine}-${endLine}`}
        >
          <FileCode className="w-3 h-3 mr-1 inline opacity-70" />
          <span>{filename}:{startLine}–{endLine}</span>
        </button>
      );

      lastIndex = matchEnd;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts;
  };

  return (
    <div className="panel overflow-hidden transition-all">
      {/* Low Confidence Notice */}
      {lowConfidence && (
        <div className="notice" data-tone="warn">
          <div className="flex items-center gap-2 font-medium">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Low confidence notice: No strong evidence was found in the indexed code chunks to definitively answer this question.</span>
          </div>
        </div>
      )}

      {/* Answer Body with serif typography and generous leading */}
      <div className="p-6 answer text-ink whitespace-pre-wrap">
        {renderFormattedText(answer)}
      </div>

      {/* Actions and Sources Bar */}
      <div className="px-5 py-2.5 bg-sunken border-t border-line flex items-center justify-between text-xs text-ink-muted">
        <div className="flex items-center gap-3">
          {sources.length > 0 && (
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1.5 text-ink-muted hover:text-accent-strong transition-colors cursor-pointer"
            >
              <span>{sources.length} sources retrieved</span>
              {showSources ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>

        <button
          onClick={handleCopy}
          className="btn btn-ghost py-1 px-2.5 text-xs font-mono"
          title="Copy answer text"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-ok" />
              <span className="text-ok font-medium">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Collapsible Source List */}
      {showSources && sources.length > 0 && (
        <div className="p-4 bg-sunken border-t border-line space-y-2">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
            Retrieved Context Chunks (Hybrid RRF + Cross-Encoder)
          </div>
          <div className="grid grid-cols-1 gap-2">
            {sources.map((s, idx) => (
              <div
                key={idx}
                onClick={() => onCitationClick(s.file_path, s.start_line, s.end_line)}
                className="p-2.5 rounded-lg bg-surface border border-line hover:border-accent-strong cursor-pointer transition-colors flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="px-1.5 py-0.5 rounded bg-sunken text-[10px] font-mono text-accent-strong uppercase">
                    {s.kind}
                  </span>
                  <span className="font-mono text-ink truncate">{s.file_path}:{s.start_line}–{s.end_line}</span>
                  <span className="text-ink-muted truncate text-[11px]">— {s.name}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0 font-mono text-[11px] text-ink-faint">
                  {s.rerank_score !== undefined && (
                    <span className="text-accent-strong">Rerank: {s.rerank_score.toFixed(2)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
