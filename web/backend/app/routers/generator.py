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
    CreateFromLatestRequest,
    DraftResponse,
    EnrichRequest,
    EnrichResponse,
    FileChangeResponse,
    GeneratedLibraryResponse,
    GenerateHierarchicalLibraryRequest,
    GenerateHierarchicalLibraryResponse,
    LibraryDocNodeResponse,
    LibraryEntryResponse,
    PublishFromEditorRequest,
    QualitySignalsResponse,
    SaveDraftRequest,
    UpdateCheckResponse,
    UpdateLibraryRequest,
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


def _analyze_source_code(
    repo_path: str,
    source_files: list[str],
) -> dict:
    """Read source files and extract meaningful code structure for instructions.

    Returns a dict with:
    - classes: list of {name, methods, docstring, file}
    - functions: list of {name, params, docstring, file}
    - imports: list of external package names
    - patterns: list of detected design patterns/frameworks
    - code_sketch: pseudocode summary of what the code does
    """
    classes: list[dict] = []
    functions: list[dict] = []
    imports: set[str] = set()
    patterns: list[str] = []

    repo_root = Path(repo_path)

    for rel_path in source_files[:30]:
        # Resolve: source_files should be relative paths
        abs_path = repo_root / rel_path
        if not abs_path.exists():
            # Try as absolute path (backwards compat)
            abs_path = Path(rel_path)
        if not abs_path.exists() or not abs_path.is_file():
            continue

        try:
            content = abs_path.read_text(errors="replace")
        except Exception:
            continue

        suffix = abs_path.suffix.lower()

        # Extract function/class signatures based on language
        for line in content.splitlines():
            stripped = line.strip()

            # Python
            if suffix == ".py":
                if stripped.startswith("import ") or stripped.startswith("from "):
                    pkg = stripped.split()[1].split(".")[0]
                    if not pkg.startswith("_"):
                        imports.add(pkg)
                if stripped.startswith("class ") and ":" in stripped:
                    cls_name = stripped.split("(")[0].replace("class ", "").strip().rstrip(":")
                    # Extract methods from indented block
                    classes.append({
                        "name": cls_name,
                        "file": rel_path,
                        "signature": stripped.rstrip(":"),
                    })
                if stripped.startswith("def ") and "(" in stripped:
                    func_sig = stripped.rstrip(":").strip()
                    func_name = func_sig.split("(")[0].replace("def ", "").strip()
                    if not func_name.startswith("_"):
                        functions.append({
                            "name": func_name,
                            "file": rel_path,
                            "signature": func_sig,
                        })
                if stripped.startswith("async def ") and "(" in stripped:
                    func_sig = stripped.rstrip(":").strip()
                    func_name = func_sig.split("(")[0].replace("async def ", "").strip()
                    if not func_name.startswith("_"):
                        functions.append({
                            "name": func_name,
                            "file": rel_path,
                            "signature": func_sig,
                        })

            # JavaScript / TypeScript
            elif suffix in (".js", ".jsx", ".ts", ".tsx"):
                if "import " in stripped and " from " in stripped:
                    parts = stripped.split(" from ")
                    if len(parts) == 2:
                        pkg = parts[1].strip().strip("'\"").strip(";")
                        if not pkg.startswith("."):
                            imports.add(pkg.split("/")[0])
                if stripped.startswith("export function ") or stripped.startswith("function "):
                    sig = stripped.split("{")[0].strip()
                    fname = sig.replace("export ", "").replace("function ", "").split("(")[0].strip()
                    functions.append({"name": fname, "file": rel_path, "signature": sig})
                if stripped.startswith("export class ") or stripped.startswith("class "):
                    sig = stripped.split("{")[0].strip()
                    cname = sig.replace("export ", "").replace("class ", "").split(" ")[0].strip()
                    classes.append({"name": cname, "file": rel_path, "signature": sig})

            # Go
            elif suffix == ".go":
                if stripped.startswith("func ") and "(" in stripped:
                    sig = stripped.split("{")[0].strip()
                    functions.append({"name": sig.split("(")[0].replace("func ", "").strip(), "file": rel_path, "signature": sig})
                if stripped.startswith("type ") and "struct" in stripped:
                    tname = stripped.split(" ")[1] if len(stripped.split(" ")) > 1 else "Unknown"
                    classes.append({"name": tname, "file": rel_path, "signature": stripped.split("{")[0].strip()})

        # Detect patterns
        if "fastapi" in content.lower() or "flask" in content.lower() or "express" in content.lower():
            if "REST API / Web Framework" not in patterns:
                patterns.append("REST API / Web Framework")
        if "sqlalchemy" in content.lower() or "prisma" in content.lower() or "orm" in content.lower():
            if "ORM / Database Layer" not in patterns:
                patterns.append("ORM / Database Layer")
        if "celery" in content.lower() or "queue" in content.lower():
            if "Task Queue / Background Jobs" not in patterns:
                patterns.append("Task Queue / Background Jobs")
        if "websocket" in content.lower():
            if "WebSocket" not in patterns:
                patterns.append("WebSocket")
        if "@router" in content or "@app.route" in content or "router." in content:
            if "Router / Endpoint Definitions" not in patterns:
                patterns.append("Router / Endpoint Definitions")
        if "dataclass" in content or "BaseModel" in content or "interface " in content:
            if "Data Models / Schema Definitions" not in patterns:
                patterns.append("Data Models / Schema Definitions")

    return {
        "classes": classes[:50],
        "functions": functions[:80],
        "imports": sorted(imports),
        "patterns": patterns,
    }


def _build_library_structure(
    name: str,
    slug: str,
    description: str,
    source_files: list[str],
    entry_points: list[str],
    tags: list[str],
    source_repo_url: str,
    candidate_name: str,
    code_analysis: dict | None = None,
) -> LibraryDocNodeResponse:
    """Build a hierarchical document tree for a generated library.

    When ``code_analysis`` is provided (from ``_analyze_source_code``),
    instructions are derived from the actual code structure rather than
    generic templates.  ``source_repo_url`` is the display URL/path for
    the source repository (never a temp clone directory).
    """
    now = datetime.now(timezone.utc).isoformat()

    files_list = "\n".join(f"- `{f}`" for f in source_files[:30]) or "- *(none detected)*"
    ep_list = "\n".join(f"- `{ep}`" for ep in entry_points[:20]) or "- *(none detected)*"
    tags_inline = ", ".join(tags) if tags else "general"

    # Use code analysis to build richer content
    ca = code_analysis or {"classes": [], "functions": [], "imports": [], "patterns": []}

    # Build a code sketch from actual signatures
    class_sketch = ""
    if ca["classes"]:
        lines = []
        for cls in ca["classes"][:15]:
            lines.append(f"- **`{cls['name']}`** (in `{cls['file']}`)")
        class_sketch = "\n".join(lines)

    func_sketch = ""
    if ca["functions"]:
        lines = []
        for fn in ca["functions"][:20]:
            lines.append(f"- `{fn['signature']}`  *(in `{fn['file']}`)*")
        func_sketch = "\n".join(lines)

    imports_list = ""
    if ca["imports"]:
        imports_list = "\n".join(f"- `{pkg}`" for pkg in ca["imports"])

    patterns_list = ""
    if ca["patterns"]:
        patterns_list = "\n".join(f"- {p}" for p in ca["patterns"])

    # ---- Build instruction steps from actual code ----

    # Step 1: Data models & types (classes found)
    step1_content = f"""# Step 1: Define Data Models & Types

## Objective
Recreate the data models and type definitions used by **{name}**.

## What to Build
"""
    if class_sketch:
        step1_content += f"""The source code defines these key classes/types:

{class_sketch}

Implement equivalent data structures in your target project's language,
following its conventions for models (dataclasses, Pydantic, TypeScript
interfaces, Go structs, etc.).
"""
    else:
        step1_content += """No explicit class definitions were detected. Define any data
structures needed based on the entry points and function signatures below.
"""
    step1_content += """
## Guidelines
- Use the target project's idiomatic approach for data modeling
- Ensure all fields have appropriate types and validation
- Add serialization support if the data crosses API boundaries
"""

    # Step 2: Core functions/logic
    step2_content = f"""# Step 2: Implement Core Logic

## Objective
Build the primary functions and business logic for **{name}**.

## Functions to Implement
"""
    if func_sketch:
        step2_content += f"""The source code exposes these public functions:

{func_sketch}

Reimplement each function's behavior in your target language. The
signatures above show the expected inputs; adapt parameter names and
types to your project's conventions.
"""
    else:
        step2_content += f"""Implement the logic corresponding to these entry points:

{ep_list}
"""
    step2_content += """
## Guidelines
- Each function should have a single clear responsibility
- Include error handling consistent with your project's patterns
- Write unit tests alongside each function
"""

    # Step 3: Integration & wiring
    step3_content = f"""# Step 3: Integration & Wiring

## Objective
Connect all modules and expose the public interface for **{name}**.
"""
    if ca["patterns"]:
        step3_content += f"""
## Detected Patterns
The source code uses these architectural patterns:

{patterns_list}

Wire up your implementation to follow the same patterns using your
target framework's conventions.
"""
    if ca["imports"]:
        step3_content += f"""
## External Dependencies
The source relies on these packages -- find equivalents in your ecosystem:

{imports_list}
"""
    step3_content += """
## Actions
1. Create the public API surface (exports, endpoints, CLI commands)
2. Configure dependency injection or wiring for internal modules
3. Add integration tests that exercise the full workflow
4. Verify all entry points are reachable end-to-end
"""

    instruction_children = [
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Step 1: Data Models & Types",
            slug=f"{slug}/instructions/step_1_models",
            type="subsection",
            summary="Define data models and type structures from the analyzed code.",
            content=step1_content,
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Step 2: Core Logic",
            slug=f"{slug}/instructions/step_2_core_logic",
            type="subsection",
            summary="Implement the primary functions and business logic.",
            content=step2_content,
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Step 3: Integration & Wiring",
            slug=f"{slug}/instructions/step_3_integration",
            type="subsection",
            summary="Connect components, wire dependencies, and expose public API.",
            content=step3_content,
            children=[],
        ),
    ]

    # ---- Build instruction steps table from actual steps ----
    step_table = "\n".join(
        f"| {i+1} | {child.title} | {child.summary} |"
        for i, child in enumerate(instruction_children)
    )

    # ---- Architecture section with real data ----
    arch_content = f"""# {name} -- Architecture

## Detected Patterns
"""
    if patterns_list:
        arch_content += patterns_list + "\n"
    else:
        arch_content += "- *(Analyze source for architectural patterns)*\n"

    arch_content += f"""
## Module Structure
{files_list}
"""
    if class_sketch:
        arch_content += f"""
## Key Types
{class_sketch}
"""
    arch_content += f"""
## Entry Points
{ep_list}

## Data Flow
1. Input enters through the defined entry points
2. Core logic processes data via the functions and classes above
3. Results are returned through the public API surface
"""

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
This library encapsulates the functionality identified in the **{candidate_name}** candidate.

## Source Reference
- **Repository**: `{source_repo_url}`
- **File count**: {len(source_files)}
- **Entry points**: {len(entry_points)}

## Key Capabilities
{tags_inline}

## When to Use
Use this library's instructions to rebuild {candidate_name} functionality natively in your own project. The instructions describe *what* to build and *how* the pieces connect -- implement them in your target language and framework.
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Architecture",
            slug=f"{slug}/architecture",
            type="section",
            summary="Architecture and design patterns from source analysis.",
            content=arch_content,
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Instructions",
            slug=f"{slug}/instructions",
            type="section",
            summary="Step-by-step implementation guide derived from source code analysis.",
            content=f"""# {name} -- Implementation Instructions

## Overview
This section provides a step-by-step guide for rebuilding the **{name}** functionality in your own project. Each step is informed by analysis of the source code's actual structure, classes, and functions.

## Steps

| Step | Title | Description |
|------|-------|-------------|
{step_table}

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
- **Native implementation**: Implement all functionality in the target project's primary language -- never copy-paste source code
- **Integration contract**: The result should look like it was hand-written for your project
- **Error handling**: Include robust error handling appropriate to the target project's patterns
- **No hardcoded environment values**: Ports, paths, hostnames, and secrets must be configurable

## Recommended Rules (SHOULD)
- **Reuse dependencies**: Use the target project's existing packages where possible
- **Match code style**: Follow the target project's formatting, naming, and structural conventions
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
3. **Conformance checks**: Validate against the source repo as a reference

## Acceptance Criteria
- All unit tests pass
- Integration tests cover primary workflows
- Code style checks pass (linting, formatting)
- Behaviour matches the source entry points

## Test Approach
| Criterion | Method | Expected Result |
|-----------|--------|----------------|
| Core functionality | Unit tests | All tests pass |
| API contracts | Integration tests | Correct inputs/outputs |
| Error handling | Negative tests | Graceful failure |
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
{imports_list if imports_list else '*(None detected -- review source for runtime dependencies)*'}

Find equivalent packages in your target ecosystem and add them to your
dependency manifest.

## Source Files (for reference)
{files_list}

## Compatibility Notes
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
- Source repository: `{source_repo_url}`
- {len(source_files)} source files analysed
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
| Source Repository | `{source_repo_url}` |
| Candidate | {candidate_name} |
| Source Files | {len(source_files)} |
| Entry Points | {len(entry_points)} |
| Tags | {tags_inline} |

## Change Log
- **{now[:10]}**: Initial library generated from analyzer candidate "{candidate_name}"

## Compliance Notes
- This library was generated using ALE's automated analysis pipeline
- Instructions are derived from static analysis of the source code
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

> Agentic build instructions generated from the **{candidate_name}** analysis candidate.

## Summary
{description or 'A library extracted from the analyzed codebase.'}

## Source Reference
- **Repository**: `{source_repo_url}`
- **Candidate**: {candidate_name}
- **Generated**: {now}
- **Version**: 1.0.0

## Structure

| Section | Description |
|---------|-------------|
{section_toc}

## Quick Start
1. Review the **Overview** to understand what this library rebuilds
2. Follow the **Instructions** step-by-step to implement in your project
3. Check **Guardrails** for mandatory rules and constraints
4. Run **Validation** criteria to verify your implementation
5. Use the source repository as a last-mile reference to validate your build

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
    """Generate a full hierarchical library document structure from an analysis candidate.

    Reads the actual source files to produce code-aware instruction steps
    rather than generic templates.  Stores the ``source_repo_url`` (the
    original repo URL or local path) instead of any temporary clone path.
    """
    if not request.repo_path.strip():
        raise HTTPException(status_code=400, detail="repo_path is required")
    if not request.candidate_name.strip():
        raise HTTPException(status_code=400, detail="candidate_name is required")

    # Determine the display URL for the source repo.
    # Prefer the explicit source_repo_url from the frontend; fall back to repo_path.
    source_repo_url = (request.source_repo_url or "").strip() or request.repo_path

    # Derive a display name
    raw_name = request.candidate_name
    if raw_name == "__whole_codebase__":
        # Use the repo directory name (strip temp prefixes)
        dir_name = Path(request.repo_path).name or "codebase"
        # If it looks like a temp clone name (ale_*), use a generic fallback
        if dir_name.startswith("ale_"):
            # Try to derive from the URL
            url_parts = source_repo_url.rstrip("/").split("/")
            dir_name = url_parts[-1].replace(".git", "") if url_parts else "codebase"
        raw_name = dir_name
    display_name = raw_name.replace("_", " ").replace("-", " ").title()
    slug = _slugify(raw_name) + "_library"

    # Analyze the actual source code for richer instructions
    code_analysis = _analyze_source_code(request.repo_path, request.source_files)

    structure = _build_library_structure(
        name=display_name,
        slug=slug,
        description=request.candidate_description,
        source_files=request.source_files,
        entry_points=request.entry_points,
        tags=request.tags,
        source_repo_url=source_repo_url,
        candidate_name=request.candidate_name,
        code_analysis=code_analysis,
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
        source_repo_url=source_repo_url,
    )

    # Persist to disk — include source commit and source_repo_url
    libs_dir = _ensure_libraries_dir()
    lib_path = libs_dir / f"{library_id}.json"
    lib_data = library.model_dump()
    lib_data["source_commit"] = _get_repo_head_commit(request.repo_path)
    with open(lib_path, "w") as f:
        json.dump(lib_data, f, indent=2)

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
    "/libraries/search",
    response_model=list[GeneratedLibraryResponse],
    summary="Search generated libraries by text query",
)
async def search_generated_libraries(
    text: str = "",
):
    """Search generated libraries by name, candidate, or repo URL.

    Returns libraries whose name, candidate_name, or source_repo_url
    contain the search text (case-insensitive).  Returns all libraries
    if no text is provided.
    """
    libs_dir = _ensure_libraries_dir()
    libraries: list[dict] = []
    query = text.strip().lower()

    for lib_file in libs_dir.glob("*.json"):
        try:
            with open(lib_file) as f:
                lib = json.load(f)
        except (json.JSONDecodeError, KeyError):
            continue

        if not query:
            libraries.append(lib)
            continue

        # Search across multiple fields
        searchable = " ".join([
            lib.get("name", ""),
            lib.get("candidate_name", ""),
            lib.get("source_repo_url", ""),
            lib.get("repo_path", ""),
        ]).lower()

        if query in searchable:
            libraries.append(lib)

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


# ---------------------------------------------------------------------------
# Library Update Detection
# ---------------------------------------------------------------------------


def _load_library(library_id: str) -> dict:
    """Load a generated library JSON by ID, or raise 404."""
    libs_dir = _ensure_libraries_dir()
    lib_path = libs_dir / f"{library_id}.json"
    if not lib_path.exists():
        raise HTTPException(status_code=404, detail=f"Library '{library_id}' not found")
    try:
        with open(lib_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read library: {exc}")


def _extract_source_files_from_structure(structure: dict) -> list[str]:
    """Walk the library document tree and extract referenced source file paths."""
    files: list[str] = []
    content = structure.get("content", "")
    # Look for backtick-quoted file paths in the content
    for match in re.finditer(r"`([^`]+\.\w+)`", content):
        candidate = match.group(1)
        # Filter to likely file paths (contain / or end with known extensions)
        if "/" in candidate or candidate.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java")):
            files.append(candidate)

    for child in structure.get("children", []):
        files.extend(_extract_source_files_from_structure(child))

    return list(dict.fromkeys(files))  # deduplicate preserving order


def _get_repo_head_commit(repo_path: str) -> str:
    """Get the current HEAD commit SHA for a repo path."""
    try:
        from git import Repo as GitRepo
        r = GitRepo(repo_path)
        return str(r.head.commit.hexsha)
    except Exception:
        return ""


@router.post(
    "/libraries/{library_id}/check-updates",
    response_model=UpdateCheckResponse,
    summary="Check if a generated library's source repo has updates",
)
async def check_library_updates(library_id: str):
    """Check the source repository for changes since the library was generated.

    Analyzes the git history of the source repo and classifies changes
    as major, minor, or patch based on commit volume, file churn, version
    tags, and whether the library's own source files were affected.
    """
    lib = _load_library(library_id)
    repo_path = lib.get("repo_path", "")

    if not repo_path or not Path(repo_path).is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Source repository path is not accessible: {repo_path}",
        )

    # Extract source files from the library structure for relevance checking
    source_files = _extract_source_files_from_structure(lib.get("structure", {}))

    # Determine the commit the library was generated from
    # We store this in the library metadata; if not present, use the creation timestamp
    since_commit = lib.get("source_commit", "")

    from ale.sync.update_checker import check_for_updates

    result = check_for_updates(
        repo_path=repo_path,
        since_commit=since_commit,
        source_files=source_files,
    )

    return UpdateCheckResponse(
        has_updates=result.has_updates,
        severity=result.severity,
        severity_reason=result.severity_reason,
        current_commit=result.current_commit,
        latest_commit=result.latest_commit,
        new_commit_count=result.new_commit_count,
        commit_messages=result.commit_messages,
        files_changed=result.files_changed,
        total_insertions=result.total_insertions,
        total_deletions=result.total_deletions,
        changed_files=[
            FileChangeResponse(
                path=fc.path,
                insertions=fc.insertions,
                deletions=fc.deletions,
                status=fc.status,
            )
            for fc in result.changed_files[:50]
        ],
        source_files_affected=result.source_files_affected,
        source_files_changed=result.source_files_changed,
        new_tags=result.new_tags,
        latest_tag=result.latest_tag,
        summary=result.summary,
        change_notes=result.change_notes,
        library_id=library_id,
        library_name=lib.get("name", ""),
    )


@router.post(
    "/libraries/{library_id}/update",
    response_model=GenerateHierarchicalLibraryResponse,
    summary="Rebuild a library from the latest source (in-place update)",
)
async def update_library(library_id: str):
    """Rebuild the library from the latest source repo state.

    Overwrites the existing library with a freshly generated version
    using the same candidate parameters but the latest source code.
    """
    lib = _load_library(library_id)
    repo_path = lib.get("repo_path", "")
    candidate_name = lib.get("candidate_name", "")

    if not repo_path or not Path(repo_path).is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Source repository path is not accessible: {repo_path}",
        )

    # Recover the source_repo_url from stored metadata
    source_repo_url = lib.get("source_repo_url", repo_path)

    # Extract the original generation parameters from the stored library
    raw_name = candidate_name
    if raw_name == "__whole_codebase__":
        raw_name = Path(repo_path).name or "codebase"
    display_name = raw_name.replace("_", " ").replace("-", " ").title()
    slug = _slugify(raw_name) + "_library"

    # Extract source files and other metadata from the original structure
    source_files = _extract_source_files_from_structure(lib.get("structure", {}))
    description = lib.get("structure", {}).get("summary", "")

    # Capture current commit for future update checks
    current_commit = _get_repo_head_commit(repo_path)

    # Analyze actual source code for richer instructions
    code_analysis = _analyze_source_code(repo_path, source_files)

    structure = _build_library_structure(
        name=display_name,
        slug=slug,
        description=description,
        source_files=source_files,
        entry_points=[],
        tags=[],
        source_repo_url=source_repo_url,
        candidate_name=candidate_name,
        code_analysis=code_analysis,
    )

    now = datetime.now(timezone.utc).isoformat()

    updated_library = GeneratedLibraryResponse(
        id=library_id,  # Keep the same ID
        name=display_name,
        root_doc=f"{slug}.md",
        repo_path=repo_path,
        candidate_name=candidate_name,
        created_at=lib.get("created_at", now),
        updated_at=now,
        structure=structure,
        source_repo_url=source_repo_url,
    )

    # Persist (overwrite) to disk
    libs_dir = _ensure_libraries_dir()
    lib_path = libs_dir / f"{library_id}.json"
    lib_data = updated_library.model_dump()
    lib_data["source_commit"] = current_commit
    with open(lib_path, "w") as f:
        json.dump(lib_data, f, indent=2)

    return GenerateHierarchicalLibraryResponse(
        success=True,
        library=updated_library,
        message=f"Library '{display_name}' updated from latest source. Commit: {current_commit[:12]}",
    )


@router.post(
    "/libraries/{library_id}/create-from-latest",
    response_model=GenerateHierarchicalLibraryResponse,
    summary="Create a new library version from latest source (preserves original)",
)
async def create_from_latest(library_id: str, request: CreateFromLatestRequest):
    """Create a new library from the latest source, preserving the original.

    This allows the user to test and experiment with the new version
    before deciding to overwrite the existing library.
    """
    lib = _load_library(library_id)
    repo_path = lib.get("repo_path", "")
    candidate_name = lib.get("candidate_name", "")
    source_repo_url = lib.get("source_repo_url", repo_path)

    if not repo_path or not Path(repo_path).is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Source repository path is not accessible: {repo_path}",
        )

    raw_name = candidate_name
    if raw_name == "__whole_codebase__":
        raw_name = Path(repo_path).name or "codebase"

    # Use custom name or generate one with timestamp
    now = datetime.now(timezone.utc)
    if request.new_name and request.new_name.strip():
        display_name = request.new_name.strip()
    else:
        display_name = raw_name.replace("_", " ").replace("-", " ").title()
        display_name = f"{display_name} ({now.strftime('%Y-%m-%d %H:%M')})"

    slug = _slugify(display_name) + "_library"

    source_files = _extract_source_files_from_structure(lib.get("structure", {}))
    description = lib.get("structure", {}).get("summary", "")

    current_commit = _get_repo_head_commit(repo_path)

    code_analysis = _analyze_source_code(repo_path, source_files)

    structure = _build_library_structure(
        name=display_name,
        slug=slug,
        description=description,
        source_files=source_files,
        entry_points=[],
        tags=[],
        source_repo_url=source_repo_url,
        candidate_name=candidate_name,
        code_analysis=code_analysis,
    )

    new_library_id = str(uuid.uuid4())

    new_library = GeneratedLibraryResponse(
        id=new_library_id,
        name=display_name,
        root_doc=f"{slug}.md",
        repo_path=repo_path,
        candidate_name=candidate_name,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        structure=structure,
        source_repo_url=source_repo_url,
    )

    # Persist as a new file
    libs_dir = _ensure_libraries_dir()
    lib_path = libs_dir / f"{new_library_id}.json"
    lib_data = new_library.model_dump()
    lib_data["source_commit"] = current_commit
    lib_data["forked_from"] = library_id
    with open(lib_path, "w") as f:
        json.dump(lib_data, f, indent=2)

    return GenerateHierarchicalLibraryResponse(
        success=True,
        library=new_library,
        message=f"New library '{display_name}' created from latest source. Original preserved.",
    )
