"""Drift and provenance router -- drift detection and provenance history."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ale.sync.drift import DriftDetector
from ale.sync.provenance import ProvenanceStore

from app.models.api import (
    DriftCheckAllRequest,
    DriftCheckRequest,
    DriftReportResponse,
    ProvenanceRecordResponse,
)

router = APIRouter(tags=["drift"])


def _drift_report_to_response(report) -> DriftReportResponse:
    """Convert a DriftReport dataclass to a Pydantic response."""
    return DriftReportResponse(
        library_name=report.library_name,
        applied_version=report.applied_version,
        latest_version=report.latest_version,
        drift_types=report.drift_types,
        details=report.details,
        has_drift=report.has_drift,
        validation_still_passes=report.validation_still_passes,
    )


def _provenance_to_response(record) -> ProvenanceRecordResponse:
    """Convert a ProvenanceRecord dataclass to a Pydantic response."""
    return ProvenanceRecordResponse(
        library_name=record.library_name,
        library_version=record.library_version,
        applied_at=record.applied_at,
        applied_by=record.applied_by,
        target_repo=record.target_repo,
        target_branch=record.target_branch,
        validation_passed=record.validation_passed,
        validation_evidence=record.validation_evidence,
        commit_sha=record.commit_sha,
    )


@router.post(
    "/api/drift/check",
    response_model=DriftReportResponse,
    summary="Check drift for a specific library",
)
async def check_drift(request: DriftCheckRequest):
    """Check whether a specific library has drifted in the given repo.

    Drift can be version-based (newer library available) or validation-based
    (hooks no longer pass against the current repo state).
    """
    if not request.repo_path or not request.library_name:
        raise HTTPException(
            status_code=400,
            detail="repo_path and library_name are required",
        )

    try:
        detector = DriftDetector(request.repo_path)
        report = detector.check(
            library_name=request.library_name,
            latest_version=request.latest_version,
            library_path=request.library_path,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _drift_report_to_response(report)


@router.post(
    "/api/drift/check-all",
    response_model=list[DriftReportResponse],
    summary="Check drift for all libraries in a repo",
)
async def check_all_drift(request: DriftCheckAllRequest):
    """Check drift for every library that has a provenance record in the repo."""
    if not request.repo_path:
        raise HTTPException(status_code=400, detail="repo_path is required")

    try:
        detector = DriftDetector(request.repo_path)
        reports = detector.check_all()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return [_drift_report_to_response(r) for r in reports]


@router.get(
    "/api/provenance/{repo_path:path}",
    response_model=list[ProvenanceRecordResponse],
    summary="Get all provenance records for a repo",
)
async def get_provenance_history(repo_path: str):
    """Retrieve all provenance records for the given repository path."""
    try:
        store = ProvenanceStore(repo_path)
        records = store.get_history()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return [_provenance_to_response(r) for r in records]


@router.get(
    "/api/provenance/{repo_path:path}/{library_name}",
    response_model=list[ProvenanceRecordResponse],
    summary="Get provenance records for a specific library",
)
async def get_library_provenance(repo_path: str, library_name: str):
    """Retrieve provenance records for a specific library in the given repo."""
    try:
        store = ProvenanceStore(repo_path)
        records = store.get_history(library_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return [_provenance_to_response(r) for r in records]
