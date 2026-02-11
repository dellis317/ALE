import { useState } from 'react';
import {
  X,
  AlertTriangle,
  ArrowUpCircle,
  GitCommit,
  FileText,
  Tag,
  Plus,
  Minus,
  RefreshCw,
  Copy,
  Loader2,
  ChevronDown,
  ChevronRight,
  Info,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import type { UpdateCheckResult } from '../types';
import Badge from './Badge';

interface UpdateCheckModalProps {
  result: UpdateCheckResult;
  onClose: () => void;
  onUpdate: () => void;
  onCreateFromLatest: (newName: string) => void;
  isUpdating: boolean;
  isCreating: boolean;
}

function SeverityIndicator({ severity }: { severity: string }) {
  const config: Record<string, { icon: typeof AlertTriangle; color: string; bg: string; label: string }> = {
    major: {
      icon: AlertCircle,
      color: 'text-red-600',
      bg: 'bg-red-50 border-red-200',
      label: 'Major Update',
    },
    minor: {
      icon: AlertTriangle,
      color: 'text-amber-600',
      bg: 'bg-amber-50 border-amber-200',
      label: 'Minor Update',
    },
    patch: {
      icon: Info,
      color: 'text-blue-600',
      bg: 'bg-blue-50 border-blue-200',
      label: 'Patch Update',
    },
    none: {
      icon: CheckCircle2,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50 border-emerald-200',
      label: 'Up to Date',
    },
  };

  const c = config[severity] || config.none;
  const Icon = c.icon;

  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${c.bg}`}>
      <Icon size={24} className={c.color} />
      <div>
        <p className={`font-semibold ${c.color}`}>{c.label}</p>
        <p className="text-sm text-gray-600">{severity !== 'none' ? 'Source repository has changed' : 'No changes detected'}</p>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, subValue }: {
  icon: typeof GitCommit;
  label: string;
  value: string | number;
  subValue?: string;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
      <div className="flex items-center gap-2 text-gray-500 mb-1">
        <Icon size={14} />
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="text-lg font-bold text-gray-900">{value}</p>
      {subValue && <p className="text-xs text-gray-500 mt-0.5">{subValue}</p>}
    </div>
  );
}

export default function UpdateCheckModal({
  result,
  onClose,
  onUpdate,
  onCreateFromLatest,
  isUpdating,
  isCreating,
}: UpdateCheckModalProps) {
  const [showCommits, setShowCommits] = useState(false);
  const [showFiles, setShowFiles] = useState(false);
  const [newName, setNewName] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);

  const severityVariant = (s: string): 'error' | 'warning' | 'info' | 'success' => {
    switch (s) {
      case 'major': return 'error';
      case 'minor': return 'warning';
      case 'patch': return 'info';
      default: return 'success';
    }
  };

  const fileStatusLabel = (status: string): string => {
    switch (status) {
      case 'A': return 'Added';
      case 'D': return 'Deleted';
      case 'R': return 'Renamed';
      default: return 'Modified';
    }
  };

  const fileStatusColor = (status: string): string => {
    switch (status) {
      case 'A': return 'text-emerald-600';
      case 'D': return 'text-red-600';
      case 'R': return 'text-blue-600';
      default: return 'text-amber-600';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center">
              <ArrowUpCircle size={22} className="text-indigo-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">Update Check</h2>
              <p className="text-sm text-gray-500">{result.library_name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content - scrollable */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Severity banner */}
          <SeverityIndicator severity={result.severity} />

          {/* Summary */}
          {result.summary && (
            <p className="text-sm text-gray-700 leading-relaxed">{result.summary}</p>
          )}

          {/* Stats grid */}
          {result.has_updates && (
            <div className="grid grid-cols-3 gap-3">
              <StatCard
                icon={GitCommit}
                label="New Commits"
                value={result.new_commit_count}
              />
              <StatCard
                icon={FileText}
                label="Files Changed"
                value={result.files_changed}
                subValue={result.source_files_affected > 0 ? `${result.source_files_affected} source file(s)` : undefined}
              />
              <StatCard
                icon={RefreshCw}
                label="Code Churn"
                value={`${result.total_insertions + result.total_deletions}`}
                subValue={`+${result.total_insertions} / -${result.total_deletions}`}
              />
            </div>
          )}

          {/* Version tags */}
          {result.new_tags.length > 0 && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Tag size={16} className="text-purple-600" />
                <span className="text-sm font-semibold text-purple-800">New Version Tags</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {result.new_tags.map((tag) => (
                  <span key={tag} className="inline-flex items-center px-2.5 py-1 rounded-md bg-purple-100 text-purple-700 text-xs font-mono font-medium">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Source files affected */}
          {result.source_files_affected > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle size={16} className="text-amber-600" />
                <span className="text-sm font-semibold text-amber-800">
                  {result.source_files_affected} Library Source File(s) Modified
                </span>
              </div>
              <ul className="space-y-1">
                {result.source_files_changed.map((f) => (
                  <li key={f} className="text-xs text-amber-700 font-mono flex items-center gap-1.5">
                    <FileText size={12} />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Change Notes */}
          {result.change_notes.length > 0 && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-800 mb-3">Change Summary</h3>
              <ul className="space-y-1.5">
                {result.change_notes.map((note, i) => (
                  <li key={i} className={`text-sm ${note.startsWith('  ') ? 'text-gray-500 font-mono text-xs ml-2' : 'text-gray-700'}`}>
                    {note.startsWith('  ') ? note : note}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Collapsible: Recent commits */}
          {result.commit_messages.length > 0 && (
            <div className="border border-gray-200 rounded-lg">
              <button
                onClick={() => setShowCommits(!showCommits)}
                className="flex items-center justify-between w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors rounded-lg"
              >
                <div className="flex items-center gap-2">
                  <GitCommit size={16} className="text-gray-500" />
                  <span className="text-sm font-medium text-gray-800">
                    Recent Commits ({result.commit_messages.length})
                  </span>
                </div>
                {showCommits ? <ChevronDown size={16} className="text-gray-400" /> : <ChevronRight size={16} className="text-gray-400" />}
              </button>
              {showCommits && (
                <div className="px-4 pb-3 space-y-1.5 border-t border-gray-100 pt-2">
                  {result.commit_messages.map((msg, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs">
                      <span className="text-gray-400 font-mono mt-0.5">{i + 1}.</span>
                      <span className="text-gray-700">{msg}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Collapsible: Changed files */}
          {result.changed_files.length > 0 && (
            <div className="border border-gray-200 rounded-lg">
              <button
                onClick={() => setShowFiles(!showFiles)}
                className="flex items-center justify-between w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors rounded-lg"
              >
                <div className="flex items-center gap-2">
                  <FileText size={16} className="text-gray-500" />
                  <span className="text-sm font-medium text-gray-800">
                    Changed Files ({result.changed_files.length})
                  </span>
                </div>
                {showFiles ? <ChevronDown size={16} className="text-gray-400" /> : <ChevronRight size={16} className="text-gray-400" />}
              </button>
              {showFiles && (
                <div className="px-4 pb-3 space-y-1 border-t border-gray-100 pt-2 max-h-48 overflow-y-auto">
                  {result.changed_files.map((f, i) => (
                    <div key={i} className="flex items-center justify-between text-xs py-0.5">
                      <span className="text-gray-700 font-mono truncate mr-2">{f.path}</span>
                      <span className={`flex-shrink-0 ${fileStatusColor(f.status)}`}>
                        {fileStatusLabel(f.status)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Commit info */}
          {result.current_commit && result.latest_commit && (
            <div className="flex items-center gap-3 text-xs text-gray-400 pt-2">
              <span className="font-mono">{result.current_commit.slice(0, 12)}</span>
              <span>&#8594;</span>
              <span className="font-mono">{result.latest_commit.slice(0, 12)}</span>
            </div>
          )}
        </div>

        {/* Actions footer */}
        {result.has_updates && (
          <div className="px-6 py-4 border-t border-gray-200 space-y-3">
            {/* Create from latest - expandable form */}
            {showCreateForm && (
              <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                <label className="block text-xs font-medium text-gray-700 mb-1.5">
                  New Library Name (optional)
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="Leave empty for auto-generated name"
                    className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  />
                  <button
                    onClick={() => onCreateFromLatest(newName)}
                    disabled={isCreating}
                    className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50"
                  >
                    {isCreating ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Copy size={14} />
                    )}
                    Create
                  </button>
                </div>
              </div>
            )}

            <div className="flex items-center gap-3">
              {/* Update in place */}
              <button
                onClick={onUpdate}
                disabled={isUpdating || isCreating}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
              >
                {isUpdating ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <RefreshCw size={16} />
                )}
                Update Library
              </button>

              {/* Create new from latest */}
              <button
                onClick={() => setShowCreateForm(!showCreateForm)}
                disabled={isUpdating || isCreating}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-white text-gray-700 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                <Copy size={16} />
                Create New from Latest
              </button>
            </div>

            <div className="flex items-start gap-2 text-xs text-gray-500">
              <Info size={14} className="flex-shrink-0 mt-0.5" />
              <p>
                <strong>Update</strong> rebuilds the library in place.{' '}
                <strong>Create New</strong> generates a separate copy so you can compare before replacing.
              </p>
            </div>
          </div>
        )}

        {/* Close button for no-updates case */}
        {!result.has_updates && (
          <div className="px-6 py-4 border-t border-gray-200">
            <button
              onClick={onClose}
              className="w-full px-4 py-2.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
