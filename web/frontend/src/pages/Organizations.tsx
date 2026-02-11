import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Building2, Plus, AlertTriangle } from 'lucide-react';
import { listOrgs, createOrg } from '../api/client';
import OrgCard from '../components/OrgCard';
import type { Organization } from '../types';

function CreateOrgModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (org: Organization) => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: async () => {
      return createOrg(name, description);
    },
    onSuccess: (data) => {
      onCreated(data);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to create organization');
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Create Organization</h3>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">
            <div className="flex items-center gap-2">
              <AlertTriangle size={16} className="text-red-600" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        <div className="space-y-4 mb-6">
          <div>
            <label htmlFor="org-name" className="block text-sm font-medium text-gray-700 mb-1.5">
              Organization Name
            </label>
            <input
              id="org-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., My Team, Acme Corp"
              className="w-full px-3 py-2.5 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              autoFocus
            />
          </div>
          <div>
            <label htmlFor="org-desc" className="block text-sm font-medium text-gray-700 mb-1.5">
              Description
            </label>
            <textarea
              id="org-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description of the organization"
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
            {mutation.isPending ? 'Creating...' : 'Create Organization'}
          </button>
        </div>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-gray-200" />
        <div>
          <div className="h-4 bg-gray-200 rounded w-32 mb-2" />
          <div className="h-3 bg-gray-100 rounded w-20" />
        </div>
      </div>
      <div className="h-3 bg-gray-100 rounded w-full mt-4" />
      <div className="flex gap-4 mt-4 pt-4 border-t border-gray-100">
        <div className="h-3 bg-gray-100 rounded w-20" />
        <div className="h-3 bg-gray-100 rounded w-20" />
      </div>
    </div>
  );
}

export default function Organizations() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const {
    data: orgs,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['organizations'],
    queryFn: listOrgs,
  });

  function handleCreated(_org: Organization) {
    setShowCreate(false);
    queryClient.invalidateQueries({ queryKey: ['organizations'] });
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Organizations</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage your organizations and multi-repo configurations
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors"
        >
          <Plus size={16} />
          Create Organization
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-6">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="text-red-600" />
            <p className="text-sm text-red-700">
              Failed to load organizations:{' '}
              {error instanceof Error ? error.message : 'Unknown error'}
            </p>
          </div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {/* Organizations grid */}
      {!isLoading && orgs && orgs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {orgs.map((org) => (
            <OrgCard key={org.id} org={org} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && orgs && orgs.length === 0 && (
        <div className="text-center py-16">
          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
            <Building2 size={28} className="text-gray-400" />
          </div>
          <h3 className="text-base font-semibold text-gray-900 mb-2">No organizations yet</h3>
          <p className="text-sm text-gray-500 mb-6 max-w-sm mx-auto">
            Create an organization to group your repositories and collaborate with your team.
          </p>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
          >
            <Plus size={16} />
            Create your first organization
          </button>
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <CreateOrgModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
      )}
    </div>
  );
}
