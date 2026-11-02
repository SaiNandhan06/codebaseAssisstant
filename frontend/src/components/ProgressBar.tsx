import React from 'react';
import { GitBranch, Code, Cpu, Database, CheckCircle, AlertCircle } from 'lucide-react';
import type { RepoInfo } from '../api';

interface ProgressBarProps {
  info: RepoInfo;
}

const STAGES = [
  { id: 'cloning', label: 'Clone', icon: GitBranch },
  { id: 'parsing', label: 'AST Parse', icon: Code },
  { id: 'embedding', label: 'Embedding', icon: Cpu },
  { id: 'storing', label: 'Vector Store', icon: Database },
];

export const ProgressBar: React.FC<ProgressBarProps> = ({ info }) => {
  const currentStage = info.stage || 'starting';
  const isDone = info.status === 'ready';
  const isError = info.status === 'error';

  const getStageIndex = (stageName: string) => {
    switch (stageName) {
      case 'cloning': return 0;
      case 'parsing': return 1;
      case 'embedding': return 2;
      case 'storing': return 3;
      case 'done': return 4;
      default: return 0;
    }
  };

  const currentIdx = getStageIndex(currentStage);

  return (
    <div className="panel p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-ink">
            {isDone ? 'Indexing Complete' : isError ? 'Indexing Failed' : 'Indexing Repository'}
          </h4>
          <p className="text-xs text-ink-muted mt-0.5">
            {info.url || info.repo_id}
          </p>
        </div>
        <div className="text-right">
          <span className="text-sm font-mono font-bold text-accent-strong">
            {Math.round(info.percent)}%
          </span>
          <div className="text-[11px] text-ink-muted">
            {info.chunk_count > 0 && `${info.chunk_count} chunks indexed`}
          </div>
        </div>
      </div>

      {/* Progress Track using .progress */}
      <div className="progress">
        <span
          style={{ width: `${Math.max(5, info.percent)}%` }}
        />
      </div>

      {/* Stage indicators */}
      <div className="grid grid-cols-4 gap-2 pt-2">
        {STAGES.map((s, idx) => {
          const Icon = s.icon;
          const isCompleted = isDone || currentIdx > idx;
          const isActive = !isDone && currentIdx === idx;

          return (
            <div
              key={s.id}
              className={`p-2.5 rounded-lg border text-center transition-all ${
                isCompleted
                  ? 'bg-sunken border-ok text-ok'
                  : isActive
                  ? 'bg-surface border-accent-strong text-accent-strong ring-1 ring-accent-soft'
                  : 'bg-surface border-line text-ink-muted'
              }`}
            >
              <div className="flex justify-center mb-1">
                {isCompleted ? (
                  <CheckCircle className="w-4 h-4 text-ok" />
                ) : (
                  <Icon className={`w-4 h-4 ${isActive ? 'animate-pulse text-accent-strong' : ''}`} />
                )}
              </div>
              <div className="text-[11px] font-medium truncate">{s.label}</div>
            </div>
          );
        })}
      </div>

      {/* Error display */}
      {isError && info.error && (
        <div className="notice" data-tone="danger">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-danger shrink-0 mt-0.5" />
            <div>{info.error}</div>
          </div>
        </div>
      )}
    </div>
  );
};
