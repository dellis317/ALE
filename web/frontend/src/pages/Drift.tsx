import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Activity,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  GitCommit,
  User,
  ShieldCheck,
} from 'lucide-react';
import { checkDrift, getProvenance } from '../api/client';
import type { DriftReport, ProvenanceRecord } from '../types';
import Badge from '../components/Badge';
import EmptyState from '../components/EmptyState';

function driftTypeBadgeVariant(
  driftType: string
): 'warning' | 'error' | 'info' | 'default' {
  switch (driftType) {
    case 'version_drift':
      return 'warning';
    case 'validation_drift':
      return 'error';
    case 'implementation_drift':
      return 'info';
    default:
      return 'default';
  }
}

function DriftReportCard({ report }: { report: DriftReport }) {
  return (
    <div
      className={`bg-white rounded-xl border p-5 ${
        report.has_drift ? 'border-amber-200' : 'border-emerald-200'
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{report.library_name}</h3>
          <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
            <span>Applied: v{report.applied_version}</span>
            <span>-&gt;</span>
            <span>Latest: v{report.latest_version}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {report.has_drift ? (
            <div className="flex flex-wrap gap-1.5">
              {report.drift_types.map((dt) => (
                <Badge key={dt} label={dt.replace('_', ' ')} variant={driftTypeBadgeVariant(dt)} />
              ))}
            </div>
          ) : (
            <Badge label="Clean" variant="success" />
          )}
        </div>
      </div>

      {/* Validation status */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-gray-500">Validation:</span>
        {report.validation_still_passes === null ? (
          <span className="text-xs text-gray-400">Unknown</span>
        ) : report.validation_still_passes ? (
          <span className="flex items-center gap-1 text-xs text-emerald-600">
            <CheckCircle2 size={12} />
            Still passes
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-red-600">
            <XCircle size={12} />
            No longer passes
          </span>
        )}
      </div>

      {/* Details */}
      {report.details.length > 0 && (
        <div className="border-t border-gray-100 pt-3">
          <ul className="space-y-1">
            {report.details.map((detail, i) => (
              <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                <AlertTriangle size={12} className="text-amber-400 mt-0.5 flex-shrink-0" />
                {detail}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ProvenanceTimeline({ records }: { records: ProvenanceRecord[] }) {
  if (records.length === 0) {
    return (
      <EmptyState
        title="No provenance records"
        description="No provenance records found for this repository."
        icon={GitCommit}
      />
    );
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-4 top-3 bottom-3 w-0.5 bg-gray-200" />

      <div className="space-y-4">
        {records.map((record, i) => (
          <div key={i} className="relative flex items-start gap-4 pl-1">
            {/* Dot */}
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 z-10 ${
                record.validation_passed
                  ? 'bg-emerald-100 text-emerald-600'
                  : 'bg-red-100 text-red-600'
              }`}
            >
              {record.validation_passed ? (
                <CheckCircle2 size={14} />
              ) : (
                <XCircle size={14} />
              )}
            </div>

            {/* Card */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 flex-1">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900 text-sm">
                    {record.library_name}
                  </span>
                  <span className="text-xs font-mono text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                    v{record.library_version}
                  </span>
                </div>
                <span className="text-xs text-gray-400">
                  {new Date(record.applied_at).toLocaleString()}
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div className="flex items-center gap-1 text-gray-500">
                  <User size={12} />
                  <span>{record.applied_by}</span>
                </div>
                <div className="flex items-center gap-1 text-gray-500">
                  <GitCommit size={12} />
                  <code className="truncate">{record.commit_sha.slice(0, 8)}</code>
                </div>
                <div className="flex items-center gap-1 text-gray-500">
                  <Activity size={12} />
                  <span className="truncate">{record.target_branch}</span>
                </div>
                <div className="flex items-center gap-1">
                  <ShieldCheck size={12} />
                  <span
                    className={
                      record.validation_passed ? 'text-emerald-600' : 'text-red-600'
                    }
                  >
                    {record.validation_passed ? 'Passed' : 'Failed'}
                  </span>
                </div>
              </div>

              {record.validation_evidence && (
                <p className="text-xs text-gray-400 mt-2 truncate">
                  Evidence: {record.validation_evidence}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Drift() {
  const [repoPath, setRepoPath] = useState('');
  const [libraryName, setLibraryName] = useState('');
  const [submittedRepoPath, setSubmittedRepoPath] = useState('');

  const driftMutation = useMutation({
    mutationFn: () => checkDrift(repoPath, libraryName || undefined),
    onSuccess: () => setSubmittedRepoPath(repoPath),
  });

  const provenanceQuery = useQuery({
    queryKey: ['provenance', submittedRepoPath, libraryName],
    queryFn: () => getProvenance(submittedRepoPath, libraryName || undefined),
    enabled: !!submittedRepoPath,
    staleTime: 30000,
  });

  const handleCheck = () => {
    driftMutation.mutate();
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Activity size={24} className="text-indigo-600" />
          Drift Dashboard
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Monitor library drift and view provenance records
        </p>
      </div>

      {/* Input form */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="md:col-span-2">
            <label
              htmlFor="drift-repo-path"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Repository Path
            </label>
            <input
              id="drift-repo-path"
              type="text"
              placeholder="/path/to/repository"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <div>
            <label
              htmlFor="drift-library-name"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Library Name (optional)
            </label>
            <input
              id="drift-library-name"
              type="text"
              placeholder="All libraries"
              value={libraryName}
              onChange={(e) => setLibraryName(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
        </div>

        <button
          onClick={handleCheck}
          disabled={!repoPath || driftMutation.isPending}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {driftMutation.isPending ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Activity size={16} />
          )}
          Check Drift
        </button>
      </div>

      {/* Loading */}
      {driftMutation.isPending && (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <Loader2 size={40} className="animate-spin text-indigo-600 mx-auto mb-4" />
            <p className="text-sm text-gray-600 font-medium">Checking for drift...</p>
          </div>
        </div>
      )}

      {/* Error */}
      {driftMutation.error && !driftMutation.isPending && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-6">
          <h3 className="text-red-800 font-semibold mb-1">Drift Check Error</h3>
          <p className="text-sm text-red-700">
            {driftMutation.error instanceof Error
              ? driftMutation.error.message
              : 'An unknown error occurred'}
          </p>
        </div>
      )}

      {/* Drift Results */}
      {driftMutation.data && !driftMutation.isPending && (
        <div className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Drift Reports</h2>
            <div className="flex items-center gap-3 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Clean: {driftMutation.data.filter((r) => !r.has_drift).length}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                Drifted: {driftMutation.data.filter((r) => r.has_drift).length}
              </span>
            </div>
          </div>

          {driftMutation.data.length === 0 ? (
            <EmptyState
              title="No drift reports"
              description="No applied libraries found in this repository."
              icon={Activity}
            />
          ) : (
            <div className="space-y-3">
              {driftMutation.data.map((report) => (
                <DriftReportCard key={report.library_name} report={report} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Provenance Section */}
      {submittedRepoPath && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Clock size={18} />
              Provenance Timeline
            </h2>
          </div>

          {provenanceQuery.isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 size={24} className="animate-spin text-indigo-600" />
            </div>
          )}

          {provenanceQuery.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-sm text-red-700">
                Failed to load provenance:{' '}
                {provenanceQuery.error instanceof Error
                  ? provenanceQuery.error.message
                  : 'Unknown error'}
              </p>
            </div>
          )}

          {provenanceQuery.data && (
            <ProvenanceTimeline records={provenanceQuery.data} />
          )}
        </div>
      )}
    </div>
  );
}
