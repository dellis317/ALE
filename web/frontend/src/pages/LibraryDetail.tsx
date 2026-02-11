import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  ShieldCheck,
  ExternalLink,
  Star,
  Download,
  Calendar,
  User,
  CheckCircle2,
  XCircle,
  Play,
  History,
  ListChecks,
  AlertTriangle,
  Code2,
  ClipboardCheck,
} from 'lucide-react';
import { getLibrary, getLibraryVersions } from '../api/client';
import Badge from '../components/Badge';

function VerificationRow({
  label,
  passed,
}: {
  label: string;
  passed: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-gray-600">{label}</span>
      {passed ? (
        <span className="flex items-center gap-1 text-emerald-600 text-sm font-medium">
          <CheckCircle2 size={14} />
          Passed
        </span>
      ) : (
        <span className="flex items-center gap-1 text-red-600 text-sm font-medium">
          <XCircle size={14} />
          Failed
        </span>
      )}
    </div>
  );
}

function VersionHistory({ name, currentVersion }: { name: string; currentVersion: string }) {
  const { data: versions, isLoading, error } = useQuery({
    queryKey: ['library-versions', name],
    queryFn: () => getLibraryVersions(name),
    staleTime: 60000,
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
        <div className="h-5 bg-gray-200 rounded w-32 mb-4" />
        <div className="space-y-2">
          <div className="h-4 bg-gray-100 rounded w-full" />
          <div className="h-4 bg-gray-100 rounded w-full" />
        </div>
      </div>
    );
  }

  if (error || !versions || versions.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <History size={18} />
        Version History
      </h2>
      <div className="space-y-2">
        {versions.map((v) => (
          <Link
            key={v.version}
            to={`/library/${name}/${v.version}`}
            className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
              v.version === currentVersion
                ? 'bg-indigo-50 border border-indigo-200 text-indigo-700 font-medium'
                : 'bg-gray-50 border border-gray-100 text-gray-700 hover:bg-gray-100'
            }`}
          >
            <span className="font-mono">v{v.version}</span>
            <div className="flex items-center gap-2">
              {v.version === currentVersion && (
                <Badge label="Current" variant="info" />
              )}
              {v.quality.last_updated && (
                <span className="text-xs text-gray-400">
                  {new Date(v.quality.last_updated).toLocaleDateString()}
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

interface InstructionStep {
  title?: string;
  description?: string;
  code_sketch?: string;
  step_number?: number;
}

function InstructionsDisplay({ instructions }: { instructions: InstructionStep[] }) {
  if (!instructions || instructions.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <ListChecks size={18} />
        Instructions
      </h2>
      <div className="space-y-4">
        {instructions.map((step, i) => (
          <div key={i} className="flex gap-4">
            {/* Step number circle */}
            <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-sm font-bold flex-shrink-0">
              {step.step_number || i + 1}
            </div>
            <div className="flex-1 min-w-0">
              {step.title && (
                <h4 className="text-sm font-semibold text-gray-900 mb-1">{step.title}</h4>
              )}
              {step.description && (
                <p className="text-sm text-gray-600 mb-2">{step.description}</p>
              )}
              {step.code_sketch && (
                <pre className="text-xs bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto">
                  {step.code_sketch}
                </pre>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface GuardrailItem {
  rule?: string;
  severity?: string;
  description?: string;
}

function GuardrailsChecklist({ guardrails }: { guardrails: GuardrailItem[] }) {
  if (!guardrails || guardrails.length === 0) return null;

  function severityVariant(severity: string | undefined): 'error' | 'warning' | 'info' {
    switch (severity?.toLowerCase()) {
      case 'must':
        return 'error';
      case 'should':
        return 'warning';
      case 'may':
        return 'info';
      default:
        return 'info';
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <AlertTriangle size={18} />
        Guardrails
      </h2>
      <div className="space-y-3">
        {guardrails.map((g, i) => (
          <div key={i} className="flex items-start gap-3 px-3 py-2.5 rounded-lg bg-gray-50 border border-gray-100">
            <CheckCircle2 size={16} className="text-gray-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm text-gray-800">{g.rule || g.description || 'Guardrail'}</span>
                {g.severity && (
                  <Badge label={g.severity} variant={severityVariant(g.severity)} />
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface ValidationCriterion {
  description?: string;
  test_approach?: string;
  expected?: string;
}

function ValidationCriteria({ criteria }: { criteria: ValidationCriterion[] }) {
  if (!criteria || criteria.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <ClipboardCheck size={18} />
        Validation Criteria
      </h2>
      <div className="space-y-4">
        {criteria.map((c, i) => (
          <div key={i} className="border-l-2 border-indigo-300 pl-4">
            {c.description && (
              <p className="text-sm font-medium text-gray-900 mb-1">{c.description}</p>
            )}
            {c.test_approach && (
              <div className="flex items-start gap-2 mb-1">
                <span className="text-xs text-gray-500 font-medium min-w-[80px]">Approach:</span>
                <span className="text-xs text-gray-600">{c.test_approach}</span>
              </div>
            )}
            {c.expected && (
              <div className="flex items-start gap-2">
                <span className="text-xs text-gray-500 font-medium min-w-[80px]">Expected:</span>
                <span className="text-xs text-gray-600">{c.expected}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function LibraryDetail() {
  const { name, version } = useParams<{ name: string; version?: string }>();
  const navigate = useNavigate();

  const { data: library, isLoading, error } = useQuery({
    queryKey: ['library', name, version],
    queryFn: () => getLibrary(name!, version),
    enabled: !!name,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-24 mb-6" />
        <div className="h-8 bg-gray-200 rounded w-64 mb-2" />
        <div className="h-4 bg-gray-100 rounded w-48 mb-8" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
            <div className="h-4 bg-gray-100 rounded w-full mb-3" />
            <div className="h-4 bg-gray-100 rounded w-3/4 mb-3" />
            <div className="h-4 bg-gray-100 rounded w-1/2" />
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="h-4 bg-gray-100 rounded w-32 mb-4" />
            <div className="h-4 bg-gray-100 rounded w-full mb-2" />
            <div className="h-4 bg-gray-100 rounded w-full mb-2" />
            <div className="h-4 bg-gray-100 rounded w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6 transition-colors"
        >
          <ArrowLeft size={16} />
          Back to Registry
        </button>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <p className="text-red-700 font-medium">Failed to load library</p>
          <p className="text-sm text-red-600 mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      </div>
    );
  }

  if (!library) return null;

  const complexityVariant =
    library.complexity === 'simple'
      ? 'success'
      : library.complexity === 'moderate'
        ? 'warning'
        : 'error';

  // Extract instructions, guardrails, and validation from library data if available
  // These would come from the agentic_library source data
  const libAny = library as Record<string, unknown>;
  const instructions: InstructionStep[] = Array.isArray(libAny.instructions)
    ? (libAny.instructions as InstructionStep[])
    : [];
  const guardrails: GuardrailItem[] = Array.isArray(libAny.guardrails)
    ? (libAny.guardrails as GuardrailItem[])
    : [];
  const validationCriteria: ValidationCriterion[] = Array.isArray(libAny.validation_criteria)
    ? (libAny.validation_criteria as ValidationCriterion[])
    : [];

  return (
    <div>
      {/* Back button */}
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6 transition-colors"
      >
        <ArrowLeft size={16} />
        Back to Registry
      </button>

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2 flex-wrap">
          <h1 className="text-2xl font-bold text-gray-900">{library.name}</h1>
          <span className="text-sm font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
            v{library.version}
          </span>
          {library.is_verified && (
            <span className="flex items-center gap-1 text-sm font-medium text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full">
              <ShieldCheck size={14} />
              Verified
            </span>
          )}
          <Badge label={library.complexity} variant={complexityVariant} />
        </div>
        <p className="text-gray-600">{library.description}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Overview</h2>

            {/* Capabilities */}
            {library.capabilities.length > 0 && (
              <div className="mb-5">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Capabilities</h3>
                <div className="flex flex-wrap gap-2">
                  {library.capabilities.map((cap) => (
                    <Badge key={cap} label={cap} variant="info" />
                  ))}
                </div>
              </div>
            )}

            {/* Tags */}
            {library.tags.length > 0 && (
              <div className="mb-5">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Tags</h3>
                <div className="flex flex-wrap gap-2">
                  {library.tags.map((tag) => (
                    <Badge key={tag} label={tag} />
                  ))}
                </div>
              </div>
            )}

            {/* Target Languages */}
            {library.target_languages.length > 0 && (
              <div className="mb-5">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Target Languages</h3>
                <div className="flex flex-wrap gap-2">
                  {library.target_languages.map((lang) => (
                    <Badge key={lang} label={lang} variant="default" />
                  ))}
                </div>
              </div>
            )}

            {/* Meta */}
            <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
              <div>
                <span className="text-xs text-gray-500">Spec Version</span>
                <p className="text-sm font-medium text-gray-900">{library.spec_version}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">Language Agnostic</span>
                <p className="text-sm font-medium text-gray-900">
                  {library.language_agnostic ? 'Yes' : 'No'}
                </p>
              </div>
            </div>
          </div>

          {/* Instructions */}
          <InstructionsDisplay instructions={instructions} />

          {/* Guardrails */}
          <GuardrailsChecklist guardrails={guardrails} />

          {/* Validation Criteria */}
          <ValidationCriteria criteria={validationCriteria} />

          {/* Compatibility Targets */}
          {library.compatibility_targets.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Compatibility Targets
              </h2>
              <div className="flex flex-wrap gap-2">
                {library.compatibility_targets.map((target) => (
                  <span
                    key={target}
                    className="inline-flex items-center px-3 py-1.5 rounded-lg bg-gray-50 text-sm text-gray-700 border border-gray-200"
                  >
                    {target}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Source Information */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Source</h2>
            <div className="space-y-3">
              {library.source_repo && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Repository</span>
                  <a
                    href={library.source_repo}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-700"
                  >
                    {library.source_repo}
                    <ExternalLink size={12} />
                  </a>
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Library Path</span>
                <code className="text-sm text-gray-900 bg-gray-100 px-2 py-0.5 rounded font-mono">
                  {library.library_path}
                </code>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Qualified ID</span>
                <code className="text-sm text-gray-900 bg-gray-100 px-2 py-0.5 rounded font-mono">
                  {library.qualified_id}
                </code>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Actions */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <Link
              to={`/conformance?library_path=${encodeURIComponent(library.library_path)}`}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
            >
              <Play size={16} />
              Run Conformance
            </Link>
          </div>

          {/* Maintainer Info */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <User size={18} />
              Maintainer
            </h2>
            <div className="flex items-center gap-3">
              {/* Avatar placeholder */}
              <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                <User size={20} className="text-gray-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {library.quality.maintainer || 'Unknown'}
                </p>
                <p className="text-xs text-gray-500">Library maintainer</p>
              </div>
            </div>
          </div>

          {/* Quality Signals */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Quality</h2>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Rating</span>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <Star
                      key={star}
                      size={14}
                      className={
                        star <= library.quality.rating
                          ? 'text-amber-400 fill-amber-400'
                          : 'text-gray-300'
                      }
                    />
                  ))}
                  <span className="text-xs text-gray-500 ml-1">
                    ({library.quality.rating_count})
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 flex items-center gap-1">
                  <Download size={14} />
                  Downloads
                </span>
                <span className="text-sm font-medium text-gray-900">
                  {library.quality.download_count.toLocaleString()}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 flex items-center gap-1">
                  <Calendar size={14} />
                  Last Updated
                </span>
                <span className="text-sm font-medium text-gray-900">
                  {new Date(library.quality.last_updated).toLocaleDateString()}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Status</span>
                <Badge
                  label={library.quality.maintained ? 'Maintained' : 'Unmaintained'}
                  variant={library.quality.maintained ? 'success' : 'warning'}
                />
              </div>
            </div>
          </div>

          {/* Verification */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Verification</h2>
            <div className="divide-y divide-gray-100">
              <VerificationRow
                label="Schema"
                passed={library.quality.verification.schema_passed}
              />
              <VerificationRow
                label="Validator"
                passed={library.quality.verification.validator_passed}
              />
              <VerificationRow
                label="Hooks Runnable"
                passed={library.quality.verification.hooks_runnable}
              />
            </div>
            {library.quality.verification.verified_at && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <p className="text-xs text-gray-500">
                  Verified {new Date(library.quality.verification.verified_at).toLocaleDateString()}{' '}
                  by {library.quality.verification.verified_by}
                </p>
              </div>
            )}
          </div>

          {/* Version History */}
          {name && <VersionHistory name={name} currentVersion={library.version} />}
        </div>
      </div>
    </div>
  );
}
