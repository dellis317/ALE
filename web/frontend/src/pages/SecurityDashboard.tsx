import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Shield,
  Webhook,
  Puzzle,
  AlertTriangle,
  Activity,
  Plus,
  Trash2,
  Send,
  ToggleLeft,
  ToggleRight,
  Loader2,
  X,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import {
  getSecurityDashboard,
  getAuditEvents,
  exportAuditLog,
  listWebhooks,
  createWebhook,
  deleteWebhook,
  toggleWebhook,
  testWebhook,
  getWebhookDeliveries,
  listPlugins,
  createPlugin,
  deletePlugin,
  togglePlugin,
} from '../api/client';
import type { Webhook as WebhookType, WebhookDelivery, Plugin } from '../types';
import AuditLogTable from '../components/AuditLogTable';
import WebhookForm from '../components/WebhookForm';

type TabId = 'audit' | 'webhooks' | 'plugins';

export default function SecurityDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>('audit');
  const queryClient = useQueryClient();

  // Dashboard stats
  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ['security-dashboard'],
    queryFn: getSecurityDashboard,
  });

  if (dashLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="animate-spin text-indigo-600" size={32} />
      </div>
    );
  }

  const stats = dashboard || {
    total_events: 0,
    events_today: 0,
    active_webhooks: 0,
    total_webhooks: 0,
    enabled_plugins: 0,
    total_plugins: 0,
    recent_events: [],
    failed_deliveries_24h: 0,
  };

  const tabs: { id: TabId; label: string }[] = [
    { id: 'audit', label: 'Audit Log' },
    { id: 'webhooks', label: 'Webhooks' },
    { id: 'plugins', label: 'Plugins' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Security</h1>
        <p className="text-sm text-gray-500 mt-1">
          Audit logs, webhooks, and extensibility plugins
        </p>
      </div>

      {/* Overview cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          icon={<Activity size={20} className="text-indigo-600" />}
          label="Audit Events"
          value={stats.total_events}
          sub={`${stats.events_today} today`}
        />
        <StatCard
          icon={<Webhook size={20} className="text-emerald-600" />}
          label="Webhooks"
          value={stats.active_webhooks}
          sub={`${stats.total_webhooks} total`}
        />
        <StatCard
          icon={<Puzzle size={20} className="text-blue-600" />}
          label="Plugins"
          value={stats.enabled_plugins}
          sub={`${stats.total_plugins} total`}
        />
        <StatCard
          icon={<AlertTriangle size={20} className="text-red-600" />}
          label="Failed Deliveries (24h)"
          value={stats.failed_deliveries_24h}
          sub="webhook errors"
          alert={stats.failed_deliveries_24h > 0}
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'audit' && <AuditTab />}
      {activeTab === 'webhooks' && <WebhooksTab />}
      {activeTab === 'plugins' && <PluginsTab />}
    </div>
  );
}

// =========================================================================
// Stat Card
// =========================================================================

function StatCard({
  icon,
  label,
  value,
  sub,
  alert = false,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  sub: string;
  alert?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border p-5 ${
        alert ? 'border-red-200 bg-red-50' : 'border-gray-200 bg-white'
      }`}
    >
      <div className="flex items-center gap-3 mb-2">
        {icon}
        <span className="text-sm font-medium text-gray-500">{label}</span>
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-500 mt-1">{sub}</div>
    </div>
  );
}

// =========================================================================
// Audit Tab
// =========================================================================

function AuditTab() {
  const { data: events = [], isLoading } = useQuery({
    queryKey: ['audit-events'],
    queryFn: () => getAuditEvents({ limit: 500 }),
  });

  const handleExport = async (format: string) => {
    try {
      const result = await exportAuditLog(format);
      const blob = new Blob([result.content], {
        type: format === 'json' ? 'application/json' : 'text/csv',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_log.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // export failed silently
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="animate-spin text-indigo-600" size={24} />
      </div>
    );
  }

  return <AuditLogTable entries={events} onExport={handleExport} />;
}

// =========================================================================
// Webhooks Tab
// =========================================================================

function WebhooksTab() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const { data: webhooks = [], isLoading } = useQuery({
    queryKey: ['webhooks'],
    queryFn: listWebhooks,
  });

  const createMut = useMutation({
    mutationFn: (data: { name: string; url: string; events: string[]; secret: string }) =>
      createWebhook(data.name, data.url, data.events, data.secret),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
      queryClient.invalidateQueries({ queryKey: ['security-dashboard'] });
      setShowForm(false);
    },
  });

  const deleteMut = useMutation({
    mutationFn: deleteWebhook,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
      queryClient.invalidateQueries({ queryKey: ['security-dashboard'] });
      setDeleteConfirm(null);
    },
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      toggleWebhook(id, active),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
      queryClient.invalidateQueries({ queryKey: ['security-dashboard'] });
    },
  });

  const testMut = useMutation({
    mutationFn: testWebhook,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhook-deliveries'] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="animate-spin text-indigo-600" size={24} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {webhooks.length} webhook{webhooks.length !== 1 ? 's' : ''} registered
        </p>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus size={16} />
            Add Webhook
          </button>
        )}
      </div>

      {/* Create form */}
      {showForm && (
        <WebhookForm
          onSave={(data) => createMut.mutate(data)}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* Webhook list */}
      {webhooks.length === 0 && !showForm ? (
        <div className="text-center py-12 text-gray-500">
          <Webhook className="mx-auto mb-3 text-gray-300" size={40} />
          <p>No webhooks registered yet.</p>
          <p className="text-xs mt-1">Click "Add Webhook" to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {webhooks.map((wh) => (
            <WebhookCard
              key={wh.id}
              webhook={wh}
              expanded={expandedId === wh.id}
              onToggleExpand={() =>
                setExpandedId(expandedId === wh.id ? null : wh.id)
              }
              onToggleActive={() =>
                toggleMut.mutate({ id: wh.id, active: !wh.active })
              }
              onTest={() => testMut.mutate(wh.id)}
              testLoading={testMut.isPending}
              onDeleteClick={() => setDeleteConfirm(wh.id)}
              deleteConfirm={deleteConfirm === wh.id}
              onDeleteConfirm={() => deleteMut.mutate(wh.id)}
              onDeleteCancel={() => setDeleteConfirm(null)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function WebhookCard({
  webhook,
  expanded,
  onToggleExpand,
  onToggleActive,
  onTest,
  testLoading,
  onDeleteClick,
  deleteConfirm,
  onDeleteConfirm,
  onDeleteCancel,
}: {
  webhook: WebhookType;
  expanded: boolean;
  onToggleExpand: () => void;
  onToggleActive: () => void;
  onTest: () => void;
  testLoading: boolean;
  onDeleteClick: () => void;
  deleteConfirm: boolean;
  onDeleteConfirm: () => void;
  onDeleteCancel: () => void;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
      <div className="flex items-center gap-4 px-5 py-4">
        <button onClick={onToggleExpand} className="text-gray-400">
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900">{webhook.name}</span>
            {!webhook.active && (
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                Disabled
              </span>
            )}
          </div>
          <div className="text-xs text-gray-500 truncate mt-0.5">
            {webhook.url}
          </div>
        </div>

        {/* Event badges */}
        <div className="hidden md:flex flex-wrap gap-1">
          {webhook.events.slice(0, 3).map((ev) => (
            <span
              key={ev}
              className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700"
            >
              {ev}
            </span>
          ))}
          {webhook.events.length > 3 && (
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
              +{webhook.events.length - 3}
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={onToggleActive}
            title={webhook.active ? 'Disable' : 'Enable'}
            className="text-gray-400 hover:text-indigo-600"
          >
            {webhook.active ? (
              <ToggleRight size={22} className="text-emerald-500" />
            ) : (
              <ToggleLeft size={22} />
            )}
          </button>
          <button
            onClick={onTest}
            disabled={testLoading}
            title="Send test event"
            className="text-gray-400 hover:text-indigo-600 disabled:opacity-50"
          >
            {testLoading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
          </button>
          {deleteConfirm ? (
            <div className="flex items-center gap-1">
              <button
                onClick={onDeleteConfirm}
                className="text-xs text-red-600 hover:text-red-800 font-medium"
              >
                Confirm
              </button>
              <button
                onClick={onDeleteCancel}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <button
              onClick={onDeleteClick}
              title="Delete"
              className="text-gray-400 hover:text-red-600"
            >
              <Trash2 size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Expanded: delivery history */}
      {expanded && <WebhookDeliveryHistory webhookId={webhook.id} />}
    </div>
  );
}

function WebhookDeliveryHistory({ webhookId }: { webhookId: string }) {
  const { data: deliveries = [], isLoading } = useQuery({
    queryKey: ['webhook-deliveries', webhookId],
    queryFn: () => getWebhookDeliveries(webhookId),
  });

  if (isLoading) {
    return (
      <div className="px-5 py-4 border-t border-gray-100">
        <Loader2 className="animate-spin text-indigo-600 mx-auto" size={18} />
      </div>
    );
  }

  if (deliveries.length === 0) {
    return (
      <div className="px-5 py-4 border-t border-gray-100 text-sm text-gray-500">
        No deliveries yet.
      </div>
    );
  }

  return (
    <div className="border-t border-gray-100">
      <div className="px-5 py-3 bg-gray-50">
        <h4 className="text-xs font-medium text-gray-500 uppercase">
          Recent Deliveries
        </h4>
      </div>
      <div className="divide-y divide-gray-100">
        {deliveries.slice(0, 10).map((d) => (
          <DeliveryRow key={d.id} delivery={d} />
        ))}
      </div>
    </div>
  );
}

function DeliveryRow({ delivery }: { delivery: WebhookDelivery }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <div
        className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50 cursor-pointer text-sm"
        onClick={() => setExpanded(!expanded)}
      >
        {delivery.success ? (
          <CheckCircle2 size={16} className="text-emerald-500 flex-shrink-0" />
        ) : (
          <XCircle size={16} className="text-red-500 flex-shrink-0" />
        )}
        <span className="text-gray-700 font-medium">{delivery.event}</span>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            delivery.success
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-red-100 text-red-700'
          }`}
        >
          {delivery.response_status || 'Error'}
        </span>
        <span className="text-gray-400 text-xs">{delivery.duration_ms}ms</span>
        <span className="flex-1" />
        <span className="text-xs text-gray-400">
          {delivery.delivered_at
            ? new Date(delivery.delivered_at).toLocaleString()
            : '-'}
        </span>
      </div>
      {expanded && (
        <div className="px-8 py-3 bg-gray-50 text-xs">
          <div className="mb-2">
            <span className="font-medium text-gray-500">Response Body:</span>
            <pre className="mt-1 bg-white border border-gray-200 rounded p-2 overflow-x-auto whitespace-pre-wrap">
              {delivery.response_body || '(empty)'}
            </pre>
          </div>
          {Object.keys(delivery.payload).length > 0 && (
            <div>
              <span className="font-medium text-gray-500">Payload:</span>
              <pre className="mt-1 bg-white border border-gray-200 rounded p-2 overflow-x-auto">
                {JSON.stringify(delivery.payload, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </>
  );
}

// =========================================================================
// Plugins Tab
// =========================================================================

const PLUGIN_HOOKS = [
  'pre_publish',
  'post_publish',
  'pre_conformance',
  'post_conformance',
  'pre_apply',
  'post_apply',
];

function PluginsTab() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // Form state
  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formHooks, setFormHooks] = useState<string[]>([]);

  const { data: plugins = [], isLoading } = useQuery({
    queryKey: ['plugins'],
    queryFn: listPlugins,
  });

  const createMut = useMutation({
    mutationFn: () => createPlugin(formName, formDescription, formHooks),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugins'] });
      queryClient.invalidateQueries({ queryKey: ['security-dashboard'] });
      setShowForm(false);
      setFormName('');
      setFormDescription('');
      setFormHooks([]);
    },
  });

  const deleteMut = useMutation({
    mutationFn: deletePlugin,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugins'] });
      queryClient.invalidateQueries({ queryKey: ['security-dashboard'] });
      setDeleteConfirm(null);
    },
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      togglePlugin(id, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plugins'] });
      queryClient.invalidateQueries({ queryKey: ['security-dashboard'] });
    },
  });

  const toggleHook = (hook: string) => {
    setFormHooks((prev) =>
      prev.includes(hook) ? prev.filter((h) => h !== hook) : [...prev, hook]
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="animate-spin text-indigo-600" size={24} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {plugins.length} plugin{plugins.length !== 1 ? 's' : ''} registered
        </p>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus size={16} />
            Register Plugin
          </button>
        )}
      </div>

      {/* Create form */}
      {showForm && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">
              Register Plugin
            </h3>
            <button
              onClick={() => setShowForm(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X size={20} />
            </button>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (formName.trim()) createMut.mutate();
            }}
            className="space-y-5"
          >
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Name
              </label>
              <input
                type="text"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="My Plugin"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder="What does this plugin do?"
                rows={2}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Hooks
              </label>
              <div className="grid grid-cols-2 gap-2">
                {PLUGIN_HOOKS.map((hook) => (
                  <label
                    key={hook}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={formHooks.includes(hook)}
                      onChange={() => toggleHook(hook)}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-sm text-gray-700">{hook}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!formName.trim() || createMut.isPending}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {createMut.isPending ? 'Creating...' : 'Register Plugin'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Plugin list */}
      {plugins.length === 0 && !showForm ? (
        <div className="text-center py-12 text-gray-500">
          <Puzzle className="mx-auto mb-3 text-gray-300" size={40} />
          <p>No plugins registered yet.</p>
          <p className="text-xs mt-1">
            Click "Register Plugin" to get started.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {plugins.map((plugin) => (
            <PluginCard
              key={plugin.id}
              plugin={plugin}
              onToggle={() =>
                toggleMut.mutate({ id: plugin.id, enabled: !plugin.enabled })
              }
              onDeleteClick={() => setDeleteConfirm(plugin.id)}
              deleteConfirm={deleteConfirm === plugin.id}
              onDeleteConfirm={() => deleteMut.mutate(plugin.id)}
              onDeleteCancel={() => setDeleteConfirm(null)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function PluginCard({
  plugin,
  onToggle,
  onDeleteClick,
  deleteConfirm,
  onDeleteConfirm,
  onDeleteCancel,
}: {
  plugin: Plugin;
  onToggle: () => void;
  onDeleteClick: () => void;
  deleteConfirm: boolean;
  onDeleteConfirm: () => void;
  onDeleteCancel: () => void;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-4">
      <div className="flex items-center gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900">{plugin.name}</span>
            {!plugin.enabled && (
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                Disabled
              </span>
            )}
          </div>
          {plugin.description && (
            <p className="text-sm text-gray-500 mt-0.5">
              {plugin.description}
            </p>
          )}
          {plugin.hooks.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {plugin.hooks.map((hook) => (
                <span
                  key={hook}
                  className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700"
                >
                  {hook}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={onToggle}
            title={plugin.enabled ? 'Disable' : 'Enable'}
            className="text-gray-400 hover:text-indigo-600"
          >
            {plugin.enabled ? (
              <ToggleRight size={22} className="text-emerald-500" />
            ) : (
              <ToggleLeft size={22} />
            )}
          </button>
          {deleteConfirm ? (
            <div className="flex items-center gap-1">
              <button
                onClick={onDeleteConfirm}
                className="text-xs text-red-600 hover:text-red-800 font-medium"
              >
                Confirm
              </button>
              <button
                onClick={onDeleteCancel}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <button
              onClick={onDeleteClick}
              title="Delete"
              className="text-gray-400 hover:text-red-600"
            >
              <Trash2 size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
