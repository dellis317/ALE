"""Generator router -- YAML editor drafts, validation, enrichment, and publishing."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from ale.registry.local_registry import LocalRegistry
from ale.spec.schema_validator import validate_schema
from ale.spec.semantic_validator import validate_semantics

from web.backend.app.models.api import (
    DraftResponse,
    EnrichRequest,
    EnrichResponse,
    LibraryEntryResponse,
    PublishFromEditorRequest,
    QualitySignalsResponse,
    SaveDraftRequest,
    ValidateContentRequest,
    ValidateContentResponse,
    VerificationResultResponse,
)

router = APIRouter(prefix="/api/generate", tags=["generator"])

# ---------------------------------------------------------------------------
# Drafts storage directory
# ---------------------------------------------------------------------------
DRAFTS_DIR = Path.home() / ".ale" / "drafts"

# Registry directory (same as used by the registry router)
REGISTRY_DIR = os.environ.get("ALE_REGISTRY_DIR", "/home/user/ALE/.ale_registry")


def _ensure_drafts_dir() -> Path:
    """Create the drafts directory if it does not exist."""
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    return DRAFTS_DIR


def _get_registry() -> LocalRegistry:
    """Return a LocalRegistry instance for the configured directory."""
    return LocalRegistry(REGISTRY_DIR)


def _entry_to_response(entry) -> LibraryEntryResponse:
    """Convert a RegistryEntry dataclass to a Pydantic response model."""
    v = entry.quality.verification
    return LibraryEntryResponse(
        name=entry.name,
        version=entry.version,
        spec_version=entry.spec_version,
        description=entry.description,
        tags=entry.tags,
        capabilities=entry.capabilities,
        complexity=entry.complexity,
        language_agnostic=entry.language_agnostic,
        target_languages=entry.target_languages,
        quality=QualitySignalsResponse(
            verification=VerificationResultResponse(
                schema_passed=v.schema_passed,
                validator_passed=v.validator_passed,
                hooks_runnable=v.hooks_runnable,
                verified_at=v.verified_at,
                verified_by=v.verified_by,
            ),
            rating=entry.quality.rating,
            rating_count=entry.quality.rating_count,
            download_count=entry.quality.download_count,
            maintained=entry.quality.maintained,
            maintainer=entry.quality.maintainer,
            last_updated=entry.quality.last_updated,
        ),
        source_repo=entry.source_repo,
        library_path=entry.library_path,
        compatibility_targets=entry.compatibility_targets,
        qualified_id=entry.qualified_id,
        is_verified=entry.is_verified,
    )


# ---------------------------------------------------------------------------
# Enrich endpoint (LLM stub)
# ---------------------------------------------------------------------------


@router.post(
    "/enrich",
    response_model=EnrichResponse,
    summary="LLM enrichment on draft YAML",
)
async def enrich_yaml(request: EnrichRequest):
    """Apply LLM enrichment to a draft YAML.

    Currently returns the same YAML with a placeholder comment.
    """
    if not request.yaml_content.strip():
        raise HTTPException(status_code=400, detail="yaml_content is required")

    enriched = "# LLM enrichment placeholder\n" + request.yaml_content
    return EnrichResponse(
        enriched_yaml=enriched,
        suggestions=[
            "Consider adding more detailed instruction steps",
            "Add validation hooks for automated testing",
            "Include compatibility targets for popular frameworks",
        ],
    )


# ---------------------------------------------------------------------------
# Draft CRUD endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/save-draft",
    response_model=DraftResponse,
    summary="Save a work-in-progress draft",
)
async def save_draft(request: SaveDraftRequest):
    """Save a YAML draft to the local drafts directory."""
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    if not request.yaml_content.strip():
        raise HTTPException(status_code=400, detail="yaml_content is required")

    drafts_dir = _ensure_drafts_dir()
    now = datetime.now(timezone.utc).isoformat()

    draft = {
        "id": str(uuid.uuid4()),
        "name": request.name.strip(),
        "yaml_content": request.yaml_content,
        "created_at": now,
        "updated_at": now,
    }

    draft_path = drafts_dir / f"{draft['id']}.json"
    with open(draft_path, "w") as f:
        json.dump(draft, f, indent=2)

    return DraftResponse(**draft)


@router.get(
    "/drafts",
    response_model=list[DraftResponse],
    summary="List saved drafts",
)
async def list_drafts():
    """List all saved drafts, sorted by most recently updated."""
    drafts_dir = _ensure_drafts_dir()
    drafts: list[dict] = []

    for draft_file in drafts_dir.glob("*.json"):
        try:
            with open(draft_file) as f:
                draft = json.load(f)
            drafts.append(draft)
        except (json.JSONDecodeError, KeyError):
            continue

    # Sort by updated_at descending
    drafts.sort(key=lambda d: d.get("updated_at", ""), reverse=True)
    return [DraftResponse(**d) for d in drafts]


@router.get(
    "/drafts/{draft_id}",
    response_model=DraftResponse,
    summary="Get a specific draft",
)
async def get_draft(draft_id: str):
    """Retrieve a specific draft by ID."""
    drafts_dir = _ensure_drafts_dir()
    draft_path = drafts_dir / f"{draft_id}.json"

    if not draft_path.exists():
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found")

    try:
        with open(draft_path) as f:
            draft = json.load(f)
    except (json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read draft: {exc}")

    return DraftResponse(**draft)


@router.delete(
    "/drafts/{draft_id}",
    summary="Delete a draft",
)
async def delete_draft(draft_id: str):
    """Delete a specific draft by ID."""
    drafts_dir = _ensure_drafts_dir()
    draft_path = drafts_dir / f"{draft_id}.json"

    if not draft_path.exists():
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found")

    draft_path.unlink()
    return {"detail": "Draft deleted"}


# ---------------------------------------------------------------------------
# Validate endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/validate",
    response_model=ValidateContentResponse,
    summary="Validate YAML content without saving",
)
async def validate_content(request: ValidateContentRequest):
    """Run schema and semantic validation on raw YAML content.

    Returns errors and warnings without saving or publishing.
    """
    if not request.yaml_content.strip():
        return ValidateContentResponse(
            valid=False,
            schema_errors=["YAML content is empty"],
        )

    # Parse the YAML
    try:
        data = yaml.safe_load(request.yaml_content)
    except yaml.YAMLError as exc:
        return ValidateContentResponse(
            valid=False,
            schema_errors=[f"YAML parse error: {exc}"],
        )

    if not isinstance(data, dict):
        return ValidateContentResponse(
            valid=False,
            schema_errors=["YAML must be a mapping (object) at the top level"],
        )

    # Gate 1: Schema validation
    schema_errors = validate_schema(data)

    # Gate 2: Semantic validation
    sem_result = validate_semantics(data)
    semantic_errors = [
        f"[{issue.code}] {issue.path}: {issue.message}"
        for issue in sem_result.errors
    ]
    semantic_warnings = [
        f"[{issue.code}] {issue.path}: {issue.message}"
        for issue in sem_result.warnings
    ]

    valid = len(schema_errors) == 0 and len(semantic_errors) == 0

    return ValidateContentResponse(
        valid=valid,
        schema_errors=schema_errors,
        semantic_errors=semantic_errors,
        semantic_warnings=semantic_warnings,
    )


# ---------------------------------------------------------------------------
# Publish endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/publish",
    response_model=LibraryEntryResponse,
    summary="Validate and publish from editor content",
)
async def publish_from_editor(request: PublishFromEditorRequest):
    """Validate the YAML content, then publish it to the registry.

    The YAML is first validated (schema + semantic). If validation fails,
    a 400 error is returned with details. On success, the library is
    published to the local registry.
    """
    if not request.yaml_content.strip():
        raise HTTPException(status_code=400, detail="yaml_content is required")

    # Parse the YAML
    try:
        data = yaml.safe_load(request.yaml_content)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=400, detail=f"YAML parse error: {exc}"
        )

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=400,
            detail="YAML must be a mapping (object) at the top level",
        )

    # Validate
    schema_errors = validate_schema(data)
    sem_result = validate_semantics(data)
    semantic_errors = [
        f"[{issue.code}] {issue.path}: {issue.message}"
        for issue in sem_result.errors
    ]

    if schema_errors or semantic_errors:
        all_errors = schema_errors + semantic_errors
        raise HTTPException(
            status_code=400,
            detail=f"Validation failed: {'; '.join(all_errors)}",
        )

    # Write to a temp file and publish
    lib = data.get("agentic_library", {})
    manifest = lib.get("manifest", {})
    name = request.name or manifest.get("name", "untitled")

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".agentic.yaml",
        prefix=f"ale_{name}_",
        mode="w",
    ) as tmp:
        tmp.write(request.yaml_content)
        tmp_path = tmp.name

    try:
        reg = _get_registry()
        entry = reg.publish(tmp_path)
        return _entry_to_response(entry)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
