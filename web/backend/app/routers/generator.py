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


def _read_source_sketches(source_files: list[str], max_files: int = 10) -> str:
    """Read source files and extract function/class signatures for code sketches."""
    sketches: list[str] = []
    sig_keywords = ("def ", "class ", "function ", "export ", "pub fn ", "func ", "async def ")

    for src in source_files[:max_files]:
        path = Path(src)
        if not path.exists():
            continue
        try:
            content = path.read_text(errors="replace")
        except Exception:
            continue

        file_sigs: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if any(stripped.startswith(kw) for kw in sig_keywords):
                file_sigs.append(f"  {stripped}")

        if file_sigs:
            sketches.append(f"# {path.name}\n" + "\n".join(file_sigs))

    return "\n\n".join(sketches) if sketches else "# No signatures extracted -- implement from description"


def _build_library_structure(
    name: str,
    slug: str,
    description: str,
    source_files: list[str],
    entry_points: list[str],
    tags: list[str],
    repo_path: str,
    candidate_name: str,
    size_class: str = "",
) -> LibraryDocNodeResponse:
    """Build a hierarchical document tree for a generated library.

    Produces detailed, actionable build instructions that an AI coding agent
    can follow to implement the library in a consumer project. Includes:
    - ALE directory structure setup instructions
    - Version tracking with versions.json
    - Detailed code sketches from source analysis
    - Size-class-appropriate depth of guidance
    """
    now = datetime.now(timezone.utc).isoformat()
    size_label = size_class.capitalize() if size_class else "Component"
    kebab_name = slug.replace("_library", "").replace("_", "-")

    files_list = "\n".join(f"- `{f}`" for f in source_files[:30]) or "- *(none detected)*"
    ep_list = "\n".join(f"- `{ep}`" for ep in entry_points[:20]) or "- *(none detected)*"
    tags_inline = ", ".join(tags) if tags else "general"

    # Extract real code sketches from source files
    code_sketches = _read_source_sketches(source_files)

    # ---------------------------------------------------------------
    # Instruction sub-nodes — detailed, actionable steps
    # ---------------------------------------------------------------
    instruction_children = [
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Step 0: ALE Directory Setup",
            slug=f"{slug}/instructions/step_0_ale_setup",
            type="subsection",
            summary="Create the ALE directory structure in the consumer project.",
            content=f"""# Step 0: ALE Directory Setup

## Objective
Set up the standardized ALE directory in the consumer project so that this
library's build instructions, version tracking, and any future ALE libraries
are organized in a consistent, discoverable location.

## IMPORTANT — Read This First
This step must be completed BEFORE implementing any library code. The ALE
directory is how the project tracks which agentic libraries have been applied,
their versions, and their build instructions. This enables version checking,
updates, and drift detection.

## Actions

### 0.1 Create the ALE directory structure
```
mkdir -p ALE/libraries/{kebab_name}
```

The directory layout should be:
```
<project-root>/
  ALE/
    versions.json          # Tracks all applied agentic libraries
    libraries/
      {kebab_name}/        # This library's build instructions
        README.md           # Summary of what was built and how
        spec.yaml           # The agentic library spec (copy of this)
```

### 0.2 Initialize or update versions.json
If `ALE/versions.json` does not exist, create it:
```json
{{
  "ale_spec_version": "1.0",
  "libraries": {{}}
}}
```

Then add (or update) this library's entry:
```json
{{
  "ale_spec_version": "1.0",
  "libraries": {{
    "{kebab_name}": {{
      "version": "1.0.0",
      "installed_at": "{now}",
      "source_repo": "{repo_path}",
      "size_class": "{size_class or 'component'}",
      "tags": {json.dumps(tags[:10])},
      "status": "installed"
    }}
  }}
}}
```

### 0.3 Add ALE directory to version control
```
git add ALE/
```

**Do NOT add ALE/ to .gitignore** — this directory should be tracked in version
control so team members and CI can verify library versions and conformance.

## Preconditions
- The consumer project must have a root directory with write access
- Git must be initialized (or another VCS)

## Notes
- If `ALE/` already exists from a previous library install, just add the new
  subdirectory under `ALE/libraries/` and update `versions.json`
- The `versions.json` file is the single source of truth for which agentic
  libraries are installed — tools can read this to check for updates
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Step 1: Project Setup & Dependencies",
            slug=f"{slug}/instructions/step_1_setup",
            type="subsection",
            summary="Install dependencies and prepare the project structure.",
            content=f"""# Step 1: Project Setup & Dependencies

## Objective
Prepare the consumer project to support the **{name}** library by installing
required dependencies and creating the necessary file structure.

## Size Classification: {size_label}
{"This is a small, focused utility. Minimal setup required." if size_class == "widget" else
"This is a focused module. Standard setup applies." if size_class == "component" else
"This is a multi-module service. Careful dependency management needed." if size_class == "service" else
"This is a full application. Comprehensive setup required." if size_class == "app" else
"Standard setup applies."}

## Actions

### 1.1 Analyze the target project's stack
Before writing any code, identify:
- **Language/runtime**: What language does the target project use?
- **Package manager**: npm/yarn/pnpm (JS), pip/poetry/uv (Python), cargo (Rust), etc.
- **Framework**: React, Django, Express, FastAPI, etc.
- **Test framework**: Jest, pytest, Go test, etc.
- **Code style**: Existing linter config, formatting rules

### 1.2 Install required dependencies
Based on the source analysis, this library may need:
- Review the Dependencies section for the full list
- Use the target project's package manager to install
- Prefer packages already in the project's dependency tree

### 1.3 Create the file structure
Based on the source files analyzed ({len(source_files)} files), create the
corresponding structure in the target project following its conventions:

{files_list}

Map these to the target project's directory conventions. For example:
- Python: `src/{kebab_name.replace("-", "_")}/` or within existing package
- JavaScript/TS: `src/{kebab_name}/` or `lib/{kebab_name}/`
- Go: `internal/{kebab_name.replace("-", "_")}/` or `pkg/{kebab_name.replace("-", "_")}/`

### 1.4 Set up type definitions (if applicable)
Create type/interface files that match the target project's type system.

## Preconditions
- Step 0 (ALE directory setup) must be complete
- Target project must have a working build system

## Touched Surfaces
- Package manifest (package.json, requirements.txt, Cargo.toml, etc.)
- Project directory structure
- Type definition files
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Step 2: Core Logic Implementation",
            slug=f"{slug}/instructions/step_2_core_logic",
            type="subsection",
            summary="Implement the primary business logic using the code sketches below.",
            content=f"""# Step 2: Core Logic Implementation

## Objective
Implement the core functionality of **{name}** in the target project's
language and style. Use the code sketches below as a reference for the
API surface and logic flow.

## Entry Points to Implement
These are the primary public interfaces this library exposes:
{ep_list}

## Code Sketches (from source analysis)
The following signatures and structures were extracted from the source
repository. Implement equivalent functionality in the target language:

```
{code_sketches}
```

## Detailed Implementation Guidance

### 2.1 Data Models & Types
- Define all data structures, types, and interfaces first
- Match the source's data model semantics, not its syntax
- Use the target project's existing type patterns (e.g., dataclasses, interfaces, structs)

### 2.2 Core Functions / Methods
For each entry point listed above:
1. Create the function/method with the same semantic signature
2. Implement the business logic following the source's approach
3. Add input validation at the public API boundary
4. Return types should match the documented contract

### 2.3 Internal Helpers
- Implement any private/internal helper functions needed by the core logic
- Keep helpers focused on a single task
- Prefer pure functions where possible

### 2.4 Error Handling
- Use the target project's error handling patterns (exceptions, Result types, error codes)
- Provide meaningful error messages that help with debugging
- Never silently swallow errors in core logic paths

### 2.5 Write Unit Tests As You Go
For each function/class implemented:
- Write at least one happy-path test
- Write at least one error/edge-case test
- Tests should be in the target project's test directory following its conventions

## Tags
{tags_inline}

## Preconditions
- Step 1 (setup) must be complete
- Dependencies must be installed and importable

## Touched Surfaces
- Core implementation files
- Unit test files
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Step 3: Integration & Wiring",
            slug=f"{slug}/instructions/step_3_integration",
            type="subsection",
            summary="Connect components, expose the public API, and add integration tests.",
            content=f"""# Step 3: Integration & Wiring

## Objective
Wire all components together, expose the public API surface, and verify
the complete **{name}** library works as an integrated unit.

## Actions

### 3.1 Create the Public API Surface
- Create an index/barrel file that exports the public API
- Only expose what consumers need — keep internals private
- Example patterns by language:
  - **Python**: `__init__.py` with `__all__` exports
  - **JavaScript/TS**: `index.ts` with named exports
  - **Go**: exported (capitalized) functions in package
  - **Rust**: `pub` items in `lib.rs`

### 3.2 Integration with Existing Code
Connect to the target project's existing systems:
- Register routes/handlers if this is a web component
- Add to dependency injection container if applicable
- Wire up event listeners/observers if event-driven
- Add configuration to the project's config system

### 3.3 Integration Tests
Write tests that verify the library works within the project context:
1. Test the public API surface end-to-end
2. Test interactions with existing project components
3. Test configuration and environment variable handling
4. Test error propagation across boundaries

### 3.4 Documentation
- Add a brief usage section to the library's `ALE/libraries/{kebab_name}/README.md`
- Document any configuration needed in the project's main docs
- Add inline documentation for complex integration points

### 3.5 Final Verification
1. Run the full test suite (existing + new tests)
2. Run the linter and formatter
3. Verify the build succeeds
4. Check that existing functionality is not broken

## Preconditions
- Step 2 (core logic) must be complete with passing unit tests
- Target project must be in a working state

## Touched Surfaces
- Public API / index files
- Configuration files
- Integration test files
- Project documentation
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Step 4: Finalize & Record",
            slug=f"{slug}/instructions/step_4_finalize",
            type="subsection",
            summary="Update version tracking, commit the ALE spec, and verify everything.",
            content=f"""# Step 4: Finalize & Record

## Objective
Record the successful installation in the ALE version tracking system and
commit all changes.

## Actions

### 4.1 Update ALE/versions.json
Set the library's status to "active":
```json
{{
  "{kebab_name}": {{
    "version": "1.0.0",
    "installed_at": "<current ISO timestamp>",
    "activated_at": "<current ISO timestamp>",
    "source_repo": "{repo_path}",
    "size_class": "{size_class or 'component'}",
    "tags": {json.dumps(tags[:10])},
    "status": "active",
    "files_created": ["<list of files you created>"],
    "files_modified": ["<list of existing files you modified>"]
  }}
}}
```

### 4.2 Write ALE/libraries/{kebab_name}/README.md
Create a summary document:
```markdown
# {name}

**Version**: 1.0.0
**Size Class**: {size_label}
**Source**: {repo_path}
**Installed**: <current date>

## What This Does
{description or "Describe what was implemented."}

## Files Created
- List all files created during implementation

## Files Modified
- List all existing files that were modified

## Usage
Brief usage example showing how to use the library.

## Testing
How to run the tests for this library.
```

### 4.3 Copy the spec file
Save this library specification to `ALE/libraries/{kebab_name}/spec.yaml`
so the project has a record of what was supposed to be built.

### 4.4 Commit
Create a commit with a clear message:
```
feat: add {kebab_name} agentic library (v1.0.0)

Implemented from ALE library spec.
Source: {repo_path}
Size class: {size_label}
```

## Notes
- The `files_created` and `files_modified` arrays in versions.json enable
  future drift detection — if those files change, ALE can flag it
- This commit should include ALL changes: library code, tests, ALE metadata
""",
            children=[],
        ),
    ]

    # ---------------------------------------------------------------
    # Main sections
    # ---------------------------------------------------------------
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

## Size Classification: {size_label}
{"**Widget** -- A small, focused utility (single function or tiny module). Quick to implement." if size_class == "widget" else
"**Component** -- A focused module or small set of modules. Standard implementation effort." if size_class == "component" else
"**Service** -- Multiple modules with coordination logic. Significant implementation." if size_class == "service" else
"**App** -- A full application or large system. Major implementation effort." if size_class == "app" else
"Classification not yet determined."}

## Scope
This library encapsulates the functionality identified in the **{candidate_name}**
candidate from the repository at `{repo_path}`.

## Key Capabilities
{tags_inline}

## Source Files ({len(source_files)} total)
{files_list}

## Entry Points
{ep_list}

## When to Use
Use this library when you need the functionality provided by the {candidate_name}
component. It is designed to be language-agnostic — implement in whatever
language/framework the target project uses.

## How This Library Works
An AI coding agent (Claude, Copilot, Cursor, etc.) reads the Instructions
section step-by-step and implements equivalent functionality in the target
project. The instructions include:
1. **ALE directory setup** — standardized tracking structure
2. **Dependencies & setup** — what needs to be installed
3. **Core logic** — code sketches showing the API surface and logic
4. **Integration** — how to wire it into the existing project
5. **Finalization** — version tracking and verification
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Architecture",
            slug=f"{slug}/architecture",
            type="section",
            summary="Architecture, design patterns, and code sketches.",
            content=f"""# {name} -- Architecture

## Design Principles
- **Separation of concerns**: Each module handles a single responsibility
- **Composability**: Functions and classes are designed to be combined
- **Minimal dependencies**: Only essential external packages are used
- **Language agnostic**: Implement in the target project's language

## Module Structure
{files_list}

## Code Sketches
The following function/class signatures were extracted from the source:

```
{code_sketches}
```

These should be treated as a **reference**, not as copy-paste code. Implement
equivalent functionality following the target project's conventions.

## Data Flow
1. Input enters through the defined entry points
2. Core logic processes data through internal modules
3. Results are returned through the public API surface

## Integration Pattern
This library integrates with the consumer project via:
- Public API surface (exports, functions, classes)
- Configuration injection (environment variables, config files)
- Event hooks (if applicable to the pattern)
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Instructions",
            slug=f"{slug}/instructions",
            type="section",
            summary="Step-by-step implementation guide for AI coding agents.",
            content=f"""# {name} -- Implementation Instructions

## For AI Coding Agents
These instructions are designed to be followed step-by-step by an AI coding
agent (Claude, Copilot, Cursor, etc.). Each step includes:
- **Objective**: What you're trying to accomplish
- **Actions**: Specific things to do
- **Preconditions**: What must be true before starting
- **Touched Surfaces**: What files/systems are affected

## Size Classification: {size_label}
{"Expect ~15 minutes of implementation work." if size_class == "widget" else
"Expect a focused implementation session." if size_class == "component" else
"Expect a multi-step implementation across several files." if size_class == "service" else
"Expect a significant implementation effort across many files." if size_class == "app" else
"Implementation scope depends on the target project."}

## Steps Overview

| Step | Title | Description |
|------|-------|-------------|
| 0 | ALE Directory Setup | Create `ALE/` tracking structure in consumer project |
| 1 | Project Setup | Install dependencies and create file structure |
| 2 | Core Logic | Implement primary business logic from code sketches |
| 3 | Integration | Wire components, expose API, add integration tests |
| 4 | Finalize | Update version tracking, commit, verify |

## Critical Instruction
**Always start with Step 0.** The ALE directory structure enables version
tracking, update detection, and conformance checking. Without it, the
consumer project cannot track or update this library.

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
- **Follow existing code style**: Match the target project's formatting, naming
  conventions, and patterns exactly
- **Error handling**: Include robust error handling using the target project's patterns
- **Type safety**: Maintain type annotations/hints consistent with the project
- **ALE tracking**: Always update `ALE/versions.json` when installing or modifying
- **No vendor lock-in**: Do not introduce dependencies that lock the project to
  a specific vendor unless the project already uses them

## Recommended Rules (SHOULD)
- **Reuse dependencies**: Use the target project's existing packages where possible
- **Documentation**: Add docstrings/comments for all public APIs
- **Test coverage**: Aim for >80% coverage on core logic
- **Atomic commits**: Each logical change should be a separate commit
- **Backward compatibility**: Avoid breaking existing APIs in the target project

## Optional Rules (MAY)
- Add performance benchmarks for hot paths
- Include usage examples in the ALE library README
- Add monitoring/observability hooks
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
3. **Regression tests**: Ensure existing functionality is not broken
4. **Conformance checks**: Verify against the ALE spec

## Acceptance Criteria
- [ ] All unit tests pass
- [ ] Integration tests cover primary workflows
- [ ] Existing project tests still pass (no regressions)
- [ ] Code style checks pass (linting, formatting)
- [ ] ALE/versions.json is updated with "active" status
- [ ] ALE/libraries/{kebab_name}/README.md exists
- [ ] Build succeeds without warnings

## Test Approach
| Criterion | Method | Expected Result |
|-----------|--------|----------------|
| Core functionality | Unit tests | All tests pass |
| API contracts | Integration tests | Correct inputs/outputs |
| Error handling | Negative tests | Graceful failure with meaningful errors |
| Existing code | Regression suite | No breakage in existing tests |
| Code quality | Linter + formatter | Zero violations |
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

*(The AI agent should inspect the source files to identify specific packages)*

## Source File References
{files_list}

## Internal Dependencies
Modules within the component that reference each other — the agent should
maintain these relationships when implementing.

## Compatibility Targets
- Ensure compatibility with the target project's runtime environment
- Check version constraints for all external dependencies
- If a dependency conflicts with an existing project dependency, prefer the
  project's version and adapt the library code accordingly
""",
            children=[],
        ),
        LibraryDocNodeResponse(
            id=str(uuid.uuid4()),
            title="Version Tracking",
            slug=f"{slug}/version_tracking",
            type="section",
            summary="ALE version tracking system and update protocol.",
            content=f"""# {name} -- Version Tracking

## ALE/versions.json Schema
The `ALE/versions.json` file at the project root tracks all installed
agentic libraries:

```json
{{
  "ale_spec_version": "1.0",
  "libraries": {{
    "{kebab_name}": {{
      "version": "1.0.0",
      "installed_at": "{now}",
      "activated_at": "",
      "source_repo": "{repo_path}",
      "size_class": "{size_class or 'component'}",
      "tags": {json.dumps(tags[:10])},
      "status": "installed|active|outdated|removed",
      "files_created": [],
      "files_modified": []
    }}
  }}
}}
```

## Status Values
| Status | Meaning |
|--------|---------|
| `installed` | Library spec saved, implementation in progress |
| `active` | Fully implemented and verified |
| `outdated` | A newer version is available from the source |
| `removed` | Library was uninstalled (entry kept for audit) |

## Checking for Updates
To check if a newer version of this library is available:
1. Read `ALE/versions.json` to get the current version and source_repo
2. Fetch the latest spec from the source repository or ALE registry
3. Compare version numbers using semantic versioning
4. If outdated, update the status to "outdated" and prompt for upgrade

## Upgrade Protocol
1. Back up current implementation files (listed in `files_created`/`files_modified`)
2. Fetch the new library spec
3. Follow the new spec's instructions, adapting for changes
4. Update `ALE/versions.json` with new version and timestamp
5. Run the full test suite to verify

## Current Version
- **Library Version**: 1.0.0
- **Generated**: {now}
- **Source**: `{repo_path}`
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
| Size Class | {size_label} |
| Source Files | {len(source_files)} |
| Entry Points | {len(entry_points)} |
| Tags | {tags_inline} |

## Change Log
- **{now[:10]}**: Initial library generated from analyzer candidate "{candidate_name}"

## Compliance Notes
- This library was generated using ALE's automated analysis pipeline
- All source files were identified through static analysis
- Code sketches were extracted programmatically (not copied verbatim)
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
| *(Discover from source analysis)* | | | |

## Configuration Files
Any configuration files this library needs:
- The agent should create config following the target project's patterns

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

    # ---------------------------------------------------------------
    # Root node
    # ---------------------------------------------------------------
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

> **{size_label}** -- Auto-generated agentic library from **{candidate_name}**

## Summary
{description or 'A library extracted from the analyzed codebase.'}

## Source
- **Repository**: `{repo_path}`
- **Candidate**: {candidate_name}
- **Size Class**: {size_label}
- **Generated**: {now}
- **Version**: 1.0.0

## How to Use This Library
This library is designed to be consumed by an **AI coding agent** (Claude,
Copilot, Cursor, etc.). Give the agent these instructions:

> "Read the Instructions section of this library spec and implement it in
> our project. Start with Step 0 (ALE Directory Setup) and work through
> each step in order."

The agent will:
1. Create an `ALE/` directory in your project for tracking
2. Install required dependencies
3. Implement the core logic from the code sketches
4. Wire everything together and add tests
5. Record the installation in `ALE/versions.json`

## Structure

| Section | Description |
|---------|-------------|
{section_toc}

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
        size_class=getattr(request, "size_class", ""),
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
