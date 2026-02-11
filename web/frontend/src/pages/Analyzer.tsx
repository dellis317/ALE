import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Search,
  Loader2,
  FileCode2,
  ChevronDown,
  ChevronRight,
  Tag,
  Flag,
  Lightbulb,
} from 'lucide-react';
import { analyzeRepo } from '../api/client';
import type { Candidate } from '../types';
import ScoreBar from '../components/ScoreBar';
import Badge from '../components/Badge';
import EmptyState from '../components/EmptyState';

function CandidateRow({ candidate, rank }: { candidate: Candidate; rank: number }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-5 py-4 cursor-pointer hover:bg-gray-50/50 transition-colors"
      >
        <div className="flex items-start gap-4">
          {/* Rank */}
          <div className="w-8 h-8 rounded-full bg-indigo-50 flex items-center justify-center flex-shrink-0">
            <span className="text-sm font-bold text-indigo-600">#{rank}</span>
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h3 className="font-semibold text-gray-900">{candidate.name}</h3>
              <span className="text-xs text-gray-500">
                {candidate.source_files.length} file{candidate.source_files.length !== 1 ? 's' : ''}
              </span>
            </div>
            <p className="text-sm text-gray-600 line-clamp-1">{candidate.description}</p>

            {/* Tags */}
            {candidate.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {candidate.tags.slice(0, 6).map((tag) => (
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
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
            {/* Score dimensions */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Score Breakdown</h4>
              <div className="space-y-3">
                <ScoreBar score={candidate.isolation_score} label="Isolation" size="sm" />
                <ScoreBar score={candidate.reuse_score} label="Reuse" size="sm" />
                <ScoreBar score={candidate.complexity_score} label="Complexity" size="sm" />
                <ScoreBar score={candidate.clarity_score} label="Clarity" size="sm" />
                {candidate.scoring.dimensions.map((dim) => (
                  <ScoreBar
                    key={dim.name}
                    score={dim.score}
                    label={`${dim.name} (w:${dim.weight})`}
                    size="sm"
                  />
                ))}
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

              {/* Source files */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
                  <FileCode2 size={14} />
                  Source Files
                </h4>
                <ul className="space-y-1">
                  {candidate.source_files.map((file) => (
                    <li key={file} className="text-xs font-mono text-gray-600 bg-gray-50 px-2 py-1 rounded">
                      {file}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Entry points */}
              {candidate.entry_points.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-1">
                    <Tag size={14} />
                    Entry Points
                  </h4>
                  <ul className="space-y-1">
                    {candidate.entry_points.map((ep) => (
                      <li key={ep} className="text-xs font-mono text-gray-600 bg-gray-50 px-2 py-1 rounded">
                        {ep}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Analyzer() {
  const [repoPath, setRepoPath] = useState('');
  const [depth, setDepth] = useState<'quick' | 'standard' | 'deep'>('standard');

  const mutation = useMutation({
    mutationFn: () => analyzeRepo(repoPath, depth),
  });

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
      {mutation.data && !mutation.isPending && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Candidates Found ({mutation.data.length})
            </h2>
            <span className="text-xs text-gray-500">Ranked by overall score</span>
          </div>

          {mutation.data.length === 0 ? (
            <EmptyState
              title="No candidates found"
              description="No extractable library candidates were found in this repository. Try a different path or depth setting."
              icon={Search}
            />
          ) : (
            <div className="space-y-3">
              {mutation.data.map((candidate, i) => (
                <CandidateRow key={candidate.name} candidate={candidate} rank={i + 1} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
