"""Conformance router -- schema validation, semantic validation, and full 3-gate pipeline."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

import yaml

from ale.spec.schema import get_schema
from ale.spec.schema_validator import validate_schema
from ale.spec.semantic_validator import validate_semantics
from ale.spec.reference_runner import ReferenceRunner
from ale.spec.conformance_history import ConformanceHistoryStore

from web.backend.app.models.api import (
    BatchConformanceResult,
    ConformanceHistoryEntry as ConformanceHistoryEntryResponse,
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

    # Record in conformance history
    try:
        history_store = ConformanceHistoryStore()
        history_store.record_run(result.library_name, result)
    except Exception:
        pass  # Don't fail the response if history recording fails

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


@router.get(
    "/api/conformance/history",
    response_model=list[ConformanceHistoryEntryResponse],
    summary="Get past conformance runs for a library",
)
async def conformance_history(library_name: str = Query(...)):
    """Get past conformance runs for a library.

    Reads from the conformance history store in ~/.ale/conformance_history/.
    """
    try:
        store = ConformanceHistoryStore()
        entries = store.get_history(library_name)
        return [
            ConformanceHistoryEntryResponse(
                library_name=e.library_name,
                library_version=e.library_version,
                ran_at=e.ran_at,
                all_passed=e.all_passed,
                schema_passed=e.schema_passed,
                semantic_passed=e.semantic_passed,
                hooks_passed=e.hooks_passed,
                total_duration_ms=e.total_duration_ms,
            )
            for e in entries
        ]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/api/conformance/batch",
    response_model=BatchConformanceResult,
    summary="Run conformance on all registry libraries",
)
async def conformance_batch():
    """Run conformance on all libraries in the registry.

    Gets all libraries from the registry, runs conformance on each,
    and returns aggregated results.
    """
    import os
    from ale.registry.local_registry import LocalRegistry

    registry_dir = os.environ.get(
        "ALE_REGISTRY_DIR", "/home/user/ALE/.ale_registry"
    )
    reg = LocalRegistry(registry_dir)
    all_entries = reg.list_all()

    results = []
    passed_count = 0
    failed_count = 0
    history_store = ConformanceHistoryStore()

    for entry in all_entries:
        if not entry.library_path:
            continue
        try:
            runner = ReferenceRunner(working_dir=".")
            result = runner.run(entry.library_path)

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

            resp = ConformanceResponse(
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
            results.append(resp)

            # Record in history
            history_store.record_run(result.library_name, result)

            if result.all_passed:
                passed_count += 1
            else:
                failed_count += 1
        except Exception:
            failed_count += 1

    return BatchConformanceResult(
        total=len(results) + (failed_count - (len(results) - passed_count)),
        passed=passed_count,
        failed=failed_count,
        results=results,
    )
