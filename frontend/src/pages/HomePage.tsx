import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Sparkles,
  GitBranch,
  Layers,
  FileCode,
  Trash2,
  ArrowRight,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { getRepos, ingestRepo, deleteRepo, type RepoInfo } from '../api';
import { ProgressBar } from '../components/ProgressBar';

const EXAMPLE_REPOS = [
  { name: 'Local Demo (Codebase Assistant)', url: 'https://github.com/example/codebase-assistant', preindexed: true, id: 'codebase-assistant' },
  { name: 'Pallets / Flask', url: 'https://github.com/pallets/flask', preindexed: false },
  { name: 'Express.js', url: 'https://github.com/expressjs/express', preindexed: false },
];

export const HomePage: React.FC = () => {
  const [url, setUrl] = useState('');
  const [repos, setRepos] = useState<RepoInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<RepoInfo | null>(null);
  const navigate = useNavigate();

  const loadRepos = async () => {
    try {
      const data = await getRepos();
      setRepos(data);
      const inProgress = data.find((r) => r.status === 'indexing');
      setActiveJob(inProgress || null);
    } catch {
      // API might still be starting
    }
  };

  useEffect(() => {
    loadRepos();
    const interval = setInterval(loadRepos, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleAnalyze = async (targetUrl: string) => {
    if (!targetUrl.trim()) return;
    setError(null);
    setLoading(true);

    try {
      const res = await ingestRepo(targetUrl.trim());
      setUrl('');
      await loadRepos();
      navigate(`/repo/${res.repo_id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to start indexing');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (repoId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Are you sure you want to delete ${repoId}?`)) return;
    try {
      await deleteRepo(repoId);
      await loadRepos();
    } catch (err: any) {
      alert(err.message || 'Failed to delete');
    }
  };

  return (
    <div className="min-h-screen bg-paper text-ink flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-line bg-surface/90 backdrop-blur sticky top-0 z-10 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-sunken border border-line flex items-center justify-center text-accent-strong">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-tight text-ink flex items-center gap-2">
              Codebase Assistant
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-sunken text-accent-strong border border-line">
                AST RAG
              </span>
            </h1>
            <p className="text-xs text-ink-muted">Grounded repository Q&A with exact file:line citations</p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-4 text-xs text-ink-muted">
          <span className="flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-accent-strong" />
            Hybrid Search (BM25 + Dense)
          </span>
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-accent-strong" />
            Cross-Encoder Rerank
          </span>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-12 space-y-10">
        <div className="text-center space-y-3 pt-4">
          <h2 className="text-3xl sm:text-4xl font-normal tracking-tight text-ink">
            Ask anything about a <span className="text-accent-strong italic font-serif">codebase</span>.
          </h2>
          <p className="text-ink-muted text-sm max-w-xl mx-auto">
            Tree-sitter AST parsing extracts semantic functions, methods, and classes.
            Answers cite exact file and line numbers with verified containment.
          </p>
        </div>

        {/* URL Input Box */}
        <div className="space-y-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAnalyze(url);
            }}
            className="flex flex-col sm:flex-row gap-2"
          >
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-ink-faint absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://github.com/owner/repository"
                className="input pl-10 py-2.5 font-mono text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !url.trim()}
              className="btn btn-primary px-6 py-2.5 text-sm"
            >
              <Sparkles className="w-4 h-4" />
              <span>{loading ? 'Starting…' : 'Analyze Repo'}</span>
            </button>
          </form>

          {error && (
            <div className="notice" data-tone="danger">
              <div className="text-xs text-danger font-medium">{error}</div>
            </div>
          )}

          {/* Quick Examples */}
          <div className="flex flex-wrap items-center gap-2 text-xs text-ink-muted pt-1">
            <span className="text-ink-faint font-medium">Try an example:</span>
            {EXAMPLE_REPOS.map((ex) => (
              <button
                key={ex.name}
                type="button"
                onClick={() => {
                  if (ex.preindexed && ex.id) {
                    navigate(`/repo/${ex.id}`);
                  } else {
                    setUrl(ex.url);
                  }
                }}
                className="btn btn-ghost py-1 px-2.5 text-xs font-mono"
              >
                {ex.name}
              </button>
            ))}
          </div>
        </div>

        {/* Live Indexing Progress (if any) */}
        {activeJob && (
          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Active Ingestion Job
            </div>
            <ProgressBar info={activeJob} />
          </div>
        )}

        {/* Indexed Repositories List */}
        <div className="space-y-3 pt-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-ink-muted">
              Indexed Repositories ({repos.length})
            </h3>
          </div>

          {repos.length === 0 ? (
            <div className="p-10 panel border-dashed text-center space-y-2 text-ink-muted">
              <FileCode className="w-8 h-8 mx-auto text-ink-faint" />
              <div className="text-sm font-medium">No repositories indexed yet.</div>
              <p className="text-xs text-ink-faint">Paste a GitHub URL above to analyze your first repository.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {repos.map((repo) => (
                <div
                  key={repo.repo_id}
                  onClick={() => navigate(`/repo/${repo.repo_id}`)}
                  className="panel p-4 hover:border-accent-strong transition-all cursor-pointer flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-sunken flex items-center justify-center text-ink-muted group-hover:text-accent-strong transition-colors shrink-0">
                      <GitBranch className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-ink group-hover:text-accent-strong transition-colors flex items-center gap-2">
                        {repo.repo_id}
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
                      </div>
                      <div className="text-xs text-ink-muted flex items-center gap-2 mt-0.5">
                        <span>{repo.chunk_count} chunks</span>
                        <span>•</span>
                        <span>{repo.file_count} files</span>
                        {repo.head_sha && (
                          <>
                            <span>•</span>
                            <span className="font-mono text-[11px] text-ink-faint">
                              {repo.head_sha.substring(0, 7)}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    <button
                      onClick={(e) => handleDelete(repo.repo_id, e)}
                      className="p-2 text-ink-faint hover:text-danger hover:bg-sunken rounded-lg transition-colors cursor-pointer"
                      title="Delete repository"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <div className="p-2 text-accent-strong flex items-center gap-1 text-xs font-medium">
                      <span>Open</span>
                      <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
