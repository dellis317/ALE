"""Generator router -- YAML editor drafts, validation, enrichment, publishing, and hierarchical library generation."""

from __future__ import annotations

import json
import os
import re
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
    GeneratedLibraryResponse,
    GenerateHierarchicalLibraryRequest,
    GenerateHierarchicalLibraryResponse,
    LibraryDocNodeResponse,
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

# Hierarchical libraries storage directory
LIBRARIES_DIR = Path.home() / ".ale" / "libraries"

# Registry directory (same as used by the registry router)
REGISTRY_DIR = os.environ.get("ALE_REGISTRY_DIR", "/home/user/ALE/.ale_registry")


def _ensure_drafts_dir() -> Path:
    """Create the drafts directory if it does not exist."""
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    return DRAFTS_DIR


def _ensure_libraries_dir() -> Path:
    """Create the libraries directory if it does not exist."""
    LIBRARIES_DIR.mkdir(parents=True, exist_ok=True)
    return LIBRARIES_DIR


def _slugify(name: str) -> str:
    """Convert a name into a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name.lower().strip())
    slug = re.sub(r"[\s_-]+", "_", slug)
    return slug


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
# Enrich endpoint (delegates to LLM when configured, graceful fallback)
# ---------------------------------------------------------------------------

_llm_client = None


def _get_llm_client():
    """Lazy-init a shared LLMClient instance."""
    global _llm_client
    if _llm_client is None:
        from ale.llm.client import LLMClient

        _llm_client = LLMClient()
    return _llm_client


@router.post(
    "/enrich",
    response_model=EnrichResponse,
    summary="LLM enrichment on draft YAML",
)
async def enrich_yaml(request: EnrichRequest):
    """Apply LLM enrichment to a draft YAML.

    When an ANTHROPIC_API_KEY is configured, sends the YAML to the LLM for
    real enrichment.  Otherwise returns the original YAML unchanged with
    actionable suggestions so the user can still iterate.
    """
    if not request.yaml_content.strip():
        raise HTTPException(status_code=400, detail="yaml_content is required")

    client = _get_llm_client()

    if client.configured:
        from ale.llm.prompts import LIBRARY_ENRICHMENT_PROMPT
        from ale.llm.usage_tracker import UsageTracker

        prompt = LIBRARY_ENRICHMENT_PROMPT.format(yaml_content=request.yaml_content)
        resp = client.complete(prompt)

        # Track usage
        tracker = UsageTracker()
        tracker.record_usage(
            model=resp.model,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            purpose="enrich",
            cost_estimate=resp.cost_estimate,
        )

        enriched = resp.content
        # If the model prepended commentary, try to separate it
        if "---" in enriched:
            parts = enriched.split("---", 1)
            if len(parts) == 2 and len(parts[1].strip()) > len(parts[0].strip()):
                enriched = "---" + parts[1]

        return EnrichResponse(
            enriched_yaml=enriched,
            suggestions=[
                "LLM enrichment applied -- review changes before accepting",
            ],
        )

    # No LLM configured -- return original YAML with helpful suggestions
    return EnrichResponse(
        enriched_yaml=request.yaml_content,
        suggestions=[
            "LLM not configured (set ANTHROPIC_API_KEY for AI enrichment)",
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


# ---------------------------------------------------------------------------
# Hierarchical Library Generation
# ---------------------------------------------------------------------------


def _build_library_structure(
    name: str,
    slug: str,
    description: str,
    source_files: list[str],
    entry_points: list[str],
    tags: list[str],
    repo_path: str,
    candidate_name: str,
) -> LibraryDocNodeResponse:
    """Build a hierarchical document tree for a generated library.

    Structure:
    - <name>_library.md (root index/summary)
      - overview.md (detailed overview)
      - architecture.md (architecture & design)
      - instructions.md (implementation guide)
        - step_1_setup.md
        - step_2_core_logic.md
        - step_3_integration.md
      - guardrails.md (rules & constraints)
      - validation.md (testing criteria)
      - dependencies.md (external & internal deps)
      - versioning.md (version history & changelog)
      - audit_trail.md (provenance tracking)
      - security.md (security considerations)
      - variables.md (configuration & environment)
    """
    now = datetime.now(timezone.utc).isoformat()

    files_list = "\n".join(f"- `{f}`" for f in source_files[:30]) or "- *(none detected)*"
    ep_list = "\n".join(f"- `{ep}`" for ep in entry_points[:20]) or "- *(none detected)*"
    tags_inline = ", ".join(tags) if tags else "general"

    # Instruction sub-nodes
    instruction_children = [
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Step 1: Project Setup",
            slug=f"{slug}/instructions/step_1_setup",
            type="subsection",
            summary="Initialize the project structure and install dependencies.",
            content=f"""# Step 1: Project Setup

## Objective
Set up the foundational project structure for **{name}**.

## Actions
1. Create the project directory and initialize version control
2. Set up the dependency manifest (package.json, requirements.txt, etc.)
3. Configure linting, formatting, and pre-commit hooks
4. Establish the directory layout following the architecture guide

## Source Files Reference
{files_list}

## Notes
- Follow the target project's existing conventions for structure
- Reuse existing build tooling where available
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Step 2: Core Logic Implementation",
            slug=f"{slug}/instructions/step_2_core_logic",
            type="subsection",
            summary="Implement the primary business logic and data models.",
            content=f"""# Step 2: Core Logic Implementation

## Objective
Build the core functionality of **{name}**.

## Entry Points
{ep_list}

## Actions
1. Define data models and types
2. Implement primary functions/classes from the entry points above
3. Add internal error handling and logging
4. Write unit tests for each module

## Tags
{tags_inline}

## Notes
- Keep functions focused and composable
- Ensure type safety throughout
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Step 3: Integration & Wiring",
            slug=f"{slug}/instructions/step_3_integration",
            type="subsection",
            summary="Connect components, add API surfaces, and finalize exports.",
            content=f"""# Step 3: Integration & Wiring

## Objective
Wire up all components and expose the public API for **{name}**.

## Actions
1. Create the public API surface (exports, endpoints, CLI commands)
2. Integrate with external dependencies
3. Add integration tests
4. Document public interfaces

## Notes
- Verify all entry points are reachable
- Run the full test suite before marking complete
""",
            children=[],
        ),
    ]

    # Build the sections
    sections = [
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Overview",
            slug=f"{slug}/overview",
            type="section",
            summary=f"High-level overview of the {name} library.",
            content=f"""# {name} -- Overview

## Purpose
{description or 'A library extracted from the analyzed codebase.'}

## Scope
This library encapsulates the functionality identified in the **{candidate_name}** candidate from the repository at `{repo_path}`.

## Key Capabilities
{tags_inline}

## Source Files ({len(source_files)} total)
{files_list}

## Entry Points
{ep_list}

## When to Use
Use this library when you need the functionality provided by the {candidate_name} component. It is designed to be integrated into projects that share similar patterns and dependencies.
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Architecture",
            slug=f"{slug}/architecture",
            type="section",
            summary="Architecture and design patterns.",
            content=f"""# {name} -- Architecture

## Design Principles
- **Separation of concerns**: Each module handles a single responsibility
- **Composability**: Functions and classes are designed to be combined
- **Minimal dependencies**: Only essential external packages are used

## Module Structure
{files_list}

## Data Flow
1. Input enters through the defined entry points
2. Core logic processes the data through internal modules
3. Results are returned through the public API surface

## Dependencies
- External packages used by the source codebase
- Internal modules referenced across the component boundary
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Instructions",
            slug=f"{slug}/instructions",
            type="section",
            summary="Step-by-step implementation guide.",
            content=f"""# {name} -- Implementation Instructions

## Overview
This section provides a step-by-step guide for implementing the **{name}** library from the extracted component.

## Steps

| Step | Title | Description |
|------|-------|-------------|
| 1 | Project Setup | Initialize structure and dependencies |
| 2 | Core Logic | Implement primary business logic |
| 3 | Integration | Connect components and finalize API |

See each sub-document for detailed instructions.
""",
            children=instruction_children,
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Guardrails",
            slug=f"{slug}/guardrails",
            type="section",
            summary="Rules, constraints, and coding standards.",
            content=f"""# {name} -- Guardrails

## Mandatory Rules (MUST)
- **Follow existing code style**: Match the target project's formatting, naming conventions, and patterns
- **Error handling**: Include robust error handling appropriate to the target project's patterns
- **Type safety**: Maintain type annotations/hints consistent with the source

## Recommended Rules (SHOULD)
- **Reuse dependencies**: Use the target project's existing packages where possible
- **Documentation**: Add docstrings/comments for public APIs
- **Test coverage**: Aim for >80% coverage on core logic

## Optional Rules (MAY)
- Add performance benchmarks for hot paths
- Include usage examples in documentation
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Validation",
            slug=f"{slug}/validation",
            type="section",
            summary="Testing criteria and validation approach.",
            content=f"""# {name} -- Validation

## Test Strategy
1. **Unit tests**: Cover each function/class in isolation
2. **Integration tests**: Verify component interactions
3. **Conformance checks**: Run ALE conformance validation

## Acceptance Criteria
- All unit tests pass
- Integration tests cover primary workflows
- No schema or semantic validation errors
- Code style checks pass (linting, formatting)

## Test Approach
| Criterion | Method | Expected Result |
|-----------|--------|----------------|
| Core functionality | Unit tests | All tests pass |
| API contracts | Integration tests | Correct inputs/outputs |
| Error handling | Negative tests | Graceful failure |
| Performance | Benchmark (optional) | Within acceptable limits |
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Dependencies",
            slug=f"{slug}/dependencies",
            type="section",
            summary="External and internal dependency tracking.",
            content=f"""# {name} -- Dependencies

## External Dependencies
These are packages from the source codebase that this library relies on.
Review and include in your project's dependency manifest.

*(Populated from analysis of the source repository)*

## Internal Dependencies
Modules within the component that reference each other.

{files_list}

## Compatibility Targets
- Ensure compatibility with the target project's runtime environment
- Check version constraints for all external dependencies
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Versioning",
            slug=f"{slug}/versioning",
            type="section",
            summary="Version history, changelog, and release policy.",
            content=f"""# {name} -- Versioning

## Current Version
- **Version**: 1.0.0
- **Spec Version**: 1.0
- **Generated**: {now}

## Versioning Policy
This library follows [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes to the public API
- **MINOR**: New features, backward-compatible
- **PATCH**: Bug fixes, backward-compatible

## Changelog

### v1.0.0 ({now[:10]})
- Initial library generation from {candidate_name}
- Source repository: `{repo_path}`
- {len(source_files)} source files extracted
- {len(entry_points)} entry points identified
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Audit Trail",
            slug=f"{slug}/audit_trail",
            type="section",
            summary="Provenance tracking and generation history.",
            content=f"""# {name} -- Audit Trail

## Generation Provenance
| Field | Value |
|-------|-------|
| Generated At | {now} |
| Source Repository | `{repo_path}` |
| Candidate | {candidate_name} |
| Source Files | {len(source_files)} |
| Entry Points | {len(entry_points)} |
| Tags | {tags_inline} |

## Change Log
- **{now[:10]}**: Initial library generated from analyzer candidate "{candidate_name}"

## Compliance Notes
- This library was generated using ALE's automated analysis pipeline
- All source files were identified through static analysis
- Review the Security section for any flagged concerns
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Security",
            slug=f"{slug}/security",
            type="section",
            summary="Security considerations and threat model.",
            content=f"""# {name} -- Security

## Security Considerations
- **Input validation**: All public API inputs must be validated
- **Dependency audit**: Review external packages for known vulnerabilities
- **Secrets management**: Never hardcode credentials; use environment variables
- **Access control**: Respect the target project's auth/authz patterns

## Threat Model
| Threat | Mitigation |
|--------|-----------|
| Injection attacks | Input validation on all entry points |
| Dependency vulnerabilities | Regular dependency audits |
| Data leakage | Proper error message sanitization |
| Unauthorized access | Follow target project's access control |

## Recommendations
1. Run `npm audit` / `pip-audit` / equivalent before deployment
2. Enable dependabot or similar for automated security updates
3. Review the guardrails section for mandatory security rules
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Variables & Configuration",
            slug=f"{slug}/variables",
            type="section",
            summary="Environment variables and configuration reference.",
            content=f"""# {name} -- Variables & Configuration

## Environment Variables
Document all environment variables this library depends on:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| *(Add project-specific variables)* | | | |

## Configuration Files
List any configuration files needed:
- *(Add project-specific config files)*

## Runtime Settings
- **Logging level**: Inherit from the target project
- **Timeout values**: Use sensible defaults with override capability
- **Feature flags**: Document any toggleable behaviors

## Notes
- All configuration should be injectable (no hardcoded values)
- Provide reasonable defaults for all optional settings
- Document the expected format and valid ranges for each variable
""",
            children=[],
        ),
    ]

    # Build root node
    section_toc = "\n".join(
        f"| [{s.title}](./{slug}/{s.slug.split('/')[-1]}) | {s.summary} |"
        for s in sections
    )

    root = LibraryDocNodeResponse(
        id=str(uuid.uuid4()),
        title=f"{name} Library",
        slug=slug,
        type="root",
        summary=description or f"Agentic library generated from {candidate_name}.",
        content=f"""# {name} Library

> Auto-generated agentic library from the **{candidate_name}** analysis candidate.

## Summary
{description or 'A library extracted from the analyzed codebase.'}

## Source
- **Repository**: `{repo_path}`
- **Candidate**: {candidate_name}
- **Generated**: {now}
- **Version**: 1.0.0

## Structure

| Section | Description |
|---------|-------------|
{section_toc}

## Quick Start
1. Review the **Overview** to understand the library's purpose
2. Follow the **Instructions** step-by-step to implement
3. Check **Guardrails** for rules and constraints
4. Run **Validation** criteria to verify your implementation
5. Consult **Security** and **Variables** for deployment readiness

## Tags
{tags_inline}
""",
        children=sections,
    )

    return root


@router.post(
    "/library",
    response_model=GenerateHierarchicalLibraryResponse,
    summary="Generate a hierarchical library from an analysis candidate",
)
async def generate_hierarchical_library(request: GenerateHierarchicalLibraryRequest):
    """Generate a full hierarchical library document structure from an analysis candidate."""
    if not request.repo_path.strip():
        raise HTTPException(status_code=400, detail="repo_path is required")
    if not request.candidate_name.strip():
        raise HTTPException(status_code=400, detail="candidate_name is required")

    # Derive a display name
    raw_name = request.candidate_name
    if raw_name == "__whole_codebase__":
        # Use the repo directory name
        raw_name = Path(request.repo_path).name or "codebase"
    display_name = raw_name.replace("_", " ").replace("-", " ").title()
    slug = _slugify(raw_name) + "_library"

    structure = _build_library_structure(
        name=display_name,
        slug=slug,
        description=request.candidate_description,
        source_files=request.source_files,
        entry_points=request.entry_points,
        tags=request.tags,
        repo_path=request.repo_path,
        candidate_name=request.candidate_name,
    )

    now = datetime.now(timezone.utc).isoformat()
    library_id = str(uuid.uuid4())

    library = GeneratedLibraryResponse(
        id=library_id,
        name=display_name,
        root_doc=f"{slug}.md",
        repo_path=request.repo_path,
        candidate_name=request.candidate_name,
        created_at=now,
        updated_at=now,
        structure=structure,
    )

    # Persist to disk
    libs_dir = _ensure_libraries_dir()
    lib_path = libs_dir / f"{library_id}.json"
    with open(lib_path, "w") as f:
        json.dump(library.model_dump(), f, indent=2)

    return GenerateHierarchicalLibraryResponse(
        success=True,
        library=library,
        message=f"Library '{display_name}' generated successfully with {len(structure.children)} sections.",
    )


@router.get(
    "/libraries",
    response_model=list[GeneratedLibraryResponse],
    summary="List all generated hierarchical libraries",
)
async def list_generated_libraries():
    """List all generated hierarchical libraries, sorted by most recent."""
    libs_dir = _ensure_libraries_dir()
    libraries: list[dict] = []

    for lib_file in libs_dir.glob("*.json"):
        try:
            with open(lib_file) as f:
                lib = json.load(f)
            libraries.append(lib)
        except (json.JSONDecodeError, KeyError):
            continue

    libraries.sort(key=lambda d: d.get("updated_at", ""), reverse=True)
    return [GeneratedLibraryResponse(**lib) for lib in libraries]


@router.get(
    "/libraries/{library_id}",
    response_model=GeneratedLibraryResponse,
    summary="Get a specific generated library",
)
async def get_generated_library(library_id: str):
    """Retrieve a specific generated library by ID."""
    libs_dir = _ensure_libraries_dir()
    lib_path = libs_dir / f"{library_id}.json"

    if not lib_path.exists():
        raise HTTPException(status_code=404, detail=f"Library '{library_id}' not found")

    try:
        with open(lib_path) as f:
            lib = json.load(f)
    except (json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read library: {exc}")

    return GeneratedLibraryResponse(**lib)


@router.delete(
    "/libraries/{library_id}",
    summary="Delete a generated library",
)
async def delete_generated_library(library_id: str):
    """Delete a specific generated library by ID."""
    libs_dir = _ensure_libraries_dir()
    lib_path = libs_dir / f"{library_id}.json"

    if not lib_path.exists():
        raise HTTPException(status_code=404, detail=f"Library '{library_id}' not found")

    lib_path.unlink()
    return {"detail": "Library deleted"}
