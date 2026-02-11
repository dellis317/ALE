"""Registry router -- CRUD and search for Agentic Libraries."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File

from ale.registry.local_registry import LocalRegistry
from ale.registry.models import SearchQuery

from app.models.api import (
    LibraryEntryResponse,
    QualitySignalsResponse,
    SearchQueryRequest,
    SearchResultResponse,
    VerificationResultResponse,
)

router = APIRouter(prefix="/api/registry", tags=["registry"])

# Configurable registry directory; default to project-level .ale_registry
REGISTRY_DIR = os.environ.get(
    "ALE_REGISTRY_DIR", "/home/user/ALE/.ale_registry"
)


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


@router.get(
    "",
    response_model=list[LibraryEntryResponse],
    summary="List all libraries",
)
async def list_libraries():
    """List every library in the registry."""
    reg = _get_registry()
    entries = reg.list_all()
    return [_entry_to_response(e) for e in entries]


@router.get(
    "/search",
    response_model=SearchResultResponse,
    summary="Search libraries",
)
async def search_libraries(
    text: Optional[str] = Query(None, description="Free-text search"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    capabilities: Optional[str] = Query(
        None, description="Comma-separated capabilities"
    ),
    verified_only: bool = Query(False, description="Only verified libraries"),
    min_rating: float = Query(0.0, description="Minimum quality rating"),
):
    """Search the registry with optional filters."""
    reg = _get_registry()
    query = SearchQuery(
        text=text or "",
        tags=[t.strip() for t in tags.split(",")] if tags else [],
        capabilities=[c.strip() for c in capabilities.split(",")]
        if capabilities
        else [],
        verified_only=verified_only,
        min_rating=min_rating,
    )
    result = reg.search(query)

    return SearchResultResponse(
        entries=[_entry_to_response(e) for e in result.entries],
        total_count=result.total_count,
        query=SearchQueryRequest(
            text=query.text,
            tags=query.tags,
            capabilities=query.capabilities,
            verified_only=query.verified_only,
            min_rating=query.min_rating,
        ),
    )


@router.get(
    "/{name}",
    response_model=LibraryEntryResponse,
    summary="Get latest version of a library",
)
async def get_library(name: str):
    """Retrieve the latest version of a library by name."""
    reg = _get_registry()
    entry = reg.get(name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Library '{name}' not found")
    return _entry_to_response(entry)


@router.get(
    "/{name}/{version}",
    response_model=LibraryEntryResponse,
    summary="Get a specific version of a library",
)
async def get_library_version(name: str, version: str):
    """Retrieve a specific version of a library."""
    reg = _get_registry()
    entry = reg.get(name, version)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Library '{name}@{version}' not found",
        )
    return _entry_to_response(entry)


@router.post(
    "/publish",
    response_model=LibraryEntryResponse,
    summary="Publish a library",
)
async def publish_library(file: UploadFile = File(...)):
    """Publish an Agentic Library from an uploaded YAML file.

    Accepts a multipart file upload of an ``.agentic.yaml`` file. The file
    is saved to a temporary location, published to the local registry, and
    the resulting entry is returned.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Save uploaded file to a temp location
    suffix = Path(file.filename).suffix or ".yaml"
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix, prefix="ale_upload_"
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        reg = _get_registry()
        entry = reg.publish(tmp_path)
        return _entry_to_response(entry)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)
