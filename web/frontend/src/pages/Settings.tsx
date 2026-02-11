import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Key, Plus, Trash2, Copy, Check, AlertTriangle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { listAPIKeys, createAPIKey, deleteAPIKey } from '../api/client';
import type { APIKeyEntry } from '../types';

function formatDate(dateStr: string): string {
  if (!dateStr) return 'Never';
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

function KeyRow({
  apiKey,
  onDelete,
  deleting,
}: {
  apiKey: APIKeyEntry;
  onDelete: (id: string) => void;
  deleting: boolean;
}) {
  const [confirmDelete, setConfirmDelete] = useState(false);

  return (
    <tr className="border-t border-gray-100 hover:bg-gray-50/50 transition-colors">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <Key size={14} className="text-gray-400" />
          <span className="text-sm font-medium text-gray-900">{apiKey.name}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <code className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-600 font-mono">
          {apiKey.prefix}...
        </code>
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">{formatDate(apiKey.created_at)}</td>
      <td className="px-4 py-3 text-sm text-gray-500">{formatDate(apiKey.last_used)}</td>
      <td className="px-4 py-3 text-sm text-gray-500">{formatDate(apiKey.expires_at)}</td>
      <td className="px-4 py-3 text-right">
        {confirmDelete ? (
          <div className="flex items-center justify-end gap-2">
            <span className="text-xs text-red-600">Delete?</span>
            <button
              onClick={() => onDelete(apiKey.id)}
              disabled={deleting}
              className="px-2 py-1 text-xs font-medium text-white bg-red-600 rounded hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              Yes
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="px-2 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
            >
              No
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmDelete(true)}
            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
            title="Delete key"
          >
            <Trash2 size={14} />
          </button>
        )}
      </td>
    </tr>
  );
}

function CreateKeyModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (rawKey: string) => void;
}) {
  const { token } = useAuth();
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error('Not authenticated');
      return createAPIKey(token, name);
    },
    onSuccess: (data) => {
      onCreated(data.raw_key);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to create key');
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Create API Key</h3>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="mb-6">
          <label htmlFor="key-name" className="block text-sm font-medium text-gray-700 mb-1.5">
            Key Name
          </label>
          <input
            id="key-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., CI/CD Pipeline, Local Development"
            className="w-full px-3 py-2.5 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            autoFocus
          />
          <p className="mt-1.5 text-xs text-gray-500">
            A descriptive name to identify where this key is used.
          </p>
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
            {mutation.isPending ? 'Creating...' : 'Create Key'}
          </button>
        </div>
      </div>
    </div>
  );
}

function RawKeyDisplay({ rawKey, onDone }: { rawKey: string; onDone: () => void }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(rawKey).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 p-6">
        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-amber-50 flex items-center justify-center flex-shrink-0">
            <AlertTriangle size={20} className="text-amber-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">API Key Created</h3>
            <p className="text-sm text-gray-500 mt-1">
              Copy your key now. You will not be able to see it again.
            </p>
          </div>
        </div>

        <div className="bg-gray-900 rounded-lg p-4 mb-6 flex items-center gap-3">
          <code className="flex-1 text-sm text-emerald-400 font-mono break-all">{rawKey}</code>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white/10 text-white rounded-md hover:bg-white/20 transition-colors text-xs font-medium flex-shrink-0"
          >
            {copied ? (
              <>
                <Check size={14} />
                Copied
              </>
            ) : (
              <>
                <Copy size={14} />
                Copy
              </>
            )}
          </button>
        </div>

        <div className="flex justify-end">
          <button
            onClick={onDone}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

function SkeletonRow() {
  return (
    <tr className="border-t border-gray-100 animate-pulse">
      <td className="px-4 py-3"><div className="h-4 bg-gray-200 rounded w-32" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-100 rounded w-20" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-100 rounded w-24" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-100 rounded w-24" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-100 rounded w-24" /></td>
      <td className="px-4 py-3"><div className="h-4 bg-gray-100 rounded w-8 ml-auto" /></td>
    </tr>
  );
}

export default function Settings() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [rawKey, setRawKey] = useState<string | null>(null);

  const {
    data: keys,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => {
      if (!token) throw new Error('Not authenticated');
      return listAPIKeys(token);
    },
    enabled: !!token,
  });

  const deleteMutation = useMutation({
    mutationFn: async (keyId: string) => {
      if (!token) throw new Error('Not authenticated');
      return deleteAPIKey(token, keyId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
  });

  function handleCreated(key: string) {
    setShowCreate(false);
    setRawKey(key);
    queryClient.invalidateQueries({ queryKey: ['api-keys'] });
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Manage your API keys and account settings</p>
      </div>

      {/* API Keys section */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-gray-900">API Keys</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Manage keys for programmatic access to the ALE API
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors"
          >
            <Plus size={16} />
            Create Key
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="px-6 py-4">
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
              <p className="text-sm text-red-700">
                Failed to load API keys: {error instanceof Error ? error.message : 'Unknown error'}
              </p>
            </div>
          </div>
        )}

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50/50">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Key
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Used
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Expires
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <>
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                </>
              )}
              {!isLoading && keys && keys.length > 0 && keys.map((k: APIKeyEntry) => (
                <KeyRow
                  key={k.id}
                  apiKey={k}
                  onDelete={(id) => deleteMutation.mutate(id)}
                  deleting={deleteMutation.isPending}
                />
              ))}
            </tbody>
          </table>
        </div>

        {/* Empty state */}
        {!isLoading && !error && keys && keys.length === 0 && (
          <div className="px-6 py-12 text-center">
            <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
              <Key size={20} className="text-gray-400" />
            </div>
            <h3 className="text-sm font-semibold text-gray-900 mb-1">No API keys</h3>
            <p className="text-sm text-gray-500 mb-4">
              Create an API key to access ALE programmatically from scripts or CI/CD pipelines.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
            >
              <Plus size={16} />
              Create your first key
            </button>
          </div>
        )}
      </div>

      {/* Modals */}
      {showCreate && (
        <CreateKeyModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
      )}
      {rawKey && (
        <RawKeyDisplay rawKey={rawKey} onDone={() => setRawKey(null)} />
      )}
    </div>
  );
}
