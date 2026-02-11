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
} from 'lucide-react';
import { analyzeRepo, generateHierarchicalLibrary } from '../api/client';
import type { Candidate, AnalyzeResult, CodebaseSummary } from '../types';
import ScoreBar from '../components/ScoreBar';
import Badge from '../components/Badge';
import EmptyState from '../components/EmptyState';
import AIQueryPanel from '../components/AIQueryPanel';

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

  const handleGenerate = (candidate: Candidate) => {
    setGeneratingCandidate(candidate.name);
    generateMutation.mutate(candidate);
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

      {/* Input form */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="md:col-span-2">
            <label
              htmlFor="repo-path"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Repository Path
            </label>
            <input
              id="repo-path"
              type="text"
              placeholder="/path/to/repository"
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
