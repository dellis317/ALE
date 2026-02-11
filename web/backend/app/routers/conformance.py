"""Conformance router -- schema validation, semantic validation, and full 3-gate pipeline."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

import yaml

from ale.spec.schema import get_schema
from ale.spec.schema_validator import validate_schema
from ale.spec.semantic_validator import validate_semantics
from ale.spec.reference_runner import ReferenceRunner

from web.backend.app.models.api import (
    ConformanceRequest,
    ConformanceResponse,
    HookResultResponse,
    SchemaResponse,
    ValidateResponse,
    ValidationIssueResponse,
)

router = APIRouter(tags=["conformance"])


@router.post(
    "/api/conformance/run",
    response_model=ConformanceResponse,
    summary="Run full 3-gate conformance pipeline",
)
async def run_conformance(request: ConformanceRequest):
    """Execute the full conformance pipeline (schema + semantic + hooks).

    Runs all three gates of the executable specification against the
    library file at the given path.
    """
    try:
        runner = ReferenceRunner(working_dir=request.working_dir)
        result = runner.run(request.library_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Library file not found: {request.library_path}",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    hook_responses = [
        HookResultResponse(
            description=h.description,
            hook_type=h.hook_type,
            passed=h.passed,
            exit_code=h.exit_code,
            stdout=h.stdout,
            stderr=h.stderr,
            duration_ms=h.duration_ms,
            error=h.error,
        )
        for h in result.hook_results
    ]

    return ConformanceResponse(
        library_name=result.library_name,
        library_version=result.library_version,
        spec_version=result.spec_version,
        schema_passed=result.schema_passed,
        semantic_passed=result.semantic_passed,
        all_passed=result.all_passed,
        hooks_passed=result.hooks_passed,
        schema_errors=result.schema_errors,
        semantic_errors=result.semantic_errors,
        semantic_warnings=result.semantic_warnings,
        hook_results=hook_responses,
        total_duration_ms=result.total_duration_ms,
    )


@router.post(
    "/api/conformance/validate",
    response_model=ValidateResponse,
    summary="Run schema + semantic validation only",
)
async def validate_only(request: ConformanceRequest):
    """Run schema and semantic validation without executing hooks.

    This is faster and safer when you only need structural and semantic
    checks without running arbitrary shell commands.
    """
    from pathlib import Path

    path = Path(request.library_path)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Library file not found: {request.library_path}",
        )

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"Failed to parse YAML: {exc}"
        )

    # Gate 1: Schema
    schema_errors = validate_schema(data)
    schema_passed = len(schema_errors) == 0

    # Gate 2: Semantics
    sem_result = validate_semantics(data)

    issues = [
        ValidationIssueResponse(
            severity=issue.severity.value,
            code=issue.code,
            message=issue.message,
            path=issue.path,
        )
        for issue in sem_result.issues
    ]

    return ValidateResponse(
        schema_passed=schema_passed,
        schema_errors=schema_errors,
        semantic_passed=sem_result.passed,
        semantic_issues=issues,
        summary=sem_result.summary(),
    )


@router.get(
    "/api/schema",
    response_model=SchemaResponse,
    summary="Get the Agentic Library JSON Schema",
)
async def get_ale_schema():
    """Return the canonical JSON Schema for Agentic Library files."""
    schema = get_schema()
    return SchemaResponse(schema=schema)
