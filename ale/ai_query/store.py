"""File-based AI query interaction store.

Stores interaction records as JSONL files indexed by
``{library_name}__{component_name}.jsonl`` under ``~/.ale/ai_query_logs/``.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

from ale.ai_query.models import AIQueryRecord


def _safe_filename(name: str) -> str:
    """Sanitise a name for use as part of a filename."""
    return re.sub(r"[^\w\-.]", "_", name)


class AIQueryStore:
    """JSONL-backed store for AI query interactions."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir) if base_dir else Path.home() / ".ale" / "ai_query_logs"
        self._base.mkdir(parents=True, exist_ok=True)

    # -- helpers -------------------------------------------------------------

    def _file_for(self, library_name: str, component_name: str) -> Path:
        lib = _safe_filename(library_name)
        comp = _safe_filename(component_name)
        return self._base / f"{lib}__{comp}.jsonl"

    def _read_file(self, path: Path) -> list[AIQueryRecord]:
        records: list[AIQueryRecord] = []
        if not path.exists():
            return records
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(AIQueryRecord(**json.loads(line)))
            except (json.JSONDecodeError, TypeError):
                continue
        return records

    # -- public API ----------------------------------------------------------

    def record_query(self, record: AIQueryRecord) -> AIQueryRecord:
        """Append an interaction record and return it."""
        path = self._file_for(record.library_name, record.component_name)
        with path.open("a") as fh:
            fh.write(json.dumps(asdict(record)) + "\n")
        return record

    def get_history(
        self,
        library_name: str,
        component_name: str,
        limit: int = 50,
    ) -> list[AIQueryRecord]:
        """Return interaction history for a specific component, newest first."""
        path = self._file_for(library_name, component_name)
        records = self._read_file(path)
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]

    def get_history_by_user(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[AIQueryRecord]:
        """Return interactions for a specific user across all components."""
        records: list[AIQueryRecord] = []
        for path in self._base.glob("*.jsonl"):
            for rec in self._read_file(path):
                if rec.user_id == user_id:
                    records.append(rec)
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]

    def get_all_for_library(
        self,
        library_name: str,
        limit: int = 100,
    ) -> list[AIQueryRecord]:
        """Return interactions for all components of a library."""
        prefix = _safe_filename(library_name) + "__"
        records: list[AIQueryRecord] = []
        for path in self._base.glob("*.jsonl"):
            if path.name.startswith(prefix):
                records.extend(self._read_file(path))
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]

    def get_insights(
        self,
        library_name: str,
        component_name: str,
        limit: int = 10,
    ) -> list[AIQueryRecord]:
        """Return recent Q&A pairs for inline display in the analyzer UI."""
        return self.get_history(library_name, component_name, limit=limit)
