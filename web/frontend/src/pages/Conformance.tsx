import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  Play,
  ShieldCheck,
  Loader2,
  Clock,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
} from 'lucide-react';
import { runConformance, validateLibrary } from '../api/client';
import type { ConformanceResult, HookResult, ValidationIssue } from '../types';
import GateResult from '../components/GateResult';
import Badge from '../components/Badge';

function HookResultItem({ hook }: { hook: HookResult }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`rounded-lg border ${
        hook.passed ? 'border-gray-200' : 'border-red-200'
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left cursor-pointer"
      >
        {hook.passed ? (
          <CheckCircle2 size={16} className="text-emerald-600 flex-shrink-0" />
        ) : (
          <XCircle size={16} className="text-red-600 flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium text-gray-900 block truncate">
            {hook.description}
          </span>
          <span className="text-xs text-gray-500">{hook.hook_type}</span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <Clock size={12} />
            {hook.duration_ms}ms
          </span>
          <span className="text-gray-400">
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-3 border-t border-gray-100 space-y-3">
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div>
              <span className="text-xs text-gray-500">Exit Code</span>
              <p
                className={`text-sm font-mono ${
                  hook.exit_code === 0 ? 'text-emerald-700' : 'text-red-700'
                }`}
              >
                {hook.exit_code}
              </p>
            </div>
            <div>
              <span className="text-xs text-gray-500">Duration</span>
              <p className="text-sm font-mono text-gray-700">{hook.duration_ms}ms</p>
            </div>
          </div>

          {hook.stdout && (
            <div>
              <span className="text-xs text-gray-500 mb-1 block">stdout</span>
              <pre className="text-xs bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto max-h-48 overflow-y-auto">
                {hook.stdout}
              </pre>
            </div>
          )}

          {hook.stderr && (
            <div>
              <span className="text-xs text-gray-500 mb-1 block">stderr</span>
              <pre className="text-xs bg-red-950 text-red-100 p-3 rounded-lg overflow-x-auto max-h-48 overflow-y-auto">
                {hook.stderr}
              </pre>
            </div>
          )}

          {hook.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-700">{hook.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SemanticIssueRow({ issue, type }: { issue: ValidationIssue; type: 'error' | 'warning' }) {
  return (
    <div
      className={`flex items-start gap-3 px-3 py-2 rounded-lg text-sm ${
        type === 'error' ? 'bg-red-50' : 'bg-amber-50'
      }`}
    >
      {type === 'error' ? (
        <XCircle size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
      ) : (
        <AlertTriangle size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 mb-0.5 flex-wrap">
          <Badge
            label={issue.severity}
            variant={type === 'error' ? 'error' : 'warning'}
          />
          <code className="text-xs text-gray-500">{issue.code}</code>
          {issue.path && (
            <code className="text-xs text-gray-400 truncate">{issue.path}</code>
          )}
        </div>
        <p className={`text-xs ${type === 'error' ? 'text-red-700' : 'text-amber-700'}`}>
          {issue.message}
        </p>
      </div>
    </div>
  );
}

function ConformanceResults({ result }: { result: ConformanceResult }) {
  return (
    <div className="space-y-6">
      {/* Overall banner */}
      <div
        className={`rounded-xl p-5 flex items-center gap-4 ${
          result.all_passed
            ? 'bg-emerald-50 border border-emerald-200'
            : 'bg-red-50 border border-red-200'
        }`}
      >
        {result.all_passed ? (
          <CheckCircle2 size={32} className="text-emerald-600" />
        ) : (
          <XCircle size={32} className="text-red-600" />
        )}
        <div>
          <h3
            className={`text-lg font-bold ${
              result.all_passed ? 'text-emerald-800' : 'text-red-800'
            }`}
          >
            {result.all_passed ? 'All Gates Passed' : 'Conformance Failed'}
          </h3>
          <p className={`text-sm ${result.all_passed ? 'text-emerald-600' : 'text-red-600'}`}>
            {result.library_name} v{result.library_version} (spec {result.spec_version})
          </p>
        </div>
        <div className="ml-auto text-right">
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <Clock size={12} />
            {result.total_duration_ms}ms total
          </span>
        </div>
      </div>

      {/* Gate 1: Schema */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Gate 1: Schema Validation
        </h3>
        <GateResult
          name="Schema Validation"
          passed={result.schema_passed}
          errors={result.schema_errors}
        />
      </div>

      {/* Gate 2: Semantic */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Gate 2: Semantic Validation
        </h3>
        <GateResult
          name="Semantic Validation"
          passed={result.semantic_passed}
          errors={result.semantic_errors.map(
            (e) => `[${e.severity}] ${e.code}: ${e.message} (${e.path})`
          )}
          details={
            result.semantic_warnings.length > 0
              ? `${result.semantic_warnings.length} warning(s)`
              : undefined
          }
        />

        {/* Detailed semantic issues */}
        {(result.semantic_errors.length > 0 || result.semantic_warnings.length > 0) && (
          <div className="mt-3 space-y-2">
            {result.semantic_errors.map((issue, i) => (
              <SemanticIssueRow key={`err-${i}`} issue={issue} type="error" />
            ))}
            {result.semantic_warnings.map((issue, i) => (
              <SemanticIssueRow key={`warn-${i}`} issue={issue} type="warning" />
            ))}
          </div>
        )}
      </div>

      {/* Gate 3: Hooks */}
      <div>
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Gate 3: Hook Execution
        </h3>
        <GateResult
          name="Hook Execution"
          passed={result.hooks_passed}
          details={`${result.hook_results.length} hook(s) executed`}
        />

        {result.hook_results.length > 0 && (
          <div className="mt-3 space-y-2">
            {result.hook_results.map((hook, i) => (
              <HookResultItem key={i} hook={hook} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Conformance() {
  const [searchParams] = useSearchParams();
  const [libraryPath, setLibraryPath] = useState(
    searchParams.get('library_path') || ''
  );
  const [workingDir, setWorkingDir] = useState('.');

  const conformanceMutation = useMutation({
    mutationFn: () => runConformance(libraryPath, workingDir),
  });

  const validateMutation = useMutation({
    mutationFn: () => validateLibrary(libraryPath),
  });

  const isRunning = conformanceMutation.isPending || validateMutation.isPending;
  const result = conformanceMutation.data || validateMutation.data;
  const error = conformanceMutation.error || validateMutation.error;

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <ShieldCheck size={24} className="text-indigo-600" />
          Conformance Runner
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Validate a library against the ALE spec with 3-gate conformance checks
        </p>
      </div>

      {/* Input form */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label
              htmlFor="library-path"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Library Path
            </label>
            <input
              id="library-path"
              type="text"
              placeholder="/path/to/library.yml"
              value={libraryPath}
              onChange={(e) => setLibraryPath(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <div>
            <label
              htmlFor="working-dir"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Working Directory
            </label>
            <input
              id="working-dir"
              type="text"
              placeholder="."
              value={workingDir}
              onChange={(e) => setWorkingDir(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => conformanceMutation.mutate()}
            disabled={!libraryPath || isRunning}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {conformanceMutation.isPending ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Play size={16} />
            )}
            Run Conformance
          </button>
          <button
            onClick={() => validateMutation.mutate()}
            disabled={!libraryPath || isRunning}
            className="flex items-center gap-2 px-4 py-2.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {validateMutation.isPending ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <ShieldCheck size={16} />
            )}
            Validate Only
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isRunning && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <Loader2 size={40} className="animate-spin text-indigo-600 mx-auto mb-4" />
            <p className="text-sm text-gray-600 font-medium">
              {conformanceMutation.isPending
                ? 'Running conformance checks...'
                : 'Validating library...'}
            </p>
            <p className="text-xs text-gray-400 mt-1">This may take a moment</p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && !isRunning && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
          <h3 className="text-red-800 font-semibold mb-1">Execution Error</h3>
          <p className="text-sm text-red-700">
            {error instanceof Error ? error.message : 'An unknown error occurred'}
          </p>
        </div>
      )}

      {/* Results */}
      {result && !isRunning && <ConformanceResults result={result} />}
    </div>
  );
}
