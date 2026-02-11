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
