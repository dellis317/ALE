import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ClipboardCheck,
  Clock,
  CheckCircle2,
  XCircle,
  MessageSquare,
  Loader2,
  Package,
  User,
  Shield,
  Calendar,
} from 'lucide-react';
import {
  listApprovals,
  approveRequest,
  rejectRequest,
  getPendingCount,
} from '../api/client';
import type { ApprovalRequest } from '../types';

type StatusTab = 'pending' | 'approved' | 'rejected';

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

function statusIcon(status: string) {
  switch (status) {
    case 'approved':
      return <CheckCircle2 size={16} className="text-emerald-600" />;
    case 'rejected':
      return <XCircle size={16} className="text-red-600" />;
    default:
      return <Clock size={16} className="text-amber-600" />;
  }
}

function statusBadge(status: string) {
  const styles: Record<string, string> = {
    pending: 'bg-amber-100 text-amber-700',
    approved: 'bg-emerald-100 text-emerald-700',
    rejected: 'bg-red-100 text-red-700',
  };
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${
        styles[status] || styles.pending
      }`}
    >
      {statusIcon(status)}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Approval Card
// ---------------------------------------------------------------------------

function ApprovalCard({
  request,
  onApprove,
  onReject,
  acting,
}: {
  request: ApprovalRequest;
  onApprove: (id: string, comment: string) => void;
  onReject: (id: string, comment: string) => void;
  acting: boolean;
}) {
  const [comment, setComment] = useState('');
  const [showActions, setShowActions] = useState(false);
  const isPending = request.status === 'pending';

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:border-gray-300 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center">
            <Package size={20} className="text-indigo-600" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              {request.library_name}
              <span className="text-gray-400 font-normal ml-1.5">v{request.library_version}</span>
            </h3>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                <User size={12} />
                {request.requester_id}
              </span>
              <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                <Shield size={12} />
                {request.policy_id.slice(0, 8)}...
              </span>
            </div>
          </div>
        </div>
        {statusBadge(request.status)}
      </div>

      {/* Reason */}
      {request.reason && (
        <div className="bg-gray-50 rounded-lg px-4 py-3 mb-3">
          <p className="text-sm text-gray-700">{request.reason}</p>
        </div>
      )}

      {/* Date info */}
      <div className="flex items-center gap-4 text-xs text-gray-400 mb-3">
        <span className="inline-flex items-center gap-1">
          <Calendar size={12} />
          Requested {formatDate(request.created_at)}
        </span>
        {request.decided_at && (
          <span className="inline-flex items-center gap-1">
            <Calendar size={12} />
            Decided {formatDate(request.decided_at)}
          </span>
        )}
      </div>

      {/* Decision info (for decided requests) */}
      {!isPending && request.decided_by && (
        <div
          className={`rounded-lg px-4 py-3 mb-3 ${
            request.status === 'approved'
              ? 'bg-emerald-50 border border-emerald-200'
              : 'bg-red-50 border border-red-200'
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            {statusIcon(request.status)}
            <span className="text-xs font-medium text-gray-900">
              {request.status === 'approved' ? 'Approved' : 'Rejected'} by {request.decided_by}
            </span>
          </div>
          {request.decision_comment && (
            <p className="text-xs text-gray-600 mt-1">{request.decision_comment}</p>
          )}
        </div>
      )}

      {/* Actions for pending requests */}
      {isPending && (
        <div>
          {showActions ? (
            <div className="border-t border-gray-100 pt-3">
              <div className="mb-3">
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  <MessageSquare size={12} className="inline mr-1" />
                  Comment (optional)
                </label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Add a comment for your decision..."
                  rows={2}
                  className="w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                />
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onApprove(request.id, comment)}
                  disabled={acting}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {acting ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <CheckCircle2 size={14} />
                  )}
                  Approve
                </button>
                <button
                  onClick={() => onReject(request.id, comment)}
                  disabled={acting}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {acting ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <XCircle size={14} />
                  )}
                  Reject
                </button>
                <button
                  onClick={() => {
                    setShowActions(false);
                    setComment('');
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 border-t border-gray-100 pt-3">
              <button
                onClick={() => setShowActions(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 rounded-lg hover:bg-emerald-100 transition-colors"
              >
                <CheckCircle2 size={14} />
                Approve
              </button>
              <button
                onClick={() => setShowActions(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-700 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
              >
                <XCircle size={14} />
                Reject
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function ApprovalCardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gray-200" />
          <div>
            <div className="h-4 bg-gray-200 rounded w-40 mb-1" />
            <div className="h-3 bg-gray-100 rounded w-24" />
          </div>
        </div>
        <div className="h-5 bg-gray-100 rounded-full w-20" />
      </div>
      <div className="h-12 bg-gray-50 rounded-lg mb-3" />
      <div className="h-3 bg-gray-100 rounded w-32" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Approvals page
// ---------------------------------------------------------------------------

export default function Approvals() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<StatusTab>('pending');

  // Fetch approvals for current tab
  const {
    data: approvals,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['approvals', activeTab],
    queryFn: () => listApprovals(activeTab),
  });

  // Fetch pending count for badge
  const { data: pendingCount } = useQuery({
    queryKey: ['approvals-pending-count'],
    queryFn: getPendingCount,
  });

  const approveMutation = useMutation({
    mutationFn: async ({ id, comment }: { id: string; comment: string }) =>
      approveRequest(id, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['approvals-pending-count'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async ({ id, comment }: { id: string; comment: string }) =>
      rejectRequest(id, comment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['approvals-pending-count'] });
    },
  });

  const tabs: { key: StatusTab; label: string; icon: typeof Clock }[] = [
    { key: 'pending', label: 'Pending', icon: Clock },
    { key: 'approved', label: 'Approved', icon: CheckCircle2 },
    { key: 'rejected', label: 'Rejected', icon: XCircle },
  ];

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Approvals</h1>
        <p className="text-sm text-gray-500 mt-1">
          Review and manage library application approval requests
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === key
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Icon size={16} />
            {label}
            {key === 'pending' && pendingCount !== undefined && pendingCount > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-xs font-semibold bg-amber-500 text-white rounded-full min-w-[20px] text-center">
                {pendingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-6">
          <p className="text-sm text-red-700">
            Failed to load approvals: {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="grid gap-4 max-w-3xl">
          <ApprovalCardSkeleton />
          <ApprovalCardSkeleton />
          <ApprovalCardSkeleton />
        </div>
      )}

      {/* Approval cards */}
      {!isLoading && !error && approvals && approvals.length > 0 && (
        <div className="grid gap-4 max-w-3xl">
          {approvals.map((req) => (
            <ApprovalCard
              key={req.id}
              request={req}
              onApprove={(id, comment) => approveMutation.mutate({ id, comment })}
              onReject={(id, comment) => rejectMutation.mutate({ id, comment })}
              acting={approveMutation.isPending || rejectMutation.isPending}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && approvals && approvals.length === 0 && (
        <div className="text-center py-16 max-w-3xl">
          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
            <ClipboardCheck size={28} className="text-gray-400" />
          </div>
          <h3 className="text-sm font-semibold text-gray-900 mb-1">
            No {activeTab} approvals
          </h3>
          <p className="text-sm text-gray-500">
            {activeTab === 'pending'
              ? 'There are no pending approval requests at this time.'
              : activeTab === 'approved'
                ? 'No approval requests have been approved yet.'
                : 'No approval requests have been rejected yet.'}
          </p>
        </div>
      )}
    </div>
  );
}
