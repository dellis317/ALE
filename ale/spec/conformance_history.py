"""Conformance history store -- persists conformance run results to disk.

Stores conformance history entries as JSON files in ~/.ale/conformance_history/
so that past runs can be reviewed from the web portal.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ConformanceHistoryEntry:
    """A single conformance run record."""

    library_name: str
    library_version: str
    ran_at: str
    all_passed: bool
    schema_passed: bool
    semantic_passed: bool
    hooks_passed: bool
    total_duration_ms: int = 0


class ConformanceHistoryStore:
    """Persists and retrieves conformance run history.

    Storage layout:
        ~/.ale/conformance_history/<library_name>.json
    Each file is a JSON array of ConformanceHistoryEntry dicts.
    """

    def __init__(self, base_dir: str | Path | None = None):
        if base_dir is None:
            base_dir = Path.home() / ".ale" / "conformance_history"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _history_path(self, library_name: str) -> Path:
        """Return the history file path for a given library."""
        safe_name = library_name.replace("/", "_").replace("\\", "_")
        return self.base_dir / f"{safe_name}.json"

    def record_run(self, library_name: str, result) -> ConformanceHistoryEntry:
        """Record a conformance run result.

        Args:
            library_name: Name of the library that was validated.
            result: A RunnerResult or similar object with schema_passed,
                    semantic_passed, hooks_passed, all_passed, total_duration_ms,
                    library_version attributes.

        Returns:
            The created history entry.
        """
        from datetime import datetime, timezone

        entry = ConformanceHistoryEntry(
            library_name=library_name,
            library_version=getattr(result, "library_version", ""),
            ran_at=datetime.now(timezone.utc).isoformat(),
            all_passed=getattr(result, "all_passed", False),
            schema_passed=getattr(result, "schema_passed", False),
            semantic_passed=getattr(result, "semantic_passed", False),
            hooks_passed=getattr(result, "hooks_passed", True),
            total_duration_ms=getattr(result, "total_duration_ms", 0),
        )

        history = self._load(library_name)
        history.append(asdict(entry))
        self._save(library_name, history)

        return entry

    def get_history(self, library_name: str) -> list[ConformanceHistoryEntry]:
        """Get all past conformance runs for a library.

        Returns entries sorted by ran_at descending (most recent first).
        """
        raw = self._load(library_name)
        entries = []
        for item in raw:
            try:
                entries.append(ConformanceHistoryEntry(**item))
            except (TypeError, KeyError):
                continue
        return sorted(entries, key=lambda e: e.ran_at, reverse=True)

    def _load(self, library_name: str) -> list[dict]:
        path = self._history_path(library_name)
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def _save(self, library_name: str, history: list[dict]):
        path = self._history_path(library_name)
        with open(path, "w") as f:
            json.dump(history, f, indent=2)
