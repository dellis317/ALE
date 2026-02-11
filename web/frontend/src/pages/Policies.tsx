import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Shield,
  Plus,
  Trash2,
  Save,
  ToggleLeft,
  ToggleRight,
  FlaskConical,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Loader2,
} from 'lucide-react';
import {
  listPolicies,
  createPolicy,
  updatePolicy,
  deletePolicy,
  togglePolicy,
  evaluatePolicy,
} from '../api/client';
import PolicyRuleEditor from '../components/PolicyRuleEditor';
import type { Policy, PolicyRule, PolicyEvaluation } from '../types';

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

function actionBadge(action: string) {
  switch (action) {
    case 'deny':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700">
          <XCircle size={12} />
          Deny
        </span>
      );
    case 'require_approval':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700">
          <AlertTriangle size={12} />
          Require Approval
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-emerald-100 text-emerald-700">
          <CheckCircle2 size={12} />
          Allow
        </span>
      );
  }
}

function scopeBadge(scope: string) {
  const colors: Record<string, string> = {
    file: 'bg-blue-100 text-blue-700',
    directory: 'bg-purple-100 text-purple-700',
    capability: 'bg-orange-100 text-orange-700',
    library: 'bg-indigo-100 text-indigo-700',
    all: 'bg-gray-100 text-gray-700',
  };
  return (
    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${colors[scope] || colors.all}`}>
      {scope}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Left panel: Policy list
// ---------------------------------------------------------------------------

function PolicyListItem({
  policy,
  selected,
  onSelect,
  onToggle,
}: {
  policy: Policy;
  selected: boolean;
  onSelect: () => void;
  onToggle: () => void;
}) {
  return (
    <div
      onClick={onSelect}
      className={`px-4 py-3 border-b border-gray-100 cursor-pointer transition-colors ${
        selected ? 'bg-indigo-50 border-l-2 border-l-indigo-600' : 'hover:bg-gray-50'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-900 truncate">{policy.name}</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {policy.rules.length} rule{policy.rules.length !== 1 ? 's' : ''} &middot; v{policy.version}
          </p>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggle();
          }}
          className="flex-shrink-0 ml-2"
          title={policy.enabled ? 'Disable policy' : 'Enable policy'}
        >
          {policy.enabled ? (
            <ToggleRight size={22} className="text-indigo-600" />
          ) : (
            <ToggleLeft size={22} className="text-gray-400" />
          )}
        </button>
      </div>
    </div>
  );
}

function PolicyListSkeleton() {
  return (
    <div className="animate-pulse">
      {[1, 2, 3].map((i) => (
        <div key={i} className="px-4 py-3 border-b border-gray-100">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
          <div className="h-3 bg-gray-100 rounded w-1/2" />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Right panel: Policy detail & editor
// ---------------------------------------------------------------------------

function PolicyDetail({
  policy,
  onUpdate,
  onDelete,
}: {
  policy: Policy;
  onUpdate: (data: { name?: string; description?: string; rules?: PolicyRule[] }) => void;
  onDelete: () => void;
}) {
  const [name, setName] = useState(policy.name);
  const [description, setDescription] = useState(policy.description);
  const [rules, setRules] = useState<PolicyRule[]>(policy.rules);
  const [editingRuleIndex, setEditingRuleIndex] = useState<number | null>(null);
  const [addingRule, setAddingRule] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [dirty, setDirty] = useState(false);

  // Test policy evaluation
  const [testLibrary, setTestLibrary] = useState('');
  const [testFiles, setTestFiles] = useState('');
  const [testCapabilities, setTestCapabilities] = useState('');
  const [testResult, setTestResult] = useState<PolicyEvaluation | null>(null);

  const testMutation = useMutation({
    mutationFn: async () => {
      const files = testFiles
        .split(',')
        .map((f) => f.trim())
        .filter(Boolean);
      const caps = testCapabilities
        .split(',')
        .map((c) => c.trim())
        .filter(Boolean);
      return evaluatePolicy(testLibrary, '1.0.0', files, caps);
    },
    onSuccess: (data) => setTestResult(data),
  });

  // Reset state when policy changes
  useState(() => {
    setName(policy.name);
    setDescription(policy.description);
    setRules(policy.rules);
    setDirty(false);
    setEditingRuleIndex(null);
    setAddingRule(false);
    setTestResult(null);
  });

  function handleSave() {
    onUpdate({ name, description, rules });
    setDirty(false);
  }

  function handleSaveRule(index: number, rule: PolicyRule) {
    const updated = [...rules];
    updated[index] = rule;
    setRules(updated);
    setEditingRuleIndex(null);
    setDirty(true);
  }

  function handleAddRule(rule: PolicyRule) {
    setRules([...rules, rule]);
    setAddingRule(false);
    setDirty(true);
  }

  function handleDeleteRule(index: number) {
    setRules(rules.filter((_, i) => i !== index));
    setDirty(true);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <input
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setDirty(true);
            }}
            className="text-xl font-bold text-gray-900 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-indigo-500 focus:outline-none w-full pb-1"
          />
          <textarea
            value={description}
            onChange={(e) => {
              setDescription(e.target.value);
              setDirty(true);
            }}
            placeholder="Add a description..."
            rows={2}
            className="mt-2 w-full text-sm text-gray-500 bg-transparent border border-transparent hover:border-gray-300 focus:border-indigo-500 focus:outline-none rounded-lg px-2 py-1 resize-none"
          />
        </div>
      </div>

      {/* Meta info */}
      <div className="flex items-center gap-4 text-xs text-gray-400">
        <span>Version {policy.version}</span>
        {policy.created_at && <span>Created {formatDate(policy.created_at)}</span>}
        {policy.updated_at && <span>Updated {formatDate(policy.updated_at)}</span>}
        <span className={policy.enabled ? 'text-emerald-600' : 'text-gray-400'}>
          {policy.enabled ? 'Enabled' : 'Disabled'}
        </span>
      </div>

      {/* Rules section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900">
            Rules ({rules.length})
          </h3>
          <button
            onClick={() => setAddingRule(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
          >
            <Plus size={14} />
            Add Rule
          </button>
        </div>

        <div className="space-y-3">
          {rules.map((rule, index) =>
            editingRuleIndex === index ? (
              <PolicyRuleEditor
                key={index}
                rule={rule}
                onSave={(updated) => handleSaveRule(index, updated)}
                onCancel={() => setEditingRuleIndex(null)}
              />
            ) : (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900">{rule.name}</span>
                    {scopeBadge(rule.scope)}
                    {actionBadge(rule.action)}
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setEditingRuleIndex(index)}
                      className="px-2 py-1 text-xs font-medium text-gray-600 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeleteRule(index)}
                      className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
                {rule.description && (
                  <p className="text-xs text-gray-500 mb-2">{rule.description}</p>
                )}
                {rule.patterns.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {rule.patterns.map((pattern, pi) => (
                      <code
                        key={pi}
                        className="text-xs bg-gray-100 px-2 py-0.5 rounded font-mono text-gray-600"
                      >
                        {pattern}
                      </code>
                    ))}
                  </div>
                )}
                {rule.rationale && (
                  <p className="text-xs text-gray-400 italic mt-1">{rule.rationale}</p>
                )}
              </div>
            )
          )}

          {addingRule && (
            <PolicyRuleEditor
              onSave={handleAddRule}
              onCancel={() => setAddingRule(false)}
            />
          )}

          {rules.length === 0 && !addingRule && (
            <div className="text-center py-8 border border-dashed border-gray-300 rounded-lg">
              <FileText size={24} className="mx-auto text-gray-400 mb-2" />
              <p className="text-sm text-gray-500">No rules defined yet</p>
              <button
                onClick={() => setAddingRule(true)}
                className="mt-2 text-xs text-indigo-600 hover:text-indigo-500 font-medium"
              >
                Add your first rule
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-3 border-t border-gray-200 pt-4">
        <button
          onClick={handleSave}
          disabled={!dirty}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Save size={16} />
          Save Changes
        </button>
        {confirmDelete ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-red-600">Delete this policy?</span>
            <button
              onClick={onDelete}
              className="px-3 py-1.5 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
            >
              Yes, Delete
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmDelete(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
          >
            <Trash2 size={16} />
            Delete
          </button>
        )}
      </div>

      {/* Test Policy section */}
      <div className="border-t border-gray-200 pt-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <FlaskConical size={16} />
          Test Policy
        </h3>
        <div className="grid grid-cols-3 gap-3 mb-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Library Name</label>
            <input
              type="text"
              value={testLibrary}
              onChange={(e) => setTestLibrary(e.target.value)}
              placeholder="e.g., my-library"
              className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Target Files <span className="text-gray-400 font-normal">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={testFiles}
              onChange={(e) => setTestFiles(e.target.value)}
              placeholder="e.g., src/main.py, .env"
              className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Capabilities <span className="text-gray-400 font-normal">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={testCapabilities}
              onChange={(e) => setTestCapabilities(e.target.value)}
              placeholder="e.g., file_write, network"
              className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
        </div>
        <button
          onClick={() => testMutation.mutate()}
          disabled={!testLibrary.trim() || testMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-gray-800 rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {testMutation.isPending ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <FlaskConical size={16} />
          )}
          Run Test
        </button>

        {testResult && (
          <div
            className={`mt-4 border rounded-lg p-4 ${
              testResult.allowed
                ? 'border-emerald-200 bg-emerald-50'
                : testResult.action === 'require_approval'
                  ? 'border-amber-200 bg-amber-50'
                  : 'border-red-200 bg-red-50'
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              {testResult.allowed ? (
                <CheckCircle2 size={18} className="text-emerald-600" />
              ) : testResult.action === 'require_approval' ? (
                <AlertTriangle size={18} className="text-amber-600" />
              ) : (
                <XCircle size={18} className="text-red-600" />
              )}
              <span className="text-sm font-semibold">
                {testResult.allowed
                  ? 'Allowed'
                  : testResult.action === 'require_approval'
                    ? 'Requires Approval'
                    : 'Denied'}
              </span>
            </div>
            {testResult.reasons.length > 0 && (
              <ul className="space-y-1">
                {testResult.reasons.map((reason, i) => (
                  <li key={i} className="text-xs text-gray-700">
                    {reason}
                  </li>
                ))}
              </ul>
            )}
            {testResult.matched_rules.length === 0 && (
              <p className="text-xs text-gray-500">No rules matched this context.</p>
            )}
          </div>
        )}

        {testMutation.isError && (
          <div className="mt-4 border border-red-200 bg-red-50 rounded-lg p-4">
            <p className="text-sm text-red-700">
              Test failed: {testMutation.error instanceof Error ? testMutation.error.message : 'Unknown error'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create Policy Modal
// ---------------------------------------------------------------------------

function CreatePolicyModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: async () => createPolicy(name, description),
    onSuccess: () => onCreated(),
    onError: (err) => setError(err instanceof Error ? err.message : 'Failed to create policy'),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Create Policy</h3>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Policy Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Production Safety Policy"
              className="w-full px-3 py-2.5 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this policy enforces..."
              rows={3}
              className="w-full px-3 py-2.5 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!name.trim() || mutation.isPending}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {mutation.isPending ? 'Creating...' : 'Create Policy'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Policies page
// ---------------------------------------------------------------------------

export default function Policies() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const {
    data: policies,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['policies'],
    queryFn: listPolicies,
  });

  const toggleMutation = useMutation({
    mutationFn: async ({ id, enabled }: { id: string; enabled: boolean }) =>
      togglePolicy(id, enabled),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['policies'] }),
  });

  const updateMutation = useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: { name?: string; description?: string; rules?: PolicyRule[] };
    }) => updatePolicy(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['policies'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => deletePolicy(id),
    onSuccess: () => {
      setSelectedId(null);
      queryClient.invalidateQueries({ queryKey: ['policies'] });
    },
  });

  const selectedPolicy = policies?.find((p) => p.id === selectedId) || null;

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Policies</h1>
        <p className="text-sm text-gray-500 mt-1">
          Define and manage policy rules that govern library applications
        </p>
      </div>

      <div className="flex gap-6">
        {/* Left Panel: Policy List */}
        <div className="w-80 flex-shrink-0">
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-900">All Policies</h2>
              <button
                onClick={() => setShowCreate(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors"
              >
                <Plus size={14} />
                Create
              </button>
            </div>

            {/* Loading */}
            {isLoading && <PolicyListSkeleton />}

            {/* Error */}
            {error && (
              <div className="px-4 py-6">
                <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                  <p className="text-sm text-red-700">
                    Failed to load policies: {error instanceof Error ? error.message : 'Unknown error'}
                  </p>
                </div>
              </div>
            )}

            {/* Policy list */}
            {!isLoading && !error && policies && policies.length > 0 && (
              <div>
                {policies.map((policy) => (
                  <PolicyListItem
                    key={policy.id}
                    policy={policy}
                    selected={policy.id === selectedId}
                    onSelect={() => setSelectedId(policy.id)}
                    onToggle={() =>
                      toggleMutation.mutate({ id: policy.id, enabled: !policy.enabled })
                    }
                  />
                ))}
              </div>
            )}

            {/* Empty */}
            {!isLoading && !error && policies && policies.length === 0 && (
              <div className="px-6 py-12 text-center">
                <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
                  <Shield size={20} className="text-gray-400" />
                </div>
                <h3 className="text-sm font-semibold text-gray-900 mb-1">No policies</h3>
                <p className="text-sm text-gray-500 mb-4">
                  Create a policy to define rules for library applications.
                </p>
                <button
                  onClick={() => setShowCreate(true)}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
                >
                  <Plus size={16} />
                  Create your first policy
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel: Policy Detail */}
        <div className="flex-1 min-w-0">
          {selectedPolicy ? (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <PolicyDetail
                key={selectedPolicy.id}
                policy={selectedPolicy}
                onUpdate={(data) =>
                  updateMutation.mutate({ id: selectedPolicy.id, data })
                }
                onDelete={() => deleteMutation.mutate(selectedPolicy.id)}
              />
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 flex items-center justify-center h-96">
              <div className="text-center">
                <Shield size={48} className="mx-auto text-gray-300 mb-4" />
                <h3 className="text-sm font-semibold text-gray-900 mb-1">
                  Select a policy
                </h3>
                <p className="text-sm text-gray-500">
                  Choose a policy from the list to view and edit its rules
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <CreatePolicyModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            queryClient.invalidateQueries({ queryKey: ['policies'] });
          }}
        />
      )}
    </div>
  );
}
