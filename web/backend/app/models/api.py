"""Pydantic models for API request/response serialization.

These models mirror the ALE dataclasses and provide proper JSON
serialization for the FastAPI endpoints.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Registry models
# ---------------------------------------------------------------------------


class VerificationResultResponse(BaseModel):
    """Mirrors ale.registry.models.VerificationResult."""

    schema_passed: bool = False
    validator_passed: bool = False
    hooks_runnable: bool = False
    verified_at: str = ""
    verified_by: str = ""


class QualitySignalsResponse(BaseModel):
    """Mirrors ale.registry.models.QualitySignals."""

    verification: VerificationResultResponse = Field(
        default_factory=VerificationResultResponse
    )
    rating: float = 0.0
    rating_count: int = 0
    download_count: int = 0
    maintained: bool = True
    maintainer: str = ""
    last_updated: str = ""


class LibraryEntryResponse(BaseModel):
    """Mirrors ale.registry.models.RegistryEntry."""

    name: str
    version: str
    spec_version: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    complexity: str = ""
    language_agnostic: bool = True
    target_languages: list[str] = Field(default_factory=list)
    quality: QualitySignalsResponse = Field(default_factory=QualitySignalsResponse)
    source_repo: str = ""
    library_path: str = ""
    compatibility_targets: list[str] = Field(default_factory=list)
    qualified_id: str = ""
    is_verified: bool = False


class SearchQueryRequest(BaseModel):
    """Mirrors ale.registry.models.SearchQuery."""

    text: str = ""
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    verified_only: bool = False
    min_rating: float = 0.0
    max_complexity: str = ""


class SearchResultResponse(BaseModel):
    """Mirrors ale.registry.models.SearchResult."""

    entries: list[LibraryEntryResponse] = Field(default_factory=list)
    total_count: int = 0
    query: SearchQueryRequest = Field(default_factory=SearchQueryRequest)


# ---------------------------------------------------------------------------
# Conformance / Validation models
# ---------------------------------------------------------------------------


class HookResultResponse(BaseModel):
    """Mirrors ale.spec.reference_runner.HookResult."""

    description: str
    hook_type: str
    passed: bool
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    error: str = ""


class ConformanceRequest(BaseModel):
    """Request body for running conformance checks."""

    library_path: str
    working_dir: str = "."


class ConformanceResponse(BaseModel):
    """Mirrors ale.spec.reference_runner.RunnerResult."""

    library_name: str
    library_version: str
    spec_version: str = ""
    schema_passed: bool
    semantic_passed: bool
    all_passed: bool
    hooks_passed: bool = True
    schema_errors: list[str] = Field(default_factory=list)
    semantic_errors: list[str] = Field(default_factory=list)
    semantic_warnings: list[str] = Field(default_factory=list)
    hook_results: list[HookResultResponse] = Field(default_factory=list)
    total_duration_ms: int = 0


class ValidationIssueResponse(BaseModel):
    """Mirrors ale.spec.semantic_validator.ValidationIssue."""

    severity: str
    code: str
    message: str
    path: str = ""


class ValidateResponse(BaseModel):
    """Response for schema + semantic validation (no hooks)."""

    schema_passed: bool
    schema_errors: list[str] = Field(default_factory=list)
    semantic_passed: bool
    semantic_issues: list[ValidationIssueResponse] = Field(default_factory=list)
    summary: str = ""


class SchemaResponse(BaseModel):
    """Wraps the JSON Schema dict."""

    schema_data: dict[str, Any] = Field(
        default_factory=dict, alias="schema"
    )

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Analyze / Generate models
# ---------------------------------------------------------------------------


class ScoreDimensionResponse(BaseModel):
    """Mirrors ale.models.candidate.ScoreDimension."""

    name: str
    score: float
    weight: float
    weighted_score: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class ScoringBreakdownResponse(BaseModel):
    """Mirrors ale.models.candidate.ScoringBreakdown."""

    dimensions: list[ScoreDimensionResponse] = Field(default_factory=list)
    overall_score: float = 0.0
    all_flags: list[str] = Field(default_factory=list)
    top_reasons: list[str] = Field(default_factory=list)


class CandidateResponse(BaseModel):
    """Mirrors ale.models.candidate.ExtractionCandidate."""

    name: str
    description: str
    source_files: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    scoring: ScoringBreakdownResponse = Field(
        default_factory=ScoringBreakdownResponse
    )
    overall_score: float = 0.0
    isolation_score: float = 0.0
    reuse_score: float = 0.0
    complexity_score: float = 0.0
    clarity_score: float = 0.0
    tags: list[str] = Field(default_factory=list)
    estimated_instruction_steps: int = 0
    dependencies_external: list[str] = Field(default_factory=list)
    dependencies_internal: list[str] = Field(default_factory=list)
    context_summary: str = ""
    symbols: list[dict] = Field(default_factory=list)
    callers: list[str] = Field(default_factory=list)
    callees: list[str] = Field(default_factory=list)


class CodebaseSummaryResponse(BaseModel):
    """Summary of the analyzed codebase."""

    total_files: int = 0
    total_lines: int = 0
    files_by_language: dict[str, int] = Field(default_factory=dict)
    total_modules: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_constants: int = 0
    external_packages: list[str] = Field(default_factory=list)
    internal_module_count: int = 0
    docstring_coverage: float = 0.0
    type_hint_coverage: float = 0.0
    has_tests: bool = False
    has_ci_config: bool = False
    description: str = ""
    purpose: str = ""
    top_level_packages: list[str] = Field(default_factory=list)
    key_capabilities: list[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    """Full analysis response with codebase summary and candidates."""

    summary: CodebaseSummaryResponse = Field(
        default_factory=CodebaseSummaryResponse
    )
    candidates: list[CandidateResponse] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    """Request body for repo analysis."""

    repo_path: str
    depth: str = "standard"


class GenerateRequest(BaseModel):
    """Request body for library generation."""

    repo_path: str
    feature_name: str
    enrich: bool = True
    output_dir: str = "./agentic_libs"


class GenerateResponse(BaseModel):
    """Response for library generation."""

    success: bool
    output_path: Optional[str] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Drift / Provenance models
# ---------------------------------------------------------------------------


class DriftCheckRequest(BaseModel):
    """Request body for drift checking."""

    repo_path: str
    library_name: str
    latest_version: str = ""
    library_path: Optional[str] = None


class DriftCheckAllRequest(BaseModel):
    """Request body for checking all libraries for drift."""

    repo_path: str


class DriftReportResponse(BaseModel):
    """Mirrors ale.sync.drift.DriftReport."""

    library_name: str
    applied_version: str
    latest_version: str = ""
    drift_types: list[str] = Field(default_factory=list)
    details: list[str] = Field(default_factory=list)
    has_drift: bool = False
    validation_still_passes: Optional[bool] = None


class ProvenanceRecordResponse(BaseModel):
    """Mirrors ale.models.agentic_library.ProvenanceRecord."""

    library_name: str
    library_version: str
    applied_at: str = ""
    applied_by: str = ""
    target_repo: str = ""
    target_branch: str = ""
    validation_passed: bool = False
    validation_evidence: str = ""
    commit_sha: str = ""


# ---------------------------------------------------------------------------
# IR models
# ---------------------------------------------------------------------------


class IRParameterResponse(BaseModel):
    """Mirrors ale.ir.models.IRParameter."""

    name: str
    type_hint: str = ""
    default_value: str = ""
    required: bool = True


class IRSymbolResponse(BaseModel):
    """Mirrors ale.ir.models.IRSymbol."""

    name: str
    kind: str
    source_file: str
    line_start: int = 0
    line_end: int = 0
    line_count: int = 0
    visibility: str = "public"
    parameters: list[IRParameterResponse] = Field(default_factory=list)
    return_type: str = ""
    is_async: bool = False
    side_effects: list[str] = Field(default_factory=list)
    docstring: str = ""
    base_classes: list[str] = Field(default_factory=list)
    interfaces: list[str] = Field(default_factory=list)
    members: list[IRSymbolResponse] = Field(default_factory=list)
    qualified_name: str = ""


class IRDependencyResponse(BaseModel):
    """Mirrors ale.ir.models.IRDependency."""

    source: str
    target: str
    kind: str
    is_external: bool = False


class IRModuleResponse(BaseModel):
    """Mirrors ale.ir.models.IRModule."""

    path: str
    language: str
    symbols: list[IRSymbolResponse] = Field(default_factory=list)
    imports: list[IRDependencyResponse] = Field(default_factory=list)


class IRParseRequest(BaseModel):
    """Request body for IR parsing."""

    file_path: str
    repo_root: str = ""


# ---------------------------------------------------------------------------
# Generator / Editor models
# ---------------------------------------------------------------------------


class DraftResponse(BaseModel):
    """Response model for a saved draft."""

    id: str
    name: str
    yaml_content: str
    created_at: str = ""
    updated_at: str = ""


class SaveDraftRequest(BaseModel):
    """Request body for saving a draft."""

    name: str
    yaml_content: str


class PublishFromEditorRequest(BaseModel):
    """Request body for publishing from the editor."""

    yaml_content: str
    name: str = ""


class ValidateContentRequest(BaseModel):
    """Request body for validating raw YAML content."""

    yaml_content: str


class ValidateContentResponse(BaseModel):
    """Response for YAML content validation."""

    valid: bool
    schema_errors: list[str] = Field(default_factory=list)
    semantic_errors: list[str] = Field(default_factory=list)
    semantic_warnings: list[str] = Field(default_factory=list)


class EnrichRequest(BaseModel):
    """Request body for LLM enrichment."""

    yaml_content: str


class EnrichResponse(BaseModel):
    """Response for LLM enrichment."""

    enriched_yaml: str
    suggestions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Auth models
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    """Public representation of a user."""

    id: str
    username: str
    email: str
    display_name: str
    avatar_url: str = ""
    provider: str = ""
    role: str = "viewer"
    org_id: str = ""
    created_at: str = ""
    last_login: str = ""


class APIKeyResponse(BaseModel):
    """Public representation of an API key (no secret material)."""

    id: str
    name: str
    prefix: str
    created_at: str = ""
    expires_at: str = ""
    last_used: str = ""


class APIKeyCreateRequest(BaseModel):
    """Request body for creating a new API key."""

    name: str
    expires_in_days: int = 90


class APIKeyCreateResponse(BaseModel):
    """Response after creating an API key -- includes raw key shown once."""

    key: APIKeyResponse
    raw_key: str  # Only shown once at creation


class RoleUpdateRequest(BaseModel):
    """Request body for updating a user's role."""

    role: str


class LoginResponse(BaseModel):
    """Response after successful login."""

    token: str
    user: UserResponse


class AuthStatusResponse(BaseModel):
    """Response for the /me endpoint."""

    authenticated: bool
    user: Optional[UserResponse] = None


# ---------------------------------------------------------------------------
# Conformance history models
# ---------------------------------------------------------------------------


class ConformanceHistoryEntry(BaseModel):
    """A single conformance history entry."""

    library_name: str
    library_version: str
    ran_at: str
    all_passed: bool
    schema_passed: bool
    semantic_passed: bool
    hooks_passed: bool
    total_duration_ms: int = 0


class BatchConformanceResult(BaseModel):
    """Result of batch conformance run across all registry libraries."""

    total: int
    passed: int
    failed: int
    results: list[ConformanceResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Drift summary models
# ---------------------------------------------------------------------------


class DriftSummaryResponse(BaseModel):
    """Aggregate drift statistics for a repository."""

    total_libraries: int = 0
    clean_count: int = 0
    drifted_count: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Organization models
# ---------------------------------------------------------------------------


class OrganizationResponse(BaseModel):
    """Public representation of an organization."""

    id: str
    name: str
    slug: str
    description: str = ""
    owner_id: str = ""
    created_at: str = ""
    member_count: int = 0
    repo_count: int = 0


class CreateOrgRequest(BaseModel):
    """Request body for creating a new organization."""

    name: str
    description: str = ""


class UpdateOrgRequest(BaseModel):
    """Request body for updating an organization."""

    name: str = ""
    description: str = ""


class OrgMemberResponse(BaseModel):
    """Public representation of an organization member."""

    user_id: str
    username: str = ""
    email: str = ""
    role: str = "member"
    joined_at: str = ""


class AddMemberRequest(BaseModel):
    """Request body for adding a member to an organization."""

    user_id: str
    role: str = "member"


class RepoResponse(BaseModel):
    """Public representation of a repository."""

    id: str
    org_id: str
    name: str
    url: str
    default_branch: str = "main"
    added_at: str = ""
    last_scanned: str = ""
    scan_status: str = "pending"


class AddRepoRequest(BaseModel):
    """Request body for adding a repository to an organization."""

    name: str
    url: str
    default_branch: str = "main"


class OrgDashboardResponse(BaseModel):
    """Dashboard statistics for an organization."""

    org: OrganizationResponse
    total_libraries: int = 0
    total_members: int = 0
    total_repos: int = 0
    recent_scans: list[RepoResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Policy models
# ---------------------------------------------------------------------------


class PolicyRuleRequest(BaseModel):
    """A single rule within a policy."""

    name: str
    description: str = ""
    scope: str = "all"
    action: str = "allow"
    patterns: list[str] = Field(default_factory=list)
    conditions: dict[str, str] = Field(default_factory=dict)
    rationale: str = ""


class PolicyResponse(BaseModel):
    """Public representation of a policy."""

    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    rules: list[PolicyRuleRequest] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    enabled: bool = True


class CreatePolicyRequest(BaseModel):
    """Request body for creating a new policy."""

    name: str
    description: str = ""
    rules: list[PolicyRuleRequest] = Field(default_factory=list)


class UpdatePolicyRequest(BaseModel):
    """Request body for updating an existing policy."""

    name: str = ""
    description: str = ""
    rules: list[PolicyRuleRequest] = Field(default_factory=list)


class TogglePolicyRequest(BaseModel):
    """Request body for toggling a policy's enabled state."""

    enabled: bool


class EvaluatePolicyRequest(BaseModel):
    """Request body for evaluating policies against a context."""

    library_name: str
    library_version: str = "1.0.0"
    target_files: list[str] = Field(default_factory=list)
    capabilities_used: list[str] = Field(default_factory=list)


class PolicyEvaluationResponse(BaseModel):
    """Response for policy evaluation results."""

    allowed: bool
    action: str
    matched_rules: list[dict] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class ApprovalRequestResponse(BaseModel):
    """Public representation of an approval request."""

    id: str
    library_name: str
    library_version: str
    requester_id: str
    policy_id: str
    reason: str = ""
    status: str = "pending"
    created_at: str = ""
    decided_at: str = ""
    decided_by: str = ""
    decision_comment: str = ""


class CreateApprovalRequest(BaseModel):
    """Request body for creating an approval request."""

    library_name: str
    library_version: str
    policy_id: str
    reason: str = ""


class ApprovalDecisionRequest(BaseModel):
    """Request body for approving or rejecting an approval request."""

    comment: str = ""


# ---------------------------------------------------------------------------
# LLM models
# ---------------------------------------------------------------------------


class LLMPreviewRequest(BaseModel):
    yaml_content: str
    format: str = "markdown"


class LLMPreviewResponse(BaseModel):
    preview: str
    tokens_used: int = 0
    cost_estimate: float = 0.0


class LLMEnrichRequest(BaseModel):
    yaml_content: str


class LLMEnrichResponse(BaseModel):
    enriched_yaml: str
    changes_summary: list[str] = Field(default_factory=list)
    tokens_used: int = 0
    cost_estimate: float = 0.0


class LLMSuggestGuardrailsRequest(BaseModel):
    yaml_content: str


class LLMSuggestGuardrailsResponse(BaseModel):
    guardrails: list[dict] = Field(default_factory=list)
    tokens_used: int = 0
    cost_estimate: float = 0.0


class LLMDescribeRequest(BaseModel):
    yaml_content: str


class LLMDescribeResponse(BaseModel):
    description: str
    tokens_used: int = 0
    cost_estimate: float = 0.0


class UsageRecordResponse(BaseModel):
    id: str
    model: str
    input_tokens: int
    output_tokens: int
    purpose: str
    cost_estimate: float
    timestamp: str


class UsageSummaryResponse(BaseModel):
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    record_count: int = 0
    records: list[UsageRecordResponse] = Field(default_factory=list)


class BudgetResponse(BaseModel):
    monthly_limit: float = 0.0
    alert_threshold_pct: float = 80.0
    current_month_cost: float = 0.0


class BudgetUpdateRequest(BaseModel):
    monthly_limit: float
    alert_threshold_pct: float = 80.0


class BudgetStatusResponse(BaseModel):
    allowed: bool = True
    remaining: float = 0.0
    percent_used: float = 0.0
    over_limit: bool = False
    monthly_limit: float = 0.0


class LLMStatusResponse(BaseModel):
    configured: bool
    model: str = ""
    message: str = ""


# ---------------------------------------------------------------------------
# Security & Audit models
# ---------------------------------------------------------------------------


class AuditEntryResponse(BaseModel):
    """A single audit log entry."""

    id: str
    timestamp: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    details: dict = Field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    success: bool = True


class AuditExportResponse(BaseModel):
    """Exported audit log content."""

    format: str
    content: str
    record_count: int = 0


# ---------------------------------------------------------------------------
# Webhook models
# ---------------------------------------------------------------------------


class WebhookResponse(BaseModel):
    """Public representation of a webhook."""

    id: str
    name: str
    url: str
    events: list[str] = Field(default_factory=list)
    active: bool = True
    created_at: str = ""
    updated_at: str = ""


class CreateWebhookRequest(BaseModel):
    """Request body for registering a webhook."""

    name: str
    url: str
    events: list[str] = Field(default_factory=list)
    secret: str = ""


class UpdateWebhookRequest(BaseModel):
    """Request body for updating a webhook."""

    name: str = ""
    url: str = ""
    events: list[str] = Field(default_factory=list)


class ToggleWebhookRequest(BaseModel):
    """Request body for toggling a webhook."""

    active: bool


class WebhookDeliveryResponse(BaseModel):
    """Record of a webhook delivery attempt."""

    id: str
    webhook_id: str
    event: str
    payload: dict = Field(default_factory=dict)
    response_status: int = 0
    response_body: str = ""
    success: bool = False
    delivered_at: str = ""
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# Plugin models
# ---------------------------------------------------------------------------


class PluginResponse(BaseModel):
    """Public representation of a plugin."""

    id: str
    name: str
    description: str = ""
    hooks: list[str] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)
    enabled: bool = True
    created_at: str = ""


class CreatePluginRequest(BaseModel):
    """Request body for registering a plugin."""

    name: str
    description: str = ""
    hooks: list[str] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)


class UpdatePluginRequest(BaseModel):
    """Request body for updating a plugin."""

    name: str = ""
    description: str = ""
    hooks: list[str] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)


class TogglePluginRequest(BaseModel):
    """Request body for toggling a plugin."""

    enabled: bool


# ---------------------------------------------------------------------------
# Security Dashboard
# ---------------------------------------------------------------------------


class SecurityDashboardResponse(BaseModel):
    """Aggregated security posture overview."""

    total_events: int = 0
    events_today: int = 0
    active_webhooks: int = 0
    total_webhooks: int = 0
    enabled_plugins: int = 0
    total_plugins: int = 0
    recent_events: list[AuditEntryResponse] = Field(default_factory=list)
    failed_deliveries_24h: int = 0
