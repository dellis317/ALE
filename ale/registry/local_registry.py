"""Local file-based registry implementation.

A simple, file-system-backed registry for development and single-org use.
Stores registry entries as JSON in a local directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from ale.registry.models import (
    QualitySignals,
    RegistryEntry,
    SearchQuery,
    SearchResult,
    VerificationResult,
)
from ale.spec.schema_validator import validate_schema
from ale.spec.semantic_validator import validate_semantics


class LocalRegistry:
    """File-based local registry for Agentic Libraries."""

    INDEX_FILE = "index.json"

    def __init__(self, registry_dir: str | Path):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.registry_dir / self.INDEX_FILE
        self._index: dict[str, dict] = self._load_index()

    def publish(self, library_path: str | Path) -> RegistryEntry:
        """Publish an Agentic Library to the registry.

        Reads the library file, verifies it, and adds it to the index.
        """
        path = Path(library_path)
        with open(path) as f:
            data = yaml.safe_load(f)

        lib = data.get("agentic_library", {})
        manifest = lib.get("manifest", {})

        # Verify against spec
        schema_issues = validate_schema(data)
        sem_result = validate_semantics(data)

        verification = VerificationResult(
            schema_passed=len(schema_issues) == 0,
            validator_passed=sem_result.passed,
            hooks_runnable=any(v.get("hook") for v in lib.get("validation", [])),
        )

        entry = RegistryEntry(
            name=manifest.get("name", ""),
            version=manifest.get("version", ""),
            spec_version=manifest.get("spec_version", ""),
            description=manifest.get("description", ""),
            tags=manifest.get("tags", []),
            capabilities=[
                d if isinstance(d, str) else d.get("capability", "")
                for d in lib.get("capability_dependencies", [])
            ],
            complexity=manifest.get("complexity", ""),
            language_agnostic=manifest.get("language_agnostic", True),
            target_languages=manifest.get("target_languages", []),
            quality=QualitySignals(verification=verification),
            library_path=str(path.resolve()),
            compatibility_targets=[
                c.get("target_id", "") for c in lib.get("compatibility", [])
            ],
        )

        # Store in index
        self._index[entry.qualified_id] = _entry_to_dict(entry)
        self._save_index()

        return entry

    def get(self, name: str, version: str = "") -> RegistryEntry | None:
        """Get a specific library entry."""
        if version:
            key = f"{name}@{version}"
            data = self._index.get(key)
            return _dict_to_entry(data) if data else None

        # Find latest version
        matching = [k for k in self._index if k.startswith(f"{name}@")]
        if not matching:
            return None
        latest_key = sorted(matching)[-1]
        return _dict_to_entry(self._index[latest_key])

    def search(self, query: SearchQuery) -> SearchResult:
        """Search the registry."""
        results = []

        for data in self._index.values():
            entry = _dict_to_entry(data)

            if query.text and query.text.lower() not in (
                entry.name + " " + entry.description
            ).lower():
                continue

            if query.tags and not any(t in entry.tags for t in query.tags):
                continue

            if query.capabilities and not any(
                c in entry.capabilities for c in query.capabilities
            ):
                continue

            if query.verified_only and not entry.is_verified:
                continue

            results.append(entry)

        return SearchResult(entries=results, total_count=len(results), query=query)

    def list_all(self) -> list[RegistryEntry]:
        """List all entries in the registry."""
        return [_dict_to_entry(d) for d in self._index.values()]

    def _load_index(self) -> dict[str, dict]:
        if self.index_path.exists():
            with open(self.index_path) as f:
                return json.load(f)
        return {}

    def _save_index(self):
        with open(self.index_path, "w") as f:
            json.dump(self._index, f, indent=2)


def _entry_to_dict(entry: RegistryEntry) -> dict:
    return {
        "name": entry.name,
        "version": entry.version,
        "spec_version": entry.spec_version,
        "description": entry.description,
        "tags": entry.tags,
        "capabilities": entry.capabilities,
        "complexity": entry.complexity,
        "language_agnostic": entry.language_agnostic,
        "target_languages": entry.target_languages,
        "library_path": entry.library_path,
        "compatibility_targets": entry.compatibility_targets,
        "quality": {
            "verified_schema": entry.quality.verification.schema_passed,
            "verified_validator": entry.quality.verification.validator_passed,
            "hooks_runnable": entry.quality.verification.hooks_runnable,
            "rating": entry.quality.rating,
            "rating_count": entry.quality.rating_count,
        },
    }


def _dict_to_entry(data: dict) -> RegistryEntry:
    quality_data = data.get("quality", {})
    return RegistryEntry(
        name=data["name"],
        version=data["version"],
        spec_version=data.get("spec_version", ""),
        description=data.get("description", ""),
        tags=data.get("tags", []),
        capabilities=data.get("capabilities", []),
        complexity=data.get("complexity", ""),
        language_agnostic=data.get("language_agnostic", True),
        target_languages=data.get("target_languages", []),
        library_path=data.get("library_path", ""),
        compatibility_targets=data.get("compatibility_targets", []),
        quality=QualitySignals(
            verification=VerificationResult(
                schema_passed=quality_data.get("verified_schema", False),
                validator_passed=quality_data.get("verified_validator", False),
                hooks_runnable=quality_data.get("hooks_runnable", False),
            ),
            rating=quality_data.get("rating", 0.0),
            rating_count=quality_data.get("rating_count", 0),
        ),
    )
