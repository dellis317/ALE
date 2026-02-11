export interface QualitySignals {
  verification: {
    schema_passed: boolean;
    validator_passed: boolean;
    hooks_runnable: boolean;
    verified_at: string;
    verified_by: string;
  };
  rating: number;
  rating_count: number;
  download_count: number;
  maintained: boolean;
  maintainer: string;
  last_updated: string;
}

export interface LibraryEntry {
  name: string;
  version: string;
  spec_version: string;
  description: string;
  tags: string[];
  capabilities: string[];
  complexity: string;
  language_agnostic: boolean;
  target_languages: string[];
  quality: QualitySignals;
  source_repo: string;
  library_path: string;
  compatibility_targets: string[];
  qualified_id: string;
  is_verified: boolean;
}

export interface SearchResult {
  entries: LibraryEntry[];
  total_count: number;
}

export interface HookResult {
  description: string;
  hook_type: string;
  passed: boolean;
  exit_code: number;
  stdout: string;
  stderr: string;
  duration_ms: number;
  error: string;
}

export interface ValidationIssue {
  severity: string;
  code: string;
  message: string;
  path: string;
}

export interface ConformanceResult {
  library_name: string;
  library_version: string;
  spec_version: string;
  schema_passed: boolean;
  semantic_passed: boolean;
  schema_errors: string[];
  semantic_errors: ValidationIssue[];
  semantic_warnings: ValidationIssue[];
  hook_results: HookResult[];
  all_passed: boolean;
  hooks_passed: boolean;
  total_duration_ms: number;
}

export interface ScoreDimension {
  name: string;
  score: number;
  weight: number;
  reasons: string[];
  flags: string[];
}

export interface Candidate {
  name: string;
  description: string;
  source_files: string[];
  entry_points: string[];
  overall_score: number;
  tags: string[];
  isolation_score: number;
  reuse_score: number;
  complexity_score: number;
  clarity_score: number;
  scoring: {
    dimensions: ScoreDimension[];
    overall_score: number;
    all_flags: string[];
    top_reasons: string[];
  };
}

export interface DriftReport {
  library_name: string;
  applied_version: string;
  latest_version: string;
  drift_types: string[];
  details: string[];
  has_drift: boolean;
  validation_still_passes: boolean | null;
}

export interface ProvenanceRecord {
  library_name: string;
  library_version: string;
  applied_at: string;
  applied_by: string;
  target_repo: string;
  target_branch: string;
  validation_passed: boolean;
  validation_evidence: string;
  commit_sha: string;
}

// IR Explorer types (frontend-friendly)
export interface IRSymbol {
  name: string;
  kind: string;
  source_file: string;
  line_start: number;
  line_end: number;
  line_count: number;
  visibility: string;
  parameters: IRParameter[];
  return_type: string;
  is_async: boolean;
  side_effects: string[];
  docstring: string;
  base_classes: string[];
  interfaces: string[];
  members: IRSymbol[];
  qualified_name: string;
}

export interface IRParameter {
  name: string;
  type_hint: string;
  default_value: string;
  required: boolean;
}

export interface IRDependency {
  source: string;
  target: string;
  kind: string;
  is_external: boolean;
}

export interface IRModule {
  path: string;
  language: string;
  symbols: IRSymbol[];
  imports: IRDependency[];
}

// Generator / Editor types
export interface Draft {
  id: string;
  name: string;
  yaml_content: string;
  created_at: string;
  updated_at: string;
}

export interface ValidationResult {
  valid: boolean;
  schema_errors: string[];
  semantic_errors: string[];
  semantic_warnings: string[];
}

export interface EnrichmentResult {
  enriched_yaml: string;
  suggestions: string[];
}

// Auth types
export interface User {
  id: string;
  username: string;
  email: string;
  display_name: string;
  avatar_url: string;
  provider: string;
  role: string;
  org_id: string;
  created_at: string;
  last_login: string;
}

export interface APIKeyEntry {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  expires_at: string;
  last_used: string;
}

export interface LoginResult {
  token: string;
  user: User;
}

// Enhanced Analyzer types
export interface CandidateSymbol {
  name: string;
  kind: string;
  signature: string;
  docstring: string;
}

export interface EnhancedCandidate extends Candidate {
  context_summary: string;
  symbols: CandidateSymbol[];
  callers: string[];
  callees: string[];
}

// Codebase summary from analyzer
export interface CodebaseSummary {
  total_files: number;
  total_lines: number;
  files_by_language: Record<string, number>;
  total_modules: number;
  total_functions: number;
  total_classes: number;
  total_constants: number;
  external_packages: string[];
  internal_module_count: number;
  docstring_coverage: number;
  type_hint_coverage: number;
  has_tests: boolean;
  has_ci_config: boolean;
  description: string;
  purpose: string;
  top_level_packages: string[];
  key_capabilities: string[];
}

// Full analysis result (summary + candidates)
export interface AnalyzeResult {
  summary: CodebaseSummary;
  candidates: Candidate[];
}

// Conformance history
export interface ConformanceHistoryEntry {
  library_name: string;
  library_version: string;
  ran_at: string;
  all_passed: boolean;
  schema_passed: boolean;
  semantic_passed: boolean;
  hooks_passed: boolean;
  total_duration_ms: number;
}

export interface BatchConformanceResult {
  total: number;
  passed: number;
  failed: number;
  results: ConformanceResult[];
}

// Drift summary
export interface DriftSummary {
  total_libraries: number;
  clean_count: number;
  drifted_count: number;
  by_type: Record<string, number>;
}

// Organization types
export interface Organization {
  id: string;
  name: string;
  slug: string;
  description: string;
  owner_id: string;
  created_at: string;
  member_count: number;
  repo_count: number;
}

export interface OrgMember {
  user_id: string;
  username: string;
  email: string;
  role: string;
  joined_at: string;
}

export interface OrgRepo {
  id: string;
  org_id: string;
  name: string;
  url: string;
  default_branch: string;
  added_at: string;
  last_scanned: string;
  scan_status: string;
}

export interface OrgDashboard {
  org: Organization;
  total_libraries: number;
  total_members: number;
  total_repos: number;
  recent_scans: OrgRepo[];
}

// Policy types
export interface PolicyRule {
  name: string;
  description: string;
  scope: string;
  action: string;
  patterns: string[];
  conditions: Record<string, string>;
  rationale: string;
}

export interface Policy {
  id: string;
  name: string;
  description: string;
  version: string;
  rules: PolicyRule[];
  created_at: string;
  updated_at: string;
  enabled: boolean;
}

export interface PolicyEvaluation {
  allowed: boolean;
  action: string;
  matched_rules: Record<string, unknown>[];
  reasons: string[];
}

export interface ApprovalRequest {
  id: string;
  library_name: string;
  library_version: string;
  requester_id: string;
  policy_id: string;
  reason: string;
  status: string;
  created_at: string;
  decided_at: string;
  decided_by: string;
  decision_comment: string;
}

// LLM types
export interface UsageRecord {
  id: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  purpose: string;
  cost_estimate: number;
  timestamp: string;
}

export interface UsageSummary {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost: number;
  record_count: number;
  records: UsageRecord[];
}

export interface Budget {
  monthly_limit: number;
  alert_threshold_pct: number;
  current_month_cost: number;
}

export interface BudgetStatus {
  allowed: boolean;
  remaining: number;
  percent_used: number;
  over_limit: boolean;
  monthly_limit: number;
}

export interface LLMStatus {
  configured: boolean;
  model: string;
  message: string;
}

export interface LLMPreviewResult {
  preview: string;
  tokens_used: number;
  cost_estimate: number;
}

export interface LLMEnrichResult {
  enriched_yaml: string;
  changes_summary: string[];
  tokens_used: number;
  cost_estimate: number;
}

export interface LLMGuardrailSuggestion {
  guardrails: Record<string, unknown>[];
  tokens_used: number;
  cost_estimate: number;
}

// Security & Audit types
export interface AuditEntry {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
  ip_address: string;
  user_agent: string;
  success: boolean;
}

export interface Webhook {
  id: string;
  name: string;
  url: string;
  events: string[];
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WebhookDelivery {
  id: string;
  webhook_id: string;
  event: string;
  payload: Record<string, unknown>;
  response_status: number;
  response_body: string;
  success: boolean;
  delivered_at: string;
  duration_ms: number;
}

export interface Plugin {
  id: string;
  name: string;
  description: string;
  hooks: string[];
  config: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
}

export interface SecurityDashboard {
  total_events: number;
  events_today: number;
  active_webhooks: number;
  total_webhooks: number;
  enabled_plugins: number;
  total_plugins: number;
  recent_events: AuditEntry[];
  failed_deliveries_24h: number;
}
