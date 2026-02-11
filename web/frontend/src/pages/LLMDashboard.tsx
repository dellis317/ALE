import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sparkles,
  DollarSign,
  Hash,
  Activity,
  AlertTriangle,
  CheckCircle,
  Send,
  Eye,
  Shield,
  Loader2,
} from 'lucide-react';
import {
  getLLMStatus,
  getLLMUsage,
  getLLMBudget,
  getLLMBudgetStatus,
  setLLMBudget,
  generatePreview,
  suggestGuardrails,
} from '../api/client';
import type { UsageSummary, Budget, BudgetStatus, LLMStatus } from '../types';
import UsageChart from '../components/UsageChart';
import BudgetGauge from '../components/BudgetGauge';

type Period = 'today' | 'week' | 'month' | 'all';

const PERIOD_LABELS: Record<Period, string> = {
  today: 'Today',
  week: 'This Week',
  month: 'This Month',
  all: 'All Time',
};

const PURPOSE_COLORS: Record<string, string> = {
  preview: 'bg-indigo-100 text-indigo-700',
  enrich: 'bg-emerald-100 text-emerald-700',
  'suggest-guardrails': 'bg-amber-100 text-amber-700',
  describe: 'bg-purple-100 text-purple-700',
  test: 'bg-gray-100 text-gray-700',
};

function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`;
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}k`;
  return tokens.toString();
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export default function LLMDashboard() {
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState<Period>('month');
  const [budgetLimit, setBudgetLimit] = useState('');
  const [budgetThreshold, setBudgetThreshold] = useState(80);
  const [previewYaml, setPreviewYaml] = useState('');
  const [guardrailYaml, setGuardrailYaml] = useState('');
  const [previewResult, setPreviewResult] = useState('');
  const [guardrailResult, setGuardrailResult] = useState('');

  // Queries
  const statusQuery = useQuery<LLMStatus>({
    queryKey: ['llm-status'],
    queryFn: getLLMStatus,
  });

  const usageQuery = useQuery<UsageSummary>({
    queryKey: ['llm-usage', period],
    queryFn: () => getLLMUsage(period),
  });

  const budgetQuery = useQuery<Budget>({
    queryKey: ['llm-budget'],
    queryFn: getLLMBudget,
  });

  const budgetStatusQuery = useQuery<BudgetStatus>({
    queryKey: ['llm-budget-status'],
    queryFn: getLLMBudgetStatus,
  });

  // Mutations
  const setBudgetMutation = useMutation({
    mutationFn: () => setLLMBudget(parseFloat(budgetLimit) || 0, budgetThreshold),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llm-budget'] });
      queryClient.invalidateQueries({ queryKey: ['llm-budget-status'] });
    },
  });

  const previewMutation = useMutation({
    mutationFn: (yaml: string) => generatePreview(yaml),
    onSuccess: (data) => {
      setPreviewResult(data.preview);
      queryClient.invalidateQueries({ queryKey: ['llm-usage'] });
    },
  });

  const guardrailMutation = useMutation({
    mutationFn: (yaml: string) => suggestGuardrails(yaml),
    onSuccess: (data) => {
      setGuardrailResult(JSON.stringify(data.guardrails, null, 2));
      queryClient.invalidateQueries({ queryKey: ['llm-usage'] });
    },
  });

  const status = statusQuery.data;
  const usage = usageQuery.data;
  const budget = budgetQuery.data;
  const budgetStatus = budgetStatusQuery.data;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center gap-3">
        <Sparkles className="text-indigo-600" size={28} />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">LLM Dashboard</h1>
          <p className="text-sm text-gray-500">Monitor usage, manage budgets, and run LLM actions</p>
        </div>
      </div>

      {/* Status banner */}
      {statusQuery.isLoading ? (
        <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 flex items-center gap-2">
          <Loader2 size={16} className="animate-spin text-gray-400" />
          <span className="text-sm text-gray-500">Checking LLM status...</span>
        </div>
      ) : status?.configured ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 flex items-center gap-2">
          <CheckCircle size={16} className="text-emerald-600" />
          <span className="text-sm text-emerald-800">
            LLM configured and ready &mdash; Model: <strong>{status.model}</strong>
          </span>
        </div>
      ) : (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 flex items-center gap-2">
          <AlertTriangle size={16} className="text-amber-600" />
          <span className="text-sm text-amber-800">
            LLM not configured. Set the <code className="bg-amber-100 px-1 rounded text-xs">ANTHROPIC_API_KEY</code> environment variable to enable LLM features.
          </span>
        </div>
      )}

      {/* Period selector */}
      <div className="flex items-center gap-2">
        {(Object.keys(PERIOD_LABELS) as Period[]).map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              period === p
                ? 'bg-indigo-600 text-white'
                : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
            }`}
          >
            {PERIOD_LABELS[p]}
          </button>
        ))}
      </div>

      {/* Stats cards row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Total Tokens */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-2">
            <Hash size={16} className="text-indigo-500" />
            <span className="text-sm font-medium text-gray-500">Total Tokens</span>
          </div>
          {usageQuery.isLoading ? (
            <div className="h-8 bg-gray-100 rounded animate-pulse" />
          ) : (
            <>
              <p className="text-2xl font-bold text-gray-900">
                {formatTokens((usage?.total_input_tokens ?? 0) + (usage?.total_output_tokens ?? 0))}
              </p>
              <div className="flex gap-3 mt-1 text-xs text-gray-500">
                <span>In: {formatTokens(usage?.total_input_tokens ?? 0)}</span>
                <span>Out: {formatTokens(usage?.total_output_tokens ?? 0)}</span>
              </div>
            </>
          )}
        </div>

        {/* Total Cost */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign size={16} className="text-emerald-500" />
            <span className="text-sm font-medium text-gray-500">Total Cost</span>
          </div>
          {usageQuery.isLoading ? (
            <div className="h-8 bg-gray-100 rounded animate-pulse" />
          ) : (
            <p className="text-2xl font-bold text-gray-900">
              {formatCost(usage?.total_cost ?? 0)}
            </p>
          )}
        </div>

        {/* Requests */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-2">
            <Activity size={16} className="text-amber-500" />
            <span className="text-sm font-medium text-gray-500">Requests</span>
          </div>
          {usageQuery.isLoading ? (
            <div className="h-8 bg-gray-100 rounded animate-pulse" />
          ) : (
            <p className="text-2xl font-bold text-gray-900">{usage?.record_count ?? 0}</p>
          )}
        </div>
      </div>

      {/* Main content: Budget + Chart side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Budget controls (left column) */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
          <h3 className="text-sm font-semibold text-gray-700">Budget Controls</h3>

          {/* Budget gauge */}
          <div className="relative flex justify-center">
            {budgetQuery.isLoading ? (
              <div className="h-[160px] w-[160px] bg-gray-100 rounded-full animate-pulse" />
            ) : budget && budget.monthly_limit > 0 ? (
              <BudgetGauge
                percentUsed={budgetStatus?.percent_used ?? 0}
                currentCost={budget.current_month_cost}
                monthlyLimit={budget.monthly_limit}
              />
            ) : (
              <div className="flex items-center justify-center h-[160px] text-gray-400 text-sm text-center">
                No budget set.<br />Configure below.
              </div>
            )}
          </div>

          {/* Budget status indicator */}
          {budgetStatus?.over_limit && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700 flex items-center gap-1">
              <AlertTriangle size={14} />
              Budget exceeded! LLM calls are blocked.
            </div>
          )}

          {/* Set budget form */}
          <div className="space-y-3 border-t border-gray-100 pt-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Monthly Limit ($)
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={budgetLimit}
                onChange={(e) => setBudgetLimit(e.target.value)}
                placeholder={budget?.monthly_limit?.toString() || '10.00'}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Alert Threshold: {budgetThreshold}%
              </label>
              <input
                type="range"
                min="10"
                max="100"
                value={budgetThreshold}
                onChange={(e) => setBudgetThreshold(parseInt(e.target.value))}
                className="w-full accent-indigo-600"
              />
            </div>
            <button
              onClick={() => setBudgetMutation.mutate()}
              disabled={setBudgetMutation.isPending || !budgetLimit}
              className="w-full rounded-lg bg-indigo-600 text-white text-sm font-medium py-2 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {setBudgetMutation.isPending ? 'Saving...' : 'Save Budget'}
            </button>
          </div>
        </div>

        {/* Usage chart (right 2 columns) */}
        <div className="lg:col-span-2">
          <UsageChart records={usage?.records ?? []} />
        </div>
      </div>

      {/* Usage history table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700">Usage History</h3>
        </div>
        {usageQuery.isLoading ? (
          <div className="p-8 text-center">
            <Loader2 size={20} className="animate-spin text-gray-400 mx-auto" />
            <p className="text-sm text-gray-400 mt-2">Loading usage history...</p>
          </div>
        ) : !usage?.records.length ? (
          <div className="p-8 text-center text-gray-400 text-sm">
            No usage records for this period.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50">
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3">Purpose</th>
                  <th className="px-5 py-3">Model</th>
                  <th className="px-5 py-3 text-right">Input Tokens</th>
                  <th className="px-5 py-3 text-right">Output Tokens</th>
                  <th className="px-5 py-3 text-right">Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {usage.records.map((record) => (
                  <tr key={record.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3 text-gray-600">{formatDate(record.timestamp)}</td>
                    <td className="px-5 py-3">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                          PURPOSE_COLORS[record.purpose] || 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {record.purpose}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-gray-500 font-mono text-xs">{record.model}</td>
                    <td className="px-5 py-3 text-right text-gray-600">
                      {record.input_tokens.toLocaleString()}
                    </td>
                    <td className="px-5 py-3 text-right text-gray-600">
                      {record.output_tokens.toLocaleString()}
                    </td>
                    <td className="px-5 py-3 text-right font-medium text-gray-900">
                      {formatCost(record.cost_estimate)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick actions section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Preview Library */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Eye size={16} className="text-indigo-500" />
            <h3 className="text-sm font-semibold text-gray-700">Preview Library</h3>
          </div>
          <textarea
            value={previewYaml}
            onChange={(e) => setPreviewYaml(e.target.value)}
            placeholder="Paste library YAML here..."
            className="w-full h-28 rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono resize-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
          />
          <button
            onClick={() => previewMutation.mutate(previewYaml)}
            disabled={previewMutation.isPending || !previewYaml.trim() || !status?.configured}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 text-white text-sm font-medium px-4 py-2 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {previewMutation.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
            Generate Preview
          </button>
          {previewMutation.isError && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
              {(previewMutation.error as Error).message}
            </div>
          )}
          {previewResult && (
            <div className="mt-2 rounded-lg bg-gray-50 border border-gray-200 p-3 text-sm text-gray-700 whitespace-pre-wrap max-h-60 overflow-y-auto">
              {previewResult}
            </div>
          )}
        </div>

        {/* Suggest Guardrails */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Shield size={16} className="text-amber-500" />
            <h3 className="text-sm font-semibold text-gray-700">Suggest Guardrails</h3>
          </div>
          <textarea
            value={guardrailYaml}
            onChange={(e) => setGuardrailYaml(e.target.value)}
            placeholder="Paste library YAML here..."
            className="w-full h-28 rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono resize-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
          />
          <button
            onClick={() => guardrailMutation.mutate(guardrailYaml)}
            disabled={guardrailMutation.isPending || !guardrailYaml.trim() || !status?.configured}
            className="flex items-center gap-2 rounded-lg bg-amber-500 text-white text-sm font-medium px-4 py-2 hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {guardrailMutation.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Shield size={14} />
            )}
            Get Suggestions
          </button>
          {guardrailMutation.isError && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
              {(guardrailMutation.error as Error).message}
            </div>
          )}
          {guardrailResult && (
            <div className="mt-2 rounded-lg bg-gray-50 border border-gray-200 p-3 text-sm text-gray-700 whitespace-pre-wrap font-mono max-h-60 overflow-y-auto">
              {guardrailResult}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
