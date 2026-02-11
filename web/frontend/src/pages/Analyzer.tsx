import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Loader2,
  FileCode2,
  ChevronDown,
  ChevronRight,
  Tag,
  Flag,
  Lightbulb,
  BarChart3,
  Package,
  Code,
  FileText,
  CheckCircle2,
  XCircle,
  Globe,
  BookOpen,
  Star,
  GitFork,
  ExternalLink,
  Layers,
} from 'lucide-react';
import { analyzeRepo, generateHierarchicalLibrary, searchGitHubRepos } from '../api/client';
import type { Candidate, AnalyzeResult, CodebaseSummary, GitHubRepoResult } from '../types';
import ScoreBar from '../components/ScoreBar';
import Badge from '../components/Badge';
import EmptyState from '../components/EmptyState';
import AIQueryPanel from '../components/AIQueryPanel';

const SIZE_CLASS_CONFIG: Record<string, { label: string; color: string; description: string }> = {
  widget: { label: 'Widget', color: 'bg-sky-100 text-sky-700 border-sky-200', description: 'Single function or tiny utility' },
  component: { label: 'Component', color: 'bg-emerald-100 text-emerald-700 border-emerald-200', description: 'Focused module or small set of modules' },
  service: { label: 'Service', color: 'bg-amber-100 text-amber-700 border-amber-200', description: 'Multiple modules with coordination' },
  app: { label: 'App', color: 'bg-purple-100 text-purple-700 border-purple-200', description: 'Full application or large system' },
};

function SizeClassBadge({ sizeClass }: { sizeClass: string }) {
  const config = SIZE_CLASS_CONFIG[sizeClass];
  if (!config) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold rounded-full border ${config.color}`}
      title={config.description}
    >
      <Layers size={10} />
      {config.label}
    </span>
  );
}

function CodebaseSummaryCard({ summary }: { summary: CodebaseSummary }) {
  const [expanded, setExpanded] = useState(false);
  const languages = Object.entries(summary.files_by_language).sort(
    ([, a], [, b]) => b - a
  );

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-6 py-5 cursor-pointer hover:bg-gray-50/50 transition-colors"
      >
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
            <BarChart3 size={20} className="text-indigo-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 mb-1">
              Codebase Summary
            </h3>
            {summary.description && (
              <p className="text-sm text-gray-800 mb-1">{summary.description}</p>
            )}
            {summary.purpose && (
              <p className="text-xs text-gray-500">{summary.purpose}</p>
            )}
            <div className="flex flex-wrap gap-4 mt-3 text-sm text-gray-700">
              <span className="flex items-center gap-1.5">
                <FileText size={14} className="text-gray-400" />
                {summary.total_files.toLocaleString()} files
              </span>
              <span className="flex items-center gap-1.5">
                <Code size={14} className="text-gray-400" />
                {summary.total_lines.toLocaleString()} lines
              </span>
              <span className="flex items-center gap-1.5">
                <Package size={14} className="text-gray-400" />
                {summary.total_functions} functions, {summary.total_classes} classes
              </span>
            </div>
          </div>
          <span className="text-gray-400 mt-2">
            {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          </span>
        </div>
      </button>

      {expanded && (
        <div className="px-6 pb-6 border-t border-gray-100">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-5">
            {/* Languages breakdown */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">
                Languages
              </h4>
              <div className="space-y-2">
                {languages.map(([lang, count]) => (
                  <div key={lang} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700 capitalize">{lang}</span>
                    <span className="text-gray-500">
                      {count} file{count !== 1 ? 's' : ''}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Quality indicators */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">
                Quality Indicators
              </h4>
              <div className="space-y-3">
                <ScoreBar
                  score={summary.docstring_coverage}
                  label="Documentation"
                  size="sm"
                />
                <ScoreBar
                  score={summary.type_hint_coverage}
                  label="Type Hints"
                  size="sm"
                />
                <div className="flex items-center gap-2 text-sm">
                  {summary.has_tests ? (
                    <CheckCircle2 size={14} className="text-emerald-500" />
                  ) : (
                    <XCircle size={14} className="text-gray-300" />
                  )}
                  <span className={summary.has_tests ? 'text-gray-700' : 'text-gray-400'}>
                    Test suite
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  {summary.has_ci_config ? (
                    <CheckCircle2 size={14} className="text-emerald-500" />
                  ) : (
                    <XCircle size={14} className="text-gray-300" />
                  )}
                  <span className={summary.has_ci_config ? 'text-gray-700' : 'text-gray-400'}>
                    CI/CD configured
                  </span>
                </div>
              </div>
            </div>

            {/* Key capabilities */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">
                Detected Capabilities
              </h4>
              {summary.key_capabilities.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {summary.key_capabilities.map((cap) => (
                    <Badge key={cap} label={cap} variant="info" />
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">No capabilities detected</p>
              )}
            </div>
          </div>

          {/* External packages */}
          {summary.external_packages.length > 0 && (
            <div className="mt-5">
              <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1.5">
                <Globe size={14} />
                External Dependencies ({summary.external_packages.length})
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {summary.external_packages.map((pkg) => (
                  <span
                    key={pkg}
                    className="text-xs font-mono text-gray-600 bg-gray-50 px-2 py-1 rounded"
                  >
                    {pkg}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Top-level packages */}
          {summary.top_level_packages.length > 0 && (
            <div className="mt-5">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">
                Top-Level Packages
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {summary.top_level_packages.map((pkg) => (
                  <span
                    key={pkg}
                    className="text-xs font-mono text-gray-600 bg-gray-50 px-2 py-1 rounded"
                  >
                    {pkg}/
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CandidateRow({
  candidate,
  rank,
  isWholeCodebase,
  repoPath,
  onGenerate,
  isGenerating,
}: {
  candidate: Candidate;
  rank: number;
  isWholeCodebase: boolean;
  repoPath: string;
  onGenerate: (candidate: Candidate) => void;
  isGenerating: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`rounded-xl border overflow-hidden ${
        isWholeCodebase
          ? 'bg-gradient-to-r from-indigo-50/50 to-purple-50/50 border-indigo-200'
          : 'bg-white border-gray-200'
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-5 py-4 cursor-pointer hover:bg-gray-50/50 transition-colors"
      >
        <div className="flex items-start gap-4">
          {/* Rank */}
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
              isWholeCodebase
                ? 'bg-gradient-to-br from-indigo-500 to-purple-600'
                : 'bg-indigo-50'
            }`}
          >
            {isWholeCodebase ? (
              <Globe size={14} className="text-white" />
            ) : (
              <span className="text-sm font-bold text-indigo-600">#{rank}</span>
            )}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h3 className="font-semibold text-gray-900">
                {isWholeCodebase ? 'Entire Codebase' : candidate.name}
              </h3>
              <span className="text-xs text-gray-500">
                {candidate.source_files.length} file{candidate.source_files.length !== 1 ? 's' : ''}
              </span>
              {candidate.size_class && (
                <SizeClassBadge sizeClass={candidate.size_class} />
              )}
              {isWholeCodebase && (
                <Badge label="Full Repository" variant="info" />
              )}
            </div>
            <p className="text-sm text-gray-600 line-clamp-2">{candidate.description}</p>

            {/* Tags */}
            {!isWholeCodebase && candidate.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {candidate.tags
                  .filter((t) => t !== 'whole-codebase' && t !== 'full-repository')
                  .slice(0, 6)
                  .map((tag) => (
                    <Badge key={tag} label={tag} variant="info" />
                  ))}
                {candidate.tags.length > 6 && (
                  <Badge label={`+${candidate.tags.length - 6}`} variant="default" />
                )}
              </div>
            )}
          </div>

          {/* Score and expand */}
          <div className="flex items-center gap-4 flex-shrink-0">
            <div className="w-32">
              <ScoreBar score={candidate.overall_score} label="Overall" size="sm" />
            </div>
            <span className="text-gray-400">
              {expanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
            </span>
          </div>
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-5 border-t border-gray-100">
          {/* Generate Library button */}
          <div className="mt-4 mb-4">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onGenerate(candidate);
              }}
              disabled={isGenerating}
              className="flex items-center gap-2 px-4 py-2.5 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isGenerating ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <BookOpen size={16} />
              )}
              {isGenerating
                ? 'Generating Library...'
                : isWholeCodebase
                  ? 'Generate Codebase Library'
                  : 'Generate Component Library'}
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Score dimensions */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Score Breakdown</h4>
              <div className="space-y-3">
                {candidate.scoring.dimensions.length > 0 ? (
                  candidate.scoring.dimensions.map((dim) => (
                    <div key={dim.name}>
                      <ScoreBar
                        score={dim.score}
                        label={`${dim.name.replace(/_/g, ' ')} (w:${dim.weight})`}
                        size="sm"
                      />
                      {dim.reasons.length > 0 && (
                        <ul className="mt-1 ml-2">
                          {dim.reasons.slice(0, 2).map((r, i) => (
                            <li key={i} className="text-xs text-gray-500">
                              {r}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))
                ) : (
                  <>
                    <ScoreBar score={candidate.isolation_score} label="Isolation" size="sm" />
                    <ScoreBar score={candidate.reuse_score} label="Reuse" size="sm" />
                    <ScoreBar score={candidate.complexity_score} label="Complexity" size="sm" />
                    <ScoreBar score={candidate.clarity_score} label="Clarity" size="sm" />
                  </>
                )}
              </div>
            </div>

            {/* Details */}
            <div className="space-y-4">
              {/* Top reasons */}
              {candidate.scoring.top_reasons.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
                    <Lightbulb size={14} />
                    Top Reasons
                  </h4>
                  <ul className="space-y-1">
                    {candidate.scoring.top_reasons.map((reason, i) => (
                      <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                        <span className="text-indigo-400 mt-1 flex-shrink-0">--</span>
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Flags */}
              {candidate.scoring.all_flags.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
                    <Flag size={14} />
                    Flags
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {candidate.scoring.all_flags.map((flag) => (
                      <Badge key={flag} label={flag} variant="warning" />
                    ))}
                  </div>
                </div>
              )}

              {/* Source files (capped for whole-codebase) */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
                  <FileCode2 size={14} />
                  Source Files
                  {isWholeCodebase && ` (${candidate.source_files.length} total)`}
                </h4>
                <ul className="space-y-1">
                  {candidate.source_files.slice(0, isWholeCodebase ? 10 : 50).map((file) => (
                    <li key={file} className="text-xs font-mono text-gray-600 bg-gray-50 px-2 py-1 rounded">
                      {file}
                    </li>
                  ))}
                  {isWholeCodebase && candidate.source_files.length > 10 && (
                    <li className="text-xs text-gray-500 italic px-2 py-1">
                      ... and {candidate.source_files.length - 10} more files
                    </li>
                  )}
                </ul>
              </div>

              {/* Entry points */}
              {candidate.entry_points.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
                    <Tag size={14} />
                    Entry Points
                    {isWholeCodebase && ` (showing top ${Math.min(candidate.entry_points.length, 15)})`}
                  </h4>
                  <ul className="space-y-1">
                    {candidate.entry_points.slice(0, isWholeCodebase ? 15 : 50).map((ep) => (
                      <li key={ep} className="text-xs font-mono text-gray-600 bg-gray-50 px-2 py-1 rounded">
                        {ep}
                      </li>
                    ))}
                    {isWholeCodebase && candidate.entry_points.length > 15 && (
                      <li className="text-xs text-gray-500 italic px-2 py-1">
                        ... and {candidate.entry_points.length - 15} more entry points
                      </li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* AI Query Panel */}
          <AIQueryPanel
            repoPath={repoPath}
            libraryName={repoPath.split('/').filter(Boolean).pop() || repoPath}
            componentName={candidate.name}
            candidateDescription={candidate.description}
            candidateTags={candidate.tags}
            sourceFiles={candidate.source_files}
            contextSummary={''}
          />
        </div>
      )}
    </div>
  );
}

export default function Analyzer() {
  const [repoPath, setRepoPath] = useState('');
  const [depth, setDepth] = useState<'quick' | 'standard' | 'deep'>('standard');
  const [generatingCandidate, setGeneratingCandidate] = useState<string | null>(null);
  const navigate = useNavigate();

  // GitHub search state
  const [showGitHubSearch, setShowGitHubSearch] = useState(false);
  const [ghQuery, setGhQuery] = useState('');
  const [ghLanguage, setGhLanguage] = useState('');
  const [ghResults, setGhResults] = useState<GitHubRepoResult[]>([]);

  const mutation = useMutation({
    mutationFn: () => analyzeRepo(repoPath, depth),
  });

  const generateMutation = useMutation({
    mutationFn: (candidate: Candidate) =>
      generateHierarchicalLibrary({
        repo_path: repoPath,
        candidate_name: candidate.name,
        candidate_description: candidate.description,
        source_files: candidate.source_files,
        entry_points: candidate.entry_points,
        tags: candidate.tags,
      }),
    onSuccess: (data) => {
      setGeneratingCandidate(null);
      if (data.success && data.library) {
        navigate(`/libraries/${data.library.id}`);
      }
    },
    onError: () => {
      setGeneratingCandidate(null);
    },
  });

  const ghSearchMutation = useMutation({
    mutationFn: () => searchGitHubRepos({ query: ghQuery, language: ghLanguage }),
    onSuccess: (data) => {
      setGhResults(data.results);
    },
  });

  const handleGenerate = (candidate: Candidate) => {
    setGeneratingCandidate(candidate.name);
    generateMutation.mutate(candidate);
  };

  const handleSelectGhRepo = (repo: GitHubRepoResult) => {
    setRepoPath(repo.clone_url);
    setShowGitHubSearch(false);
  };

  const result: AnalyzeResult | undefined = mutation.data;
  const candidates = result?.candidates ?? [];
  const summary = result?.summary;

  // Separate whole-codebase candidate from component candidates
  const wholeCodebaseCandidate = candidates.find(
    (c) => c.name === '__whole_codebase__'
  );
  const componentCandidates = candidates.filter(
    (c) => c.name !== '__whole_codebase__'
  );

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Search size={24} className="text-indigo-600" />
          Repository Analyzer
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Analyze a repository to discover extractable library candidates
        </p>
      </div>

      {/* GitHub Repo Search */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-4">
        <button
          onClick={() => setShowGitHubSearch(!showGitHubSearch)}
          className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-indigo-600 transition-colors"
        >
          {showGitHubSearch ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <Globe size={16} />
          Search GitHub for Repositories
        </button>

        {showGitHubSearch && (
          <div className="mt-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-3">
              <div className="md:col-span-2">
                <input
                  type="text"
                  placeholder="Search keywords (e.g. rate limiter, auth middleware)"
                  value={ghQuery}
                  onChange={(e) => setGhQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && ghQuery.trim() && ghSearchMutation.mutate()}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
              <div>
                <select
                  value={ghLanguage}
                  onChange={(e) => setGhLanguage(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                  <option value="">Any Language</option>
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="typescript">TypeScript</option>
                  <option value="go">Go</option>
                  <option value="rust">Rust</option>
                  <option value="java">Java</option>
                  <option value="csharp">C#</option>
                  <option value="ruby">Ruby</option>
                </select>
              </div>
              <div>
                <button
                  onClick={() => ghSearchMutation.mutate()}
                  disabled={!ghQuery.trim() || ghSearchMutation.isPending}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-800 text-white text-sm font-medium rounded-lg hover:bg-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {ghSearchMutation.isPending ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Search size={14} />
                  )}
                  Search GitHub
                </button>
              </div>
            </div>

            {ghSearchMutation.error && (
              <p className="text-sm text-red-600 mb-3">
                {ghSearchMutation.error instanceof Error
                  ? ghSearchMutation.error.message
                  : 'Search failed'}
              </p>
            )}

            {ghResults.length > 0 && (
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="max-h-80 overflow-y-auto">
                  {ghResults.map((repo) => (
                    <button
                      key={repo.full_name}
                      onClick={() => handleSelectGhRepo(repo)}
                      className="w-full text-left px-4 py-3 border-b border-gray-100 last:border-b-0 hover:bg-indigo-50/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className="font-medium text-sm text-gray-900">
                              {repo.full_name}
                            </span>
                            {repo.language && (
                              <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                                {repo.language}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-600 line-clamp-1">
                            {repo.description || 'No description'}
                          </p>
                          {repo.topics.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {repo.topics.slice(0, 5).map((topic) => (
                                <span key={topic} className="text-xs text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">
                                  {topic}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-gray-500 flex-shrink-0">
                          <span className="flex items-center gap-1">
                            <Star size={12} /> {repo.stargazers_count.toLocaleString()}
                          </span>
                          <span className="flex items-center gap-1">
                            <GitFork size={12} /> {repo.forks_count.toLocaleString()}
                          </span>
                          <a
                            href={repo.html_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-gray-400 hover:text-indigo-600"
                          >
                            <ExternalLink size={12} />
                          </a>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input form */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="md:col-span-2">
            <label
              htmlFor="repo-path"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Repository Path or URL
            </label>
            <input
              id="repo-path"
              type="text"
              placeholder="/path/to/repository or https://github.com/owner/repo.git"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Analysis Depth
            </label>
            <div className="flex rounded-lg border border-gray-300 overflow-hidden">
              {(['quick', 'standard', 'deep'] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setDepth(d)}
                  className={`flex-1 px-3 py-2 text-sm font-medium capitalize transition-colors ${
                    depth === d
                      ? 'bg-indigo-600 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
        </div>

        <button
          onClick={() => mutation.mutate()}
          disabled={!repoPath || mutation.isPending}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {mutation.isPending ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Search size={16} />
          )}
          Analyze
        </button>
      </div>

      {/* Loading */}
      {mutation.isPending && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <Loader2 size={40} className="animate-spin text-indigo-600 mx-auto mb-4" />
            <p className="text-sm text-gray-600 font-medium">Analyzing repository...</p>
            <p className="text-xs text-gray-400 mt-1">
              {depth === 'deep'
                ? 'Deep analysis may take several minutes'
                : depth === 'quick'
                  ? 'Quick scan in progress'
                  : 'Standard analysis in progress'}
            </p>
          </div>
        </div>
      )}

      {/* Error */}
      {mutation.error && !mutation.isPending && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
          <h3 className="text-red-800 font-semibold mb-1">Analysis Error</h3>
          <p className="text-sm text-red-700">
            {mutation.error instanceof Error
              ? mutation.error.message
              : 'An unknown error occurred'}
          </p>
        </div>
      )}

      {/* Results */}
      {result && !mutation.isPending && (
        <div>
          {/* Codebase summary */}
          {summary && summary.total_files > 0 && (
            <CodebaseSummaryCard summary={summary} />
          )}

          {/* Generate error toast */}
          {generateMutation.error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
              <p className="text-sm text-red-700">
                {generateMutation.error instanceof Error
                  ? generateMutation.error.message
                  : 'Failed to generate library'}
              </p>
            </div>
          )}

          {/* Whole codebase option */}
          {wholeCodebaseCandidate && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Globe size={18} className="text-indigo-600" />
                Full Repository Option
              </h2>
              <CandidateRow
                candidate={wholeCodebaseCandidate}
                rank={0}
                isWholeCodebase
                repoPath={repoPath}
                onGenerate={handleGenerate}
                isGenerating={generatingCandidate === wholeCodebaseCandidate.name}
              />
            </div>
          )}

          {/* Component candidates */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Component Candidates ({componentCandidates.length})
            </h2>
            <span className="text-xs text-gray-500">Ranked by overall score</span>
          </div>

          {componentCandidates.length === 0 ? (
            <EmptyState
              title="No component candidates found"
              description="No extractable library candidates were found in this repository. Try a different path or depth setting. You can still use the full repository option above."
              icon={Search}
            />
          ) : (
            <div className="space-y-3">
              {componentCandidates.map((candidate, i) => (
                <CandidateRow
                  key={candidate.name}
                  candidate={candidate}
                  rank={i + 1}
                  isWholeCodebase={false}
                  repoPath={repoPath}
                  onGenerate={handleGenerate}
                  isGenerating={generatingCandidate === candidate.name}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
