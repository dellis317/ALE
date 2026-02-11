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
