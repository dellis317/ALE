"""Provenance — auditable records of library application.

Every time an Agentic Library is applied to a repo, a provenance record
is created. This supports auditability, rollback, and drift detection.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ale.models.agentic_library import ProvenanceRecord


class ProvenanceStore:
    """Stores and retrieves provenance records for a repository."""

    PROVENANCE_DIR = ".ale"
    PROVENANCE_FILE = "provenance.jsonl"

    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path)
        self.store_dir = self.repo_path / self.PROVENANCE_DIR
        self.store_file = self.store_dir / self.PROVENANCE_FILE

    def record(self, record: ProvenanceRecord) -> None:
        """Append a provenance record."""
        self.store_dir.mkdir(parents=True, exist_ok=True)

        if not record.applied_at:
            record.applied_at = datetime.now(timezone.utc).isoformat()

        entry = {
            "library_name": record.library_name,
            "library_version": record.library_version,
            "applied_at": record.applied_at,
            "applied_by": record.applied_by,
            "target_repo": record.target_repo,
            "target_branch": record.target_branch,
            "validation_passed": record.validation_passed,
            "validation_evidence": record.validation_evidence,
            "commit_sha": record.commit_sha,
        }

        with open(self.store_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_history(self, library_name: str | None = None) -> list[ProvenanceRecord]:
        """Retrieve provenance records, optionally filtered by library name."""
        if not self.store_file.exists():
            return []

        records = []
        with open(self.store_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if library_name and data.get("library_name") != library_name:
                    continue
                records.append(
                    ProvenanceRecord(
                        library_name=data["library_name"],
                        library_version=data["library_version"],
                        applied_at=data.get("applied_at", ""),
                        applied_by=data.get("applied_by", ""),
                        target_repo=data.get("target_repo", ""),
                        target_branch=data.get("target_branch", ""),
                        validation_passed=data.get("validation_passed", False),
                        validation_evidence=data.get("validation_evidence", ""),
                        commit_sha=data.get("commit_sha", ""),
                    )
                )
        return records

    def get_latest(self, library_name: str) -> ProvenanceRecord | None:
        """Get the most recent provenance record for a library."""
        history = self.get_history(library_name)
        return history[-1] if history else None
