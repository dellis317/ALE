import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Building2,
  Users,
  GitBranch,
  LayoutDashboard,
  ArrowLeft,
  Plus,
  Trash2,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  XCircle,
  Loader2,
  BookOpen,
  UserPlus,
  Shield,
} from 'lucide-react';
import {
  getOrgDashboard,
  listOrgMembers,
  addOrgMember,
  removeOrgMember,
  updateOrgMemberRole,
  listOrgRepos,
  addOrgRepo,
  removeOrgRepo,
  scanOrgRepo,
} from '../api/client';
import type { OrgMember, OrgRepo, OrgDashboard } from '../types';

type TabKey = 'dashboard' | 'members' | 'repos';

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

function ScanStatusBadge({ status }: { status: string }) {
  const config: Record<string, { icon: typeof CheckCircle2; color: string; bg: string }> = {
    complete: { icon: CheckCircle2, color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200' },
    scanning: { icon: Loader2, color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
    pending: { icon: Clock, color: 'text-gray-600', bg: 'bg-gray-50 border-gray-200' },
    error: { icon: XCircle, color: 'text-red-700', bg: 'bg-red-50 border-red-200' },
  };

  const cfg = config[status] || config.pending;
  const Icon = cfg.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border ${cfg.bg} ${cfg.color}`}
    >
      <Icon size={12} className={status === 'scanning' ? 'animate-spin' : ''} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function RoleBadge({ role }: { role: string }) {
  const config: Record<string, string> = {
    admin: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    member: 'bg-gray-50 text-gray-700 border-gray-200',
    viewer: 'bg-gray-50 text-gray-500 border-gray-200',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 text-xs font-medium rounded-full border ${config[role] || config.viewer}`}
    >
      {role.charAt(0).toUpperCase() + role.slice(1)}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Dashboard Tab
// ---------------------------------------------------------------------------

function DashboardTab({ slug }: { slug: string }) {
  const {
    data: dashboard,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['org-dashboard', slug],
    queryFn: () => getOrgDashboard(slug),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-20 mb-3" />
              <div className="h-8 bg-gray-100 rounded w-12" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} className="text-red-600" />
          <p className="text-sm text-red-700">
            Failed to load dashboard: {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      </div>
    );
  }

  if (!dashboard) return null;

  const stats = [
    {
      label: 'Libraries',
      value: dashboard.total_libraries,
      icon: BookOpen,
      color: 'text-indigo-600',
      bg: 'bg-indigo-50',
    },
    {
      label: 'Members',
      value: dashboard.total_members,
      icon: Users,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
    },
    {
      label: 'Repositories',
      value: dashboard.total_repos,
      icon: GitBranch,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.label}
              className="bg-white rounded-xl border border-gray-200 p-6"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{stat.label}</p>
                  <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>
                </div>
                <div className={`w-12 h-12 rounded-xl ${stat.bg} flex items-center justify-center`}>
                  <Icon size={22} className={stat.color} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent scans */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="text-base font-semibold text-gray-900">Recent Scan Activity</h3>
        </div>
        {dashboard.recent_scans.length === 0 ? (
          <div className="px-6 py-8 text-center">
            <p className="text-sm text-gray-500">No scan activity yet. Add repositories and trigger scans.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {dashboard.recent_scans.map((repo) => (
              <div key={repo.id} className="px-6 py-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">{repo.name}</p>
                  <p className="text-xs text-gray-500">{repo.url}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400">
                    {formatDate(repo.last_scanned)}
                  </span>
                  <ScanStatusBadge status={repo.scan_status} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Members Tab
// ---------------------------------------------------------------------------

function AddMemberModal({
  slug,
  onClose,
}: {
  slug: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState('');
  const [role, setRole] = useState('member');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: async () => {
      return addOrgMember(slug, userId, role);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-members', slug] });
      queryClient.invalidateQueries({ queryKey: ['org-dashboard', slug] });
      onClose();
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to add member');
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Member</h3>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="space-y-4 mb-6">
          <div>
            <label htmlFor="member-id" className="block text-sm font-medium text-gray-700 mb-1.5">
              User ID
            </label>
            <input
              id="member-id"
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="Enter user ID"
              className="w-full px-3 py-2.5 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              autoFocus
            />
          </div>
          <div>
            <label htmlFor="member-role" className="block text-sm font-medium text-gray-700 mb-1.5">
              Role
            </label>
            <select
              id="member-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-3 py-2.5 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="viewer">Viewer</option>
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
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
            disabled={!userId.trim() || mutation.isPending}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {mutation.isPending ? 'Adding...' : 'Add Member'}
          </button>
        </div>
      </div>
    </div>
  );
}

function MembersTab({ slug }: { slug: string }) {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);

  const {
    data: members,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['org-members', slug],
    queryFn: () => listOrgMembers(slug),
  });

  const removeMutation = useMutation({
    mutationFn: async (userId: string) => {
      return removeOrgMember(slug, userId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-members', slug] });
      queryClient.invalidateQueries({ queryKey: ['org-dashboard', slug] });
    },
  });

  const roleMutation = useMutation({
    mutationFn: async ({ userId, role }: { userId: string; role: string }) => {
      return updateOrgMemberRole(slug, userId, role);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-members', slug] });
    },
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="divide-y divide-gray-100">
          {[1, 2, 3].map((i) => (
            <div key={i} className="px-6 py-4 animate-pulse">
              <div className="flex items-center gap-4">
                <div className="w-8 h-8 rounded-full bg-gray-200" />
                <div className="flex-1">
                  <div className="h-4 bg-gray-200 rounded w-32 mb-2" />
                  <div className="h-3 bg-gray-100 rounded w-48" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} className="text-red-600" />
          <p className="text-sm text-red-700">
            Failed to load members: {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">
          {members?.length ?? 0} {(members?.length ?? 0) === 1 ? 'member' : 'members'}
        </p>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors"
        >
          <UserPlus size={14} />
          Add Member
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {/* Table header */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50/50">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Joined
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {members && members.length > 0 ? (
                members.map((member: OrgMember) => (
                  <tr
                    key={member.user_id}
                    className="border-t border-gray-100 hover:bg-gray-50/50 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {member.username || member.user_id}
                        </p>
                        {member.email && (
                          <p className="text-xs text-gray-500">{member.email}</p>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={member.role}
                        onChange={(e) =>
                          roleMutation.mutate({
                            userId: member.user_id,
                            role: e.target.value,
                          })
                        }
                        className="text-xs border border-gray-200 rounded-lg px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="viewer">Viewer</option>
                        <option value="member">Member</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {formatDate(member.joined_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => removeMutation.mutate(member.user_id)}
                        disabled={removeMutation.isPending}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                        title="Remove member"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-500">
                    No members found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showAdd && <AddMemberModal slug={slug} onClose={() => setShowAdd(false)} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Repositories Tab
// ---------------------------------------------------------------------------

function AddRepoModal({
  slug,
  onClose,
}: {
  slug: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: async () => {
      return addOrgRepo(slug, name, url, branch);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-repos', slug] });
      queryClient.invalidateQueries({ queryKey: ['org-dashboard', slug] });
      onClose();
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to add repository');
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Repository</h3>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="space-y-4 mb-6">
          <div>
            <label htmlFor="repo-name" className="block text-sm font-medium text-gray-700 mb-1.5">
              Repository Name
            </label>
            <input
              id="repo-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., my-awesome-project"
              className="w-full px-3 py-2.5 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              autoFocus
            />
          </div>
          <div>
            <label htmlFor="repo-url" className="block text-sm font-medium text-gray-700 mb-1.5">
              Repository URL
            </label>
            <input
              id="repo-url"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/org/repo"
              className="w-full px-3 py-2.5 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
          </div>
          <div>
            <label htmlFor="repo-branch" className="block text-sm font-medium text-gray-700 mb-1.5">
              Default Branch
            </label>
            <input
              id="repo-branch"
              type="text"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              placeholder="main"
              className="w-full px-3 py-2.5 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
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
            disabled={!name.trim() || !url.trim() || mutation.isPending}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {mutation.isPending ? 'Adding...' : 'Add Repository'}
          </button>
        </div>
      </div>
    </div>
  );
}

function ReposTab({ slug }: { slug: string }) {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);

  const {
    data: repos,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['org-repos', slug],
    queryFn: () => listOrgRepos(slug),
  });

  const removeMutation = useMutation({
    mutationFn: async (repoId: string) => {
      return removeOrgRepo(slug, repoId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-repos', slug] });
      queryClient.invalidateQueries({ queryKey: ['org-dashboard', slug] });
    },
  });

  const scanMutation = useMutation({
    mutationFn: async (repoId: string) => {
      return scanOrgRepo(slug, repoId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-repos', slug] });
      queryClient.invalidateQueries({ queryKey: ['org-dashboard', slug] });
    },
  });

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="divide-y divide-gray-100">
          {[1, 2, 3].map((i) => (
            <div key={i} className="px-6 py-4 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-40 mb-2" />
              <div className="h-3 bg-gray-100 rounded w-64" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} className="text-red-600" />
          <p className="text-sm text-red-700">
            Failed to load repositories:{' '}
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">
          {repos?.length ?? 0} {(repos?.length ?? 0) === 1 ? 'repository' : 'repositories'}
        </p>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors"
        >
          <Plus size={14} />
          Add Repository
        </button>
      </div>

      {/* Empty state */}
      {repos && repos.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-200 py-12 text-center">
          <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
            <GitBranch size={20} className="text-gray-400" />
          </div>
          <h3 className="text-sm font-semibold text-gray-900 mb-1">No repositories</h3>
          <p className="text-sm text-gray-500 mb-4">
            Add a repository to start tracking and scanning.
          </p>
          <button
            onClick={() => setShowAdd(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
          >
            <Plus size={16} />
            Add your first repository
          </button>
        </div>
      )}

      {/* Repos list */}
      {repos && repos.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="divide-y divide-gray-100">
            {repos.map((repo: OrgRepo) => (
              <div
                key={repo.id}
                className="px-6 py-4 flex items-center justify-between hover:bg-gray-50/50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <GitBranch size={16} className="text-gray-400 flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{repo.name}</p>
                      <p className="text-xs text-gray-500 truncate">{repo.url}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 mt-2 ml-7">
                    <span className="text-xs text-gray-400">
                      Branch: <span className="font-mono">{repo.default_branch}</span>
                    </span>
                    {repo.last_scanned && (
                      <span className="text-xs text-gray-400">
                        Last scanned: {formatDate(repo.last_scanned)}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  <ScanStatusBadge status={repo.scan_status} />
                  <button
                    onClick={() => scanMutation.mutate(repo.id)}
                    disabled={scanMutation.isPending}
                    className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors"
                    title="Trigger scan"
                  >
                    <RefreshCw
                      size={14}
                      className={scanMutation.isPending ? 'animate-spin' : ''}
                    />
                  </button>
                  <button
                    onClick={() => removeMutation.mutate(repo.id)}
                    disabled={removeMutation.isPending}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                    title="Remove repository"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {showAdd && <AddRepoModal slug={slug} onClose={() => setShowAdd(false)} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main OrgDetail Page
// ---------------------------------------------------------------------------

export default function OrgDetail() {
  const { slug } = useParams<{ slug: string }>();
  const [activeTab, setActiveTab] = useState<TabKey>('dashboard');

  const {
    data: dashboard,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['org-dashboard', slug],
    queryFn: () => getOrgDashboard(slug!),
    enabled: !!slug,
  });

  const tabs: { key: TabKey; label: string; icon: typeof LayoutDashboard }[] = [
    { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { key: 'members', label: 'Members', icon: Users },
    { key: 'repos', label: 'Repositories', icon: GitBranch },
  ];

  if (!slug) {
    return (
      <div className="text-center py-16">
        <p className="text-sm text-gray-500">Organization not found.</p>
      </div>
    );
  }

  return (
    <div>
      {/* Back link + header */}
      <div className="mb-6">
        <Link
          to="/orgs"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-indigo-600 transition-colors mb-4"
        >
          <ArrowLeft size={14} />
          Back to Organizations
        </Link>

        {isLoading && (
          <div className="animate-pulse">
            <div className="h-7 bg-gray-200 rounded w-48 mb-2" />
            <div className="h-4 bg-gray-100 rounded w-64" />
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
            <div className="flex items-center gap-2">
              <AlertTriangle size={16} className="text-red-600" />
              <p className="text-sm text-red-700">
                Failed to load organization:{' '}
                {error instanceof Error ? error.message : 'Unknown error'}
              </p>
            </div>
          </div>
        )}

        {dashboard && (
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center">
              <Building2 size={24} className="text-indigo-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{dashboard.org.name}</h1>
              {dashboard.org.description && (
                <p className="text-sm text-gray-500 mt-0.5">{dashboard.org.description}</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-6">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 pb-3 text-sm font-medium border-b-2 transition-colors ${
                  isActive
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'dashboard' && <DashboardTab slug={slug} />}
      {activeTab === 'members' && <MembersTab slug={slug} />}
      {activeTab === 'repos' && <ReposTab slug={slug} />}
    </div>
  );
}
