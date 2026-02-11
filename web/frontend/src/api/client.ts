import type {
  LibraryEntry,
  SearchResult,
  ConformanceResult,
  Candidate,
  AnalyzeResult,
  DriftReport,
  ProvenanceRecord,
  IRModule,
  Draft,
  ValidationResult,
  EnrichmentResult,
  User,
  APIKeyEntry,
  LoginResult,
  ConformanceHistoryEntry,
  BatchConformanceResult,
  DriftSummary,
  Organization,
  OrgMember,
  OrgRepo,
  OrgDashboard,
  Policy,
  PolicyRule,
  PolicyEvaluation,
  ApprovalRequest,
  LLMStatus,
  UsageSummary,
  Budget,
  BudgetStatus,
  LLMPreviewResult,
  LLMEnrichResult,
  LLMGuardrailSuggestion,
  AuditEntry,
  Webhook,
  WebhookDelivery,
  Plugin,
  SecurityDashboard,
  GeneratedLibrary,
  GenerateLibraryResponse,
  AIQueryRequest,
  AIQueryResponse,
  AIQueryHistoryEntry,
  UserModerationStatus,
  UpdateCheckResult,
  GenerateLibraryResponse,
} from '../types';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (body.detail) {
        message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // ignore parse errors
    }
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

export async function fetchRegistry(): Promise<LibraryEntry[]> {
  return request<LibraryEntry[]>('/api/registry');
}

export async function searchRegistry(params: {
  q?: string;
  tags?: string[];
  verified_only?: boolean;
  limit?: number;
  offset?: number;
}): Promise<SearchResult> {
  const searchParams = new URLSearchParams();
  if (params.q) searchParams.set('q', params.q);
  if (params.tags) {
    params.tags.forEach((tag) => searchParams.append('tags', tag));
  }
  if (params.verified_only) searchParams.set('verified_only', 'true');
  if (params.limit !== undefined) searchParams.set('limit', String(params.limit));
  if (params.offset !== undefined) searchParams.set('offset', String(params.offset));

  return request<SearchResult>(`/api/registry/search?${searchParams.toString()}`);
}

export async function getLibrary(name: string, version?: string): Promise<LibraryEntry> {
  const path = version ? `/api/registry/${name}/${version}` : `/api/registry/${name}`;
  return request<LibraryEntry>(path);
}

export async function runConformance(
  libraryPath: string,
  workingDir?: string
): Promise<ConformanceResult> {
  return request<ConformanceResult>('/api/conformance/run', {
    method: 'POST',
    body: JSON.stringify({
      library_path: libraryPath,
      working_dir: workingDir || '.',
    }),
  });
}

export async function validateLibrary(libraryPath: string): Promise<ConformanceResult> {
  return request<ConformanceResult>('/api/conformance/validate', {
    method: 'POST',
    body: JSON.stringify({
      library_path: libraryPath,
    }),
  });
}

export async function getSchema(): Promise<unknown> {
  return request<unknown>('/api/schema');
}

export async function analyzeRepo(
  repoPath: string,
  depth?: string
): Promise<AnalyzeResult> {
  return request<AnalyzeResult>('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({
      repo_path: repoPath,
      depth: depth || 'standard',
    }),
  });
}

export async function checkDrift(
  repoPath: string,
  libraryName?: string
): Promise<DriftReport[]> {
  if (libraryName) {
    return request<DriftReport[]>('/api/drift/check', {
      method: 'POST',
      body: JSON.stringify({
        repo_path: repoPath,
        library_name: libraryName,
      }),
    });
  }
  return request<DriftReport[]>('/api/drift/check-all', {
    method: 'POST',
    body: JSON.stringify({
      repo_path: repoPath,
    }),
  });
}

export async function getProvenance(
  repoPath: string,
  libraryName?: string
): Promise<ProvenanceRecord[]> {
  const params = new URLSearchParams({ repo_path: repoPath });
  if (libraryName) params.set('library_name', libraryName);
  return request<ProvenanceRecord[]>(`/api/provenance?${params.toString()}`);
}

// IR Explorer API
export async function parseFile(filePath: string, repoRoot?: string): Promise<IRModule> {
  return request<IRModule>('/api/ir/parse', {
    method: 'POST',
    body: JSON.stringify({ file_path: filePath, repo_root: repoRoot || '' }),
  });
}

// Generator / Editor API
export async function generateLibrary(
  repoPath: string,
  featureName: string,
  enrich?: boolean
): Promise<{ success: boolean; output_path?: string; message: string }> {
  return request<{ success: boolean; output_path?: string; message: string }>('/api/generate', {
    method: 'POST',
    body: JSON.stringify({ repo_path: repoPath, feature_name: featureName, enrich: enrich ?? true }),
  });
}

export async function validateContent(yamlContent: string): Promise<ValidationResult> {
  return request<ValidationResult>('/api/generate/validate', {
    method: 'POST',
    body: JSON.stringify({ yaml_content: yamlContent }),
  });
}

export async function enrichContent(yamlContent: string): Promise<EnrichmentResult> {
  return request<EnrichmentResult>('/api/generate/enrich', {
    method: 'POST',
    body: JSON.stringify({ yaml_content: yamlContent }),
  });
}

export async function saveDraft(name: string, yamlContent: string): Promise<Draft> {
  return request<Draft>('/api/generate/save-draft', {
    method: 'POST',
    body: JSON.stringify({ name, yaml_content: yamlContent }),
  });
}

export async function listDrafts(): Promise<Draft[]> {
  return request<Draft[]>('/api/generate/drafts');
}

export async function getDraft(id: string): Promise<Draft> {
  return request<Draft>(`/api/generate/drafts/${id}`);
}

export async function deleteDraft(id: string): Promise<void> {
  await request<void>(`/api/generate/drafts/${id}`, { method: 'DELETE' });
}

export async function publishFromEditor(yamlContent: string, name?: string): Promise<LibraryEntry> {
  return request<LibraryEntry>('/api/generate/publish', {
    method: 'POST',
    body: JSON.stringify({ yaml_content: yamlContent, name: name || '' }),
  });
}

// Auth API
export async function loginDemo(): Promise<LoginResult> {
  return request<LoginResult>('/api/auth/login/github');
}

export async function logout(token: string): Promise<void> {
  await request<void>('/api/auth/logout', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getCurrentUser(token: string): Promise<User> {
  return request<User>('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function listUsers(token: string): Promise<User[]> {
  return request<User[]>('/api/auth/users', {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateUserRole(token: string, userId: string, role: string): Promise<User> {
  return request<User>(`/api/auth/users/${userId}/role`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ role }),
  });
}

export async function createAPIKey(token: string, name: string): Promise<{ key: APIKeyEntry; raw_key: string }> {
  return request<{ key: APIKeyEntry; raw_key: string }>('/api/auth/api-keys', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ name }),
  });
}

export async function listAPIKeys(token: string): Promise<APIKeyEntry[]> {
  return request<APIKeyEntry[]>('/api/auth/api-keys', {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function deleteAPIKey(token: string, keyId: string): Promise<void> {
  await request<void>(`/api/auth/api-keys/${keyId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });
}

// Enhanced endpoints

export async function getLibraryVersions(name: string): Promise<LibraryEntry[]> {
  return request<LibraryEntry[]>(`/api/registry/${encodeURIComponent(name)}/versions`);
}

export async function getConformanceHistory(libraryName: string): Promise<ConformanceHistoryEntry[]> {
  return request<ConformanceHistoryEntry[]>(`/api/conformance/history?library_name=${encodeURIComponent(libraryName)}`);
}

export async function runBatchConformance(): Promise<BatchConformanceResult> {
  return request<BatchConformanceResult>('/api/conformance/batch', { method: 'POST' });
}

export async function getDriftSummary(repoPath: string): Promise<DriftSummary> {
  const params = new URLSearchParams({ repo_path: repoPath });
  return request<DriftSummary>(`/api/drift/summary?${params.toString()}`);
}

// Organization API
export async function createOrg(name: string, description?: string): Promise<Organization> {
  return request<Organization>('/api/orgs', {
    method: 'POST',
    body: JSON.stringify({ name, description: description || '' }),
  });
}

export async function listOrgs(): Promise<Organization[]> {
  return request<Organization[]>('/api/orgs');
}

export async function getOrg(slug: string): Promise<Organization> {
  return request<Organization>(`/api/orgs/${slug}`);
}

export async function updateOrg(slug: string, data: { name?: string; description?: string }): Promise<Organization> {
  return request<Organization>(`/api/orgs/${slug}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteOrg(slug: string): Promise<void> {
  await request<void>(`/api/orgs/${slug}`, { method: 'DELETE' });
}

export async function listOrgMembers(slug: string): Promise<OrgMember[]> {
  return request<OrgMember[]>(`/api/orgs/${slug}/members`);
}

export async function addOrgMember(slug: string, userId: string, role?: string): Promise<OrgMember> {
  return request<OrgMember>(`/api/orgs/${slug}/members`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, role: role || 'member' }),
  });
}

export async function removeOrgMember(slug: string, userId: string): Promise<void> {
  await request<void>(`/api/orgs/${slug}/members/${userId}`, { method: 'DELETE' });
}

export async function updateOrgMemberRole(slug: string, userId: string, role: string): Promise<OrgMember> {
  return request<OrgMember>(`/api/orgs/${slug}/members/${userId}/role`, {
    method: 'PUT',
    body: JSON.stringify({ role }),
  });
}

export async function listOrgRepos(slug: string): Promise<OrgRepo[]> {
  return request<OrgRepo[]>(`/api/orgs/${slug}/repos`);
}

export async function addOrgRepo(slug: string, name: string, url: string, defaultBranch?: string): Promise<OrgRepo> {
  return request<OrgRepo>(`/api/orgs/${slug}/repos`, {
    method: 'POST',
    body: JSON.stringify({ name, url, default_branch: defaultBranch || 'main' }),
  });
}

export async function removeOrgRepo(slug: string, repoId: string): Promise<void> {
  await request<void>(`/api/orgs/${slug}/repos/${repoId}`, { method: 'DELETE' });
}

export async function scanOrgRepo(slug: string, repoId: string): Promise<void> {
  await request<void>(`/api/orgs/${slug}/repos/${repoId}/scan`, { method: 'POST' });
}

export async function getOrgDashboard(slug: string): Promise<OrgDashboard> {
  return request<OrgDashboard>(`/api/orgs/${slug}/dashboard`);
}

// Policy API
export async function createPolicy(name: string, description?: string, rules?: PolicyRule[]): Promise<Policy> {
  return request<Policy>('/api/policies', {
    method: 'POST',
    body: JSON.stringify({ name, description: description || '', rules: rules || [] }),
  });
}

export async function listPolicies(): Promise<Policy[]> {
  return request<Policy[]>('/api/policies');
}

export async function getPolicy(id: string): Promise<Policy> {
  return request<Policy>(`/api/policies/${id}`);
}

export async function updatePolicy(id: string, data: { name?: string; description?: string; rules?: PolicyRule[] }): Promise<Policy> {
  return request<Policy>(`/api/policies/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deletePolicy(id: string): Promise<void> {
  await request<void>(`/api/policies/${id}`, { method: 'DELETE' });
}

export async function togglePolicy(id: string, enabled: boolean): Promise<Policy> {
  return request<Policy>(`/api/policies/${id}/toggle`, {
    method: 'PUT',
    body: JSON.stringify({ enabled }),
  });
}

export async function evaluatePolicy(libraryName: string, libraryVersion?: string, targetFiles?: string[], capabilities?: string[]): Promise<PolicyEvaluation> {
  return request<PolicyEvaluation>('/api/policies/evaluate', {
    method: 'POST',
    body: JSON.stringify({
      library_name: libraryName,
      library_version: libraryVersion || '1.0.0',
      target_files: targetFiles || [],
      capabilities_used: capabilities || [],
    }),
  });
}

// Approval API
export async function createApprovalRequest(libraryName: string, libraryVersion: string, policyId: string, reason?: string): Promise<ApprovalRequest> {
  return request<ApprovalRequest>('/api/approvals', {
    method: 'POST',
    body: JSON.stringify({ library_name: libraryName, library_version: libraryVersion, policy_id: policyId, reason: reason || '' }),
  });
}

export async function listApprovals(status?: string): Promise<ApprovalRequest[]> {
  const params = status ? `?status_filter=${status}` : '';
  return request<ApprovalRequest[]>(`/api/approvals${params}`);
}

export async function approveRequest(id: string, comment?: string): Promise<ApprovalRequest> {
  return request<ApprovalRequest>(`/api/approvals/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ comment: comment || '' }),
  });
}

export async function rejectRequest(id: string, comment?: string): Promise<ApprovalRequest> {
  return request<ApprovalRequest>(`/api/approvals/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ comment: comment || '' }),
  });
}

export async function getPendingCount(): Promise<number> {
  const data = await request<{ count: number }>('/api/approvals/pending/count');
  return data.count;
}

// LLM API
export async function getLLMStatus(): Promise<LLMStatus> {
  return request<LLMStatus>('/api/llm/status');
}

export async function getLLMUsage(period?: string): Promise<UsageSummary> {
  const params = period ? `?period=${period}` : '';
  return request<UsageSummary>(`/api/llm/usage${params}`);
}

export async function getLLMCost(period?: string): Promise<{ total_cost: number }> {
  const params = period ? `?period=${period}` : '';
  return request<{ total_cost: number }>(`/api/llm/usage/cost${params}`);
}

export async function getLLMBudget(): Promise<Budget> {
  return request<Budget>('/api/llm/budget');
}

export async function setLLMBudget(monthlyLimit: number, alertThresholdPct?: number): Promise<Budget> {
  return request<Budget>('/api/llm/budget', {
    method: 'PUT',
    body: JSON.stringify({ monthly_limit: monthlyLimit, alert_threshold_pct: alertThresholdPct || 80 }),
  });
}

export async function getLLMBudgetStatus(): Promise<BudgetStatus> {
  return request<BudgetStatus>('/api/llm/budget/status');
}

export async function generatePreview(yamlContent: string): Promise<LLMPreviewResult> {
  return request<LLMPreviewResult>('/api/llm/preview', {
    method: 'POST',
    body: JSON.stringify({ yaml_content: yamlContent }),
  });
}

export async function llmEnrich(yamlContent: string): Promise<LLMEnrichResult> {
  return request<LLMEnrichResult>('/api/llm/enrich', {
    method: 'POST',
    body: JSON.stringify({ yaml_content: yamlContent }),
  });
}

export async function suggestGuardrails(yamlContent: string): Promise<LLMGuardrailSuggestion> {
  return request<LLMGuardrailSuggestion>('/api/llm/suggest-guardrails', {
    method: 'POST',
    body: JSON.stringify({ yaml_content: yamlContent }),
  });
}

export async function llmDescribe(yamlContent: string): Promise<{ description: string }> {
  return request<{ description: string }>('/api/llm/describe', {
    method: 'POST',
    body: JSON.stringify({ yaml_content: yamlContent }),
  });
}

// Security & Audit API
export async function getAuditEvents(params?: {
  actor?: string;
  action?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
}): Promise<AuditEntry[]> {
  const searchParams = new URLSearchParams();
  if (params?.actor) searchParams.set('actor', params.actor);
  if (params?.action) searchParams.set('action', params.action);
  if (params?.resource_type) searchParams.set('resource_type', params.resource_type);
  if (params?.start_date) searchParams.set('start_date', params.start_date);
  if (params?.end_date) searchParams.set('end_date', params.end_date);
  if (params?.limit) searchParams.set('limit', String(params.limit));
  return request<AuditEntry[]>(`/api/security/audit?${searchParams.toString()}`);
}

export async function exportAuditLog(format: string): Promise<{ format: string; content: string; record_count: number }> {
  return request<{ format: string; content: string; record_count: number }>(`/api/security/audit/export?format=${format}`);
}

export async function getSecurityDashboard(): Promise<SecurityDashboard> {
  return request<SecurityDashboard>('/api/security/dashboard');
}

// Webhook API
export async function createWebhook(name: string, url: string, events: string[], secret?: string): Promise<Webhook> {
  return request<Webhook>('/api/security/webhooks', {
    method: 'POST',
    body: JSON.stringify({ name, url, events, secret: secret || '' }),
  });
}

export async function listWebhooks(): Promise<Webhook[]> {
  return request<Webhook[]>('/api/security/webhooks');
}

export async function getWebhook(id: string): Promise<Webhook> {
  return request<Webhook>(`/api/security/webhooks/${id}`);
}

export async function updateWebhook(id: string, data: { name?: string; url?: string; events?: string[] }): Promise<Webhook> {
  return request<Webhook>(`/api/security/webhooks/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteWebhook(id: string): Promise<void> {
  await request<void>(`/api/security/webhooks/${id}`, { method: 'DELETE' });
}

export async function toggleWebhook(id: string, active: boolean): Promise<Webhook> {
  return request<Webhook>(`/api/security/webhooks/${id}/toggle`, {
    method: 'PUT',
    body: JSON.stringify({ active }),
  });
}

export async function testWebhook(id: string): Promise<WebhookDelivery> {
  return request<WebhookDelivery>(`/api/security/webhooks/${id}/test`, { method: 'POST' });
}

export async function getWebhookDeliveries(id: string): Promise<WebhookDelivery[]> {
  return request<WebhookDelivery[]>(`/api/security/webhooks/${id}/deliveries`);
}

// Plugin API
export async function createPlugin(name: string, description?: string, hooks?: string[]): Promise<Plugin> {
  return request<Plugin>('/api/security/plugins', {
    method: 'POST',
    body: JSON.stringify({ name, description: description || '', hooks: hooks || [] }),
  });
}

export async function listPlugins(): Promise<Plugin[]> {
  return request<Plugin[]>('/api/security/plugins');
}

export async function togglePlugin(id: string, enabled: boolean): Promise<Plugin> {
  return request<Plugin>(`/api/security/plugins/${id}/toggle`, {
    method: 'PUT',
    body: JSON.stringify({ enabled }),
  });
}

export async function deletePlugin(id: string): Promise<void> {
  await request<void>(`/api/security/plugins/${id}`, { method: 'DELETE' });
}

// Hierarchical Library Generation API

export async function generateHierarchicalLibrary(params: {
  repo_path: string;
  candidate_name: string;
  candidate_description: string;
  source_files: string[];
  entry_points: string[];
  tags: string[];
  source_repo_url?: string;
}): Promise<GenerateLibraryResponse> {
  return request<GenerateLibraryResponse>('/api/generate/library', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function listGeneratedLibraries(): Promise<GeneratedLibrary[]> {
  return request<GeneratedLibrary[]>('/api/generate/libraries');
}

export async function searchGeneratedLibraries(text: string = ''): Promise<GeneratedLibrary[]> {
  const params = new URLSearchParams();
  if (text) params.set('text', text);
  return request<GeneratedLibrary[]>(`/api/generate/libraries/search?${params.toString()}`);
}

export async function getGeneratedLibrary(id: string): Promise<GeneratedLibrary> {
  return request<GeneratedLibrary>(`/api/generate/libraries/${id}`);
}

export async function deleteGeneratedLibrary(id: string): Promise<void> {
  await request<void>(`/api/generate/libraries/${id}`, { method: 'DELETE' });
}

// AI Query API

export async function submitAIQuery(params: AIQueryRequest): Promise<AIQueryResponse> {
  return request<AIQueryResponse>('/api/ai-query', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function getAIQueryHistory(
  libraryName: string,
  componentName: string,
  limit?: number
): Promise<AIQueryHistoryEntry[]> {
  const searchParams = new URLSearchParams({
    library_name: libraryName,
    component_name: componentName,
  });
  if (limit !== undefined) searchParams.set('limit', String(limit));
  return request<AIQueryHistoryEntry[]>(`/api/ai-query/history?${searchParams.toString()}`);
}

export async function getAIQueryInsights(
  libraryName: string,
  componentName: string,
  limit?: number
): Promise<AIQueryHistoryEntry[]> {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set('limit', String(limit));
  const qs = params.toString();
  return request<AIQueryHistoryEntry[]>(
    `/api/ai-query/insights/${encodeURIComponent(libraryName)}/${encodeURIComponent(componentName)}${qs ? '?' + qs : ''}`
  );
}

export async function getUserModerationStatus(): Promise<UserModerationStatus> {
  return request<UserModerationStatus>('/api/ai-query/user-status');
}

export async function adminUnlockUser(userId: string): Promise<void> {
  await request<void>(`/api/ai-query/admin/unlock/${encodeURIComponent(userId)}`, {
    method: 'POST',
  });
}

// Library Update Detection API

export async function checkLibraryUpdates(libraryId: string): Promise<UpdateCheckResult> {
  return request<UpdateCheckResult>(`/api/generate/libraries/${encodeURIComponent(libraryId)}/check-updates`, {
    method: 'POST',
  });
}

export async function updateLibrary(libraryId: string): Promise<GenerateLibraryResponse> {
  return request<GenerateLibraryResponse>(`/api/generate/libraries/${encodeURIComponent(libraryId)}/update`, {
    method: 'POST',
  });
}

export async function createLibraryFromLatest(libraryId: string, newName?: string): Promise<GenerateLibraryResponse> {
  return request<GenerateLibraryResponse>(`/api/generate/libraries/${encodeURIComponent(libraryId)}/create-from-latest`, {
    method: 'POST',
    body: JSON.stringify({ library_id: libraryId, new_name: newName || '' }),
  });
}
