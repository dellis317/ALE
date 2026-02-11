"""Consumer scaffold generator — creates the ALE/ folder structure on the consumer's machine.

When a developer (or their AI coding assistant) first pulls an ALE library,
we need to create a standardized folder structure OUTSIDE their application root.
This module generates that structure.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Template content for generated files
# ---------------------------------------------------------------------------

_ALE_ENV_TEMPLATE = """\
# ALE (Agentic Library Exchange) Configuration
# This file contains credentials for the ALE registry API.
# Do NOT commit this file to version control.

ALE_API_ENDPOINT={api_endpoint}
ALE_API_KEY=
ALE_USER_EMAIL={user_email}
"""

_AGENT_INSTRUCTIONS_TEMPLATE = """\
# ALE Agent Instructions

You have access to ALE (Agentic Library Exchange) build plans — pre-built
blueprints for implementing common features and patterns.

## What ALE Libraries Are

ALE libraries are NOT code dependencies. They are structured instruction sets
(build plans) that describe HOW to implement a feature natively in any project.
When you use an ALE library, you read the build plan and write native code
that follows the instructions — the result should look like it was hand-written
for this project.

## How to Use Existing Libraries

1. Check `ALE_versions.md` for a list of available build plans
2. Read `Libraries/<library-id>/build-plan.md` for implementation instructions
3. Follow the build plan to implement the feature in THIS project's language/framework
4. Respect the guardrails section — these are constraints the implementation MUST follow
5. Use the validation criteria to verify your implementation is correct

## How to Get New Libraries

1. Read credentials from `ALE.env` (ALE_API_ENDPOINT and ALE_API_KEY)
2. Search: `GET {ALE_API_ENDPOINT}/distribution/search?q={description}`
3. Pull: `GET {ALE_API_ENDPOINT}/distribution/pull/{library_id}/{version}`
4. Save the returned build plan to `Libraries/<library-id>/build-plan.md`
5. Save the returned README to `Libraries/<library-id>/README.md`
6. Update `ALE_versions.md` with the new library entry

## Critical Rules

- **DO NOT** let ALE libraries override this project's language, framework, or dependency choices
- **DO NOT** introduce new dependencies — use the project's existing equivalents
- **DO NOT** override the project's security model, auth approach, or environment configuration
- **DO** implement features using the project's native patterns and conventions
- **DO** follow the guardrails in each build plan
- **DO** run the validation criteria after implementation
"""

_ALE_VERSIONS_TEMPLATE = """\
# ALE Library Manifest

Last updated: {timestamp}

## Installed Libraries

| Library ID | Name | Version | Downloaded | Status |
|------------|------|---------|------------|--------|

## Configuration

- **ALE Endpoint**: {endpoint_display}
- **User**: {user_display}

---
*Managed by ALE (Agentic Library Exchange). Updated automatically when libraries are pulled.*
"""


class ConsumerScaffold:
    """Generates and manages the consumer-side ALE folder structure.

    The ALE folder lives OUTSIDE the application root to keep credentials
    and build plans separate from deployable code.

    Structure:
        ALE/
        ├── ALE.env                  # API key, endpoint URL, user config
        ├── ALE_versions.md          # Manifest of all pulled libraries
        ├── AGENT_INSTRUCTIONS.md    # Instructions for AI coding assistants
        └── Libraries/
            └── <library_id>/
                ├── README.md        # Library description, version, metadata
                └── build-plan.md    # Full implementation instructions
    """

    def __init__(self, ale_root: str):
        """Initialize with path to the ALE/ directory.

        Args:
            ale_root: Absolute or relative path to the consumer ALE/ directory.
        """
        self.ale_root = Path(ale_root)
        self.libraries_dir = self.ale_root / "Libraries"
        self.env_path = self.ale_root / "ALE.env"
        self.versions_path = self.ale_root / "ALE_versions.md"
        self.agent_instructions_path = self.ale_root / "AGENT_INSTRUCTIONS.md"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize(self, api_endpoint: str = "", user_email: str = "") -> dict:
        """Create the full ALE folder structure if it doesn't exist.

        Creates: ALE/, ALE/Libraries/, ALE.env, ALE_versions.md,
        AGENT_INSTRUCTIONS.md

        Returns:
            dict with keys ``directories`` and ``files``, each a list of
            :class:`pathlib.Path` objects that were created (or already existed).

        Idempotent — safe to call multiple times.
        """
        created_dirs: list[Path] = []
        created_files: list[Path] = []

        # --- Directories ---------------------------------------------------
        for directory in (self.ale_root, self.libraries_dir):
            directory.mkdir(parents=True, exist_ok=True)
            created_dirs.append(directory)

        # --- ALE.env -------------------------------------------------------
        if not self.env_path.exists():
            endpoint = api_endpoint or "https://ale.example.com/api/v1"
            self.env_path.write_text(
                _ALE_ENV_TEMPLATE.format(
                    api_endpoint=endpoint,
                    user_email=user_email,
                ),
            )
        created_files.append(self.env_path)

        # --- AGENT_INSTRUCTIONS.md -----------------------------------------
        if not self.agent_instructions_path.exists():
            self.agent_instructions_path.write_text(_AGENT_INSTRUCTIONS_TEMPLATE)
        created_files.append(self.agent_instructions_path)

        # --- ALE_versions.md -----------------------------------------------
        if not self.versions_path.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            endpoint_display = api_endpoint if api_endpoint else "(not configured)"
            user_display = user_email if user_email else "(not configured)"
            self.versions_path.write_text(
                _ALE_VERSIONS_TEMPLATE.format(
                    timestamp=timestamp,
                    endpoint_display=endpoint_display,
                    user_display=user_display,
                ),
            )
        created_files.append(self.versions_path)

        return {
            "directories": created_dirs,
            "files": created_files,
        }

    def add_library(self, library_id: str, build_plan_md: str, readme_md: str) -> str:
        """Add a library to the ALE/Libraries/ folder.

        Creates ``ALE/Libraries/<library_id>/`` and writes ``build-plan.md``
        and ``README.md`` inside it.

        Args:
            library_id: Unique identifier for the library (e.g. ``"ale_a1b2c3d4"``).
            build_plan_md: Full Markdown content for the build plan.
            readme_md: Full Markdown content for the README.

        Returns:
            Absolute string path to the created library directory.
        """
        lib_dir = self.libraries_dir / library_id
        lib_dir.mkdir(parents=True, exist_ok=True)

        build_plan_path = lib_dir / "build-plan.md"
        build_plan_path.write_text(build_plan_md)

        readme_path = lib_dir / "README.md"
        readme_path.write_text(readme_md)

        return str(lib_dir)

    def library_exists(self, library_id: str) -> bool:
        """Check if a library folder already exists."""
        return (self.libraries_dir / library_id).is_dir()

    def list_libraries(self) -> list[str]:
        """List all library IDs currently in ALE/Libraries/.

        Returns:
            Sorted list of directory names inside ``ALE/Libraries/``.
        """
        if not self.libraries_dir.exists():
            return []
        return sorted(
            p.name for p in self.libraries_dir.iterdir() if p.is_dir()
        )
