"""Distribution router -- consumer-facing API for agents pulling ALE libraries.

This router serves rendered build plans (markdown) and metadata to consuming
agents (Claude Code, Cursor, Copilot, etc.) that want to use ALE libraries
to implement features in their target projects.

All endpoints require API key authentication via X-API-Key header.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ale.auth.models import User
from ale.registry.local_registry import LocalRegistry, _dict_to_entry, generate_library_id
from ale.registry.models import SearchQuery
from web.backend.app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1", tags=["distribution"])

# Configurable registry directory; default to project-level .ale_registry
REGISTRY_DIR = os.environ.get("ALE_REGISTRY_DIR", "/home/user/ALE/.ale_registry")


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class LibrarySummary(BaseModel):
    """Lightweight library info for search results."""

    library_id: str
    name: str
    version: str
    description: str = ""
    complexity: str = ""
    tags: list[str] = Field(default_factory=list)
    is_verified: bool = False


class SearchResponse(BaseModel):
    """Search results for distribution."""

    results: list[LibrarySummary] = Field(default_factory=list)
    total: int = 0
    query: str = ""


class PullResponse(BaseModel):
    """Full library pull response -- contains the rendered build plan."""

    library_id: str
    name: str
    version: str
    build_plan_md: str  # The full rendered markdown build plan
    readme_md: str  # The README for the library folder
    downloaded_at: str = ""


class VersionsResponse(BaseModel):
    """All available libraries in the registry."""

    libraries: list[LibrarySummary] = Field(default_factory=list)
    total: int = 0
    updated_at: str = ""


class LibraryInfoResponse(BaseModel):
    """Detailed metadata about a library."""

    library_id: str
    name: str
    latest_version: str
    all_versions: list[str] = Field(default_factory=list)
    description: str = ""
    complexity: str = ""
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    is_verified: bool = False
    language_agnostic: bool = True


class InitResponse(BaseModel):
    """Consumer scaffold templates."""

    agent_instructions_md: str
    ale_env_template: str
    versions_md_template: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_registry() -> LocalRegistry:
    """Return a LocalRegistry instance for the configured directory."""
    return LocalRegistry(REGISTRY_DIR)


def _entry_to_summary(entry) -> LibrarySummary:
    """Convert a RegistryEntry to a lightweight LibrarySummary."""
    library_id = entry.library_id or generate_library_id(entry.name)
    return LibrarySummary(
        library_id=library_id,
        name=entry.name,
        version=entry.version,
        description=entry.description,
        complexity=entry.complexity,
        tags=entry.tags,
        is_verified=entry.is_verified,
    )


def _find_entry_by_library_id(
    reg: LocalRegistry, library_id: str, version: str = "",
) -> Optional[object]:
    """Find a registry entry by its library_id (ale_XXXXXXXX).

    If *version* is provided, only return that specific version.
    Otherwise return the latest version found.
    """
    candidates = []
    for data in reg._index.values():
        entry = _dict_to_entry(data)
        entry_lid = entry.library_id or generate_library_id(entry.name)
        if entry_lid == library_id:
            if version and entry.version != version:
                continue
            candidates.append(entry)

    if not candidates:
        return None

    # Return the latest version (simple alphabetical sort on version string)
    return sorted(candidates, key=lambda e: e.version)[-1]


def _load_yaml_data(library_path: str) -> dict:
    """Load and return the parsed YAML data from a library file."""
    if not library_path or not os.path.isfile(library_path):
        raise HTTPException(
            status_code=404,
            detail=f"Library YAML file not found at: {library_path}",
        )
    with open(library_path) as f:
        return yaml.safe_load(f)


def _render_build_plan(yaml_data: dict, library_id: str) -> str:
    """Render a YAML library spec into a markdown build plan.

    Attempts to use ``ale.distribution.renderer.render_build_plan`` if
    available; otherwise falls back to a built-in renderer.
    """
    try:
        from ale.distribution.renderer import render_build_plan
        return render_build_plan(yaml_data, library_id)
    except (ImportError, ModuleNotFoundError):
        return _fallback_render_build_plan(yaml_data, library_id)


def _fallback_render_build_plan(yaml_data: dict, library_id: str) -> str:
    """Built-in markdown renderer for when the distribution renderer is
    not yet installed."""
    lib = yaml_data.get("agentic_library", {})
    manifest = lib.get("manifest", {})
    name = manifest.get("name", "Unknown Library")
    version = manifest.get("version", "0.0.0")
    description = manifest.get("description", "")
    complexity = manifest.get("complexity", "")

    lines = [
        f"# {name} -- Build Plan",
        "",
        f"**Library ID:** `{library_id}`",
        f"**Version:** {version}",
    ]
    if complexity:
        lines.append(f"**Complexity:** {complexity}")
    if description:
        lines += ["", f"> {description}"]

    # Implementation steps
    impl = lib.get("implementation", {})
    steps = impl.get("steps", [])
    if steps:
        lines += ["", "## Implementation Steps", ""]
        for i, step in enumerate(steps, 1):
            step_title = step.get("title", step.get("description", f"Step {i}"))
            lines.append(f"### Step {i}: {step_title}")
            if step.get("description"):
                lines.append(f"\n{step['description']}")
            instructions = step.get("instructions", [])
            if instructions:
                lines.append("")
                for instr in instructions:
                    if isinstance(instr, str):
                        lines.append(f"- {instr}")
                    elif isinstance(instr, dict):
                        lines.append(f"- {instr.get('action', instr.get('description', str(instr)))}")
            files = step.get("files", [])
            if files:
                lines.append("\n**Files:**")
                for fobj in files:
                    if isinstance(fobj, str):
                        lines.append(f"- `{fobj}`")
                    elif isinstance(fobj, dict):
                        path = fobj.get("path", fobj.get("file", ""))
                        lines.append(f"- `{path}`")
                        content = fobj.get("content", "")
                        if content:
                            lines.append(f"\n```\n{content}\n```")
            lines.append("")

    # Validation / verification hooks
    validation = lib.get("validation", [])
    if validation:
        lines += ["## Validation", ""]
        for v in validation:
            desc = v.get("description", "")
            hook = v.get("hook", "")
            if desc:
                lines.append(f"- {desc}")
            if hook:
                lines.append(f"  - Hook: `{hook}`")
        lines.append("")

    # Guardrails
    guardrails = lib.get("guardrails", [])
    if guardrails:
        lines += ["## Guardrails", ""]
        for g in guardrails:
            if isinstance(g, str):
                lines.append(f"- {g}")
            elif isinstance(g, dict):
                lines.append(f"- {g.get('description', g.get('rule', str(g)))}")
        lines.append("")

    return "\n".join(lines)


def _generate_readme(yaml_data: dict, library_id: str, version: str, downloaded_at: str) -> str:
    """Generate a README for the library.

    Attempts to use ``ale.distribution.readme_generator.generate_library_readme``
    if available; otherwise falls back to a built-in generator.
    """
    try:
        from ale.distribution.readme_generator import generate_library_readme
        return generate_library_readme(yaml_data, library_id, version, downloaded_at)
    except (ImportError, ModuleNotFoundError):
        return _fallback_generate_readme(yaml_data, library_id, version, downloaded_at)


def _fallback_generate_readme(yaml_data: dict, library_id: str, version: str, downloaded_at: str) -> str:
    """Built-in README generator for when the distribution readme_generator is
    not yet installed."""
    lib = yaml_data.get("agentic_library", {})
    manifest = lib.get("manifest", {})
    name = manifest.get("name", "Unknown Library")
    description = manifest.get("description", "")
    tags = manifest.get("tags", [])
    complexity = manifest.get("complexity", "")

    lines = [
        f"# {name}",
        "",
        f"**Library ID:** `{library_id}`  ",
        f"**Version:** {version}  ",
        f"**Downloaded:** {downloaded_at}  ",
    ]
    if complexity:
        lines.append(f"**Complexity:** {complexity}  ")
    if tags:
        lines.append(f"**Tags:** {', '.join(tags)}  ")
    if description:
        lines += ["", description]

    lines += [
        "",
        "## Usage",
        "",
        "This library was pulled from the ALE registry. Follow the build plan",
        "in the accompanying markdown file to implement this library in your",
        "target project.",
        "",
        "See `AGENT_INSTRUCTIONS.md` in the consumer root for the full workflow.",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Static template content for /init
# ---------------------------------------------------------------------------

_AGENT_INSTRUCTIONS_MD = """\
# ALE Consumer -- Agent Instructions

You are integrating ALE (Agentic Library Exchange) libraries into a target project.

## Workflow

1. **Search** for libraries that match the capability you need:
   ```
   GET /api/v1/search?text=<description>&tags=<comma-separated>
   ```

2. **Pull** the library build plan:
   ```
   GET /api/v1/pull/<library_id>
   ```

3. **Read the build plan** (`build_plan_md`) carefully. It contains:
   - Step-by-step implementation instructions
   - File contents to create or modify
   - Validation hooks to run after implementation

4. **Implement** each step in order, creating/modifying files in the target project.

5. **Validate** by running any provided hooks or test commands.

6. **Record provenance** in your `ALE.env` file so drift detection works later.

## Rules

- Always follow the build plan steps in order.
- Do not skip validation steps.
- Record every library you apply in `ALE.env`.
- If a step fails, stop and report the error -- do not continue blindly.
"""

_ALE_ENV_TEMPLATE = """\
# ALE Environment Configuration
# This file tracks which ALE libraries have been applied to this project.
# Do not edit manually -- managed by the ALE consumer agent.

ALE_CONSUMER_VERSION=1.0.0
ALE_REGISTRY_URL=

# Applied libraries (one per line: LIBRARY_ID=VERSION@TIMESTAMP)
# Example:
# ale_a1b2c3d4=1.0.0@2025-01-01T00:00:00Z
"""

_VERSIONS_MD_TEMPLATE = """\
# ALE Library Versions

> Auto-generated manifest of ALE libraries applied to this project.

| Library ID | Name | Version | Applied At |
|------------|------|---------|------------|
<!-- ALE_VERSIONS_TABLE -->
"""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Search for libraries by description/capability",
)
async def search_libraries(
    text: Optional[str] = Query(None, description="Free-text search"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    capabilities: Optional[str] = Query(
        None, description="Comma-separated capabilities"
    ),
    verified_only: bool = Query(False, description="Only verified libraries"),
    min_rating: float = Query(0.0, description="Minimum quality rating"),
    user: User = Depends(get_current_user),
):
    """Search the ALE registry for libraries matching the given criteria.

    Returns lightweight ``LibrarySummary`` objects suitable for agent
    consumption. Use the ``library_id`` from the results to pull the full
    build plan via ``/api/v1/pull/{library_id}``.
    """
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

    summaries = [_entry_to_summary(e) for e in result.entries]
    return SearchResponse(
        results=summaries,
        total=result.total_count,
        query=text or "",
    )


@router.get(
    "/pull/{library_id}/{version}",
    response_model=PullResponse,
    summary="Pull a specific version of a library as a rendered build plan",
)
async def pull_library_version(
    library_id: str,
    version: str,
    user: User = Depends(get_current_user),
):
    """Pull a specific version of an ALE library.

    Returns the fully rendered markdown build plan and README that a
    consuming agent can follow step-by-step to implement the library in
    a target project.
    """
    reg = _get_registry()
    entry = _find_entry_by_library_id(reg, library_id, version=version)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Library '{library_id}@{version}' not found in registry",
        )

    yaml_data = _load_yaml_data(entry.library_path)
    now = datetime.now(timezone.utc).isoformat()

    build_plan = _render_build_plan(yaml_data, library_id)
    readme = _generate_readme(yaml_data, library_id, entry.version, now)

    # Best-effort increment download count
    _try_increment_download(reg, entry)

    return PullResponse(
        library_id=library_id,
        name=entry.name,
        version=entry.version,
        build_plan_md=build_plan,
        readme_md=readme,
        downloaded_at=now,
    )


@router.get(
    "/pull/{library_id}",
    response_model=PullResponse,
    summary="Pull the latest version of a library as a rendered build plan",
)
async def pull_library_latest(
    library_id: str,
    user: User = Depends(get_current_user),
):
    """Pull the latest version of an ALE library.

    Returns the fully rendered markdown build plan and README that a
    consuming agent can follow step-by-step to implement the library in
    a target project.
    """
    reg = _get_registry()
    entry = _find_entry_by_library_id(reg, library_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Library '{library_id}' not found in registry",
        )

    yaml_data = _load_yaml_data(entry.library_path)
    now = datetime.now(timezone.utc).isoformat()

    build_plan = _render_build_plan(yaml_data, library_id)
    readme = _generate_readme(yaml_data, library_id, entry.version, now)

    # Best-effort increment download count
    _try_increment_download(reg, entry)

    return PullResponse(
        library_id=library_id,
        name=entry.name,
        version=entry.version,
        build_plan_md=build_plan,
        readme_md=readme,
        downloaded_at=now,
    )


@router.get(
    "/versions",
    response_model=VersionsResponse,
    summary="Get the full versions manifest of all available libraries",
)
async def list_versions(
    user: User = Depends(get_current_user),
):
    """Return every library in the registry as lightweight summaries.

    This is the full catalog -- consuming agents can use it to browse what
    is available before pulling specific libraries.
    """
    reg = _get_registry()
    entries = reg.list_all()
    summaries = [_entry_to_summary(e) for e in entries]

    return VersionsResponse(
        libraries=summaries,
        total=len(summaries),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/library/{library_id}/info",
    response_model=LibraryInfoResponse,
    summary="Get metadata about a library",
)
async def library_info(
    library_id: str,
    user: User = Depends(get_current_user),
):
    """Return detailed metadata for a library identified by its library_id.

    Includes all available versions, capabilities, tags, and verification
    status.
    """
    reg = _get_registry()

    # Collect all versions for this library_id
    all_entries = []
    for data in reg._index.values():
        entry = _dict_to_entry(data)
        entry_lid = entry.library_id or generate_library_id(entry.name)
        if entry_lid == library_id:
            all_entries.append(entry)

    if not all_entries:
        raise HTTPException(
            status_code=404,
            detail=f"Library '{library_id}' not found in registry",
        )

    # Sort by version; latest is last
    all_entries.sort(key=lambda e: e.version)
    latest = all_entries[-1]

    return LibraryInfoResponse(
        library_id=library_id,
        name=latest.name,
        latest_version=latest.version,
        all_versions=[e.version for e in all_entries],
        description=latest.description,
        complexity=latest.complexity,
        tags=latest.tags,
        capabilities=latest.capabilities,
        is_verified=latest.is_verified,
        language_agnostic=latest.language_agnostic,
    )


@router.post(
    "/init",
    response_model=InitResponse,
    summary="Get consumer scaffold templates",
)
async def init_consumer(
    user: User = Depends(get_current_user),
):
    """Return the standard ALE consumer scaffold templates.

    These templates help a consuming agent set up the target project for
    ALE library integration:

    - **agent_instructions_md** -- instructions for the agent on the ALE workflow
    - **ale_env_template** -- the ``ALE.env`` tracking file template
    - **versions_md_template** -- the ``VERSIONS.md`` table template
    """
    return InitResponse(
        agent_instructions_md=_AGENT_INSTRUCTIONS_MD,
        ale_env_template=_ALE_ENV_TEMPLATE,
        versions_md_template=_VERSIONS_MD_TEMPLATE,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _try_increment_download(reg: LocalRegistry, entry) -> None:
    """Best-effort increment of the download_count for a registry entry.

    Silently ignores errors so that a pull always succeeds even if the
    counter update fails.
    """
    try:
        key = entry.qualified_id
        if key in reg._index:
            quality = reg._index[key].setdefault("quality", {})
            count = quality.get("download_count", 0)
            quality["download_count"] = count + 1
            reg._save_index()
    except Exception:
        pass
