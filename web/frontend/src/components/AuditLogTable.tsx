import { useState } from 'react';
import { ChevronDown, ChevronRight, Download } from 'lucide-react';
import type { AuditEntry } from '../types';

interface AuditLogTableProps {
  entries: AuditEntry[];
  onExport?: (format: string) => void;
}

const ACTION_COLORS: Record<string, string> = {
  'library.publish': 'bg-emerald-100 text-emerald-800',
  'library.delete': 'bg-red-100 text-red-800',
  'conformance.run': 'bg-indigo-100 text-indigo-800',
  'user.login': 'bg-blue-100 text-blue-800',
  'user.logout': 'bg-gray-100 text-gray-800',
  'api_key.create': 'bg-amber-100 text-amber-800',
  'api_key.delete': 'bg-red-100 text-red-800',
  'policy.create': 'bg-emerald-100 text-emerald-800',
  'policy.update': 'bg-amber-100 text-amber-800',
  'org.create': 'bg-indigo-100 text-indigo-800',
  'org.member_add': 'bg-blue-100 text-blue-800',
  'webhook.trigger': 'bg-purple-100 text-purple-800',
  'webhook.create': 'bg-emerald-100 text-emerald-800',
  'webhook.delete': 'bg-red-100 text-red-800',
  'plugin.create': 'bg-emerald-100 text-emerald-800',
  'plugin.delete': 'bg-red-100 text-red-800',
};

function getActionColor(action: string): string {
  return ACTION_COLORS[action] || 'bg-gray-100 text-gray-800';
}

function formatTimestamp(ts: string): string {
  if (!ts) return '-';
  try {
    const d = new Date(ts);
    return d.toLocaleString();
  } catch {
    return ts;
  }
}

export default function AuditLogTable({ entries, onExport }: AuditLogTableProps) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [filterAction, setFilterAction] = useState('');
  const [filterActor, setFilterActor] = useState('');
  const [dateRange, setDateRange] = useState('all');

  // Compute unique actions from entries
  const uniqueActions = Array.from(new Set(entries.map((e) => e.action))).sort();

  // Filter locally
  let filtered = entries;
  if (filterAction) {
    filtered = filtered.filter((e) => e.action === filterAction);
  }
  if (filterActor) {
    filtered = filtered.filter((e) =>
      e.actor.toLowerCase().includes(filterActor.toLowerCase())
    );
  }
  if (dateRange !== 'all') {
    const now = new Date();
    let cutoff: Date;
    switch (dateRange) {
      case 'today':
        cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        break;
      case 'week':
        cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case 'month':
        cutoff = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      default:
        cutoff = new Date(0);
    }
    filtered = filtered.filter((e) => new Date(e.timestamp) >= cutoff);
  }

  return (
    <div>
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <select
          value={filterAction}
          onChange={(e) => setFilterAction(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
        >
          <option value="">All Actions</option>
          {uniqueActions.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Filter by actor..."
          value={filterActor}
          onChange={(e) => setFilterActor(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
        />

        <select
          value={dateRange}
          onChange={(e) => setDateRange(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
        >
          <option value="all">All Time</option>
          <option value="today">Today</option>
          <option value="week">Last 7 Days</option>
          <option value="month">Last 30 Days</option>
        </select>

        <div className="flex-1" />

        {onExport && (
          <div className="flex gap-2">
            <button
              onClick={() => onExport('json')}
              className="inline-flex items-center gap-1.5 rounded-md bg-white border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <Download size={14} />
              Export JSON
            </button>
            <button
              onClick={() => onExport('csv')}
              className="inline-flex items-center gap-1.5 rounded-md bg-white border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <Download size={14} />
              Export CSV
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No audit events found.
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="w-8 px-3 py-3" />
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actor
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Resource
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Success
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filtered.map((entry) => (
                <TableRow
                  key={entry.id}
                  entry={entry}
                  expanded={expandedRow === entry.id}
                  onToggle={() =>
                    setExpandedRow(expandedRow === entry.id ? null : entry.id)
                  }
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-2 text-xs text-gray-500">
        Showing {filtered.length} of {entries.length} events
      </div>
    </div>
  );
}

function TableRow({
  entry,
  expanded,
  onToggle,
}: {
  entry: AuditEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className="hover:bg-gray-50 cursor-pointer"
        onClick={onToggle}
      >
        <td className="px-3 py-3">
          {expanded ? (
            <ChevronDown size={14} className="text-gray-400" />
          ) : (
            <ChevronRight size={14} className="text-gray-400" />
          )}
        </td>
        <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
          {formatTimestamp(entry.timestamp)}
        </td>
        <td className="px-4 py-3 text-sm font-medium text-gray-900">
          {entry.actor}
        </td>
        <td className="px-4 py-3">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getActionColor(
              entry.action
            )}`}
          >
            {entry.action}
          </span>
        </td>
        <td className="px-4 py-3 text-sm text-gray-600">
          <span className="text-gray-400">{entry.resource_type}/</span>
          {entry.resource_id}
        </td>
        <td className="px-4 py-3">
          {entry.success ? (
            <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">
              Success
            </span>
          ) : (
            <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
              Failed
            </span>
          )}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={6} className="px-8 py-4 bg-gray-50">
            <div className="text-sm">
              <h4 className="font-medium text-gray-900 mb-2">Event Details</h4>
              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <span className="text-gray-500">ID:</span>{' '}
                  <span className="font-mono text-xs">{entry.id}</span>
                </div>
                <div>
                  <span className="text-gray-500">IP Address:</span>{' '}
                  {entry.ip_address || '-'}
                </div>
                <div>
                  <span className="text-gray-500">User Agent:</span>{' '}
                  {entry.user_agent || '-'}
                </div>
              </div>
              {Object.keys(entry.details).length > 0 && (
                <div>
                  <span className="text-gray-500 block mb-1">Details:</span>
                  <pre className="bg-white rounded-md border border-gray-200 p-3 text-xs overflow-x-auto">
                    {JSON.stringify(entry.details, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
