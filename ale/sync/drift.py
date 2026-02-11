"""Drift detection — detect divergence between library intent and repo reality.

Drift happens when:
1. A newer version of the agentic library exists than what was applied
2. The repo's implementation has changed since the library was applied
3. The library's validation hooks no longer pass

Drift detection enables safe re-alignment and upgrade proposals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ale.sync.provenance import ProvenanceStore
from ale.spec.reference_runner import ReferenceRunner


class DriftType:
    VERSION = "version_drift"  # Newer library version available
    IMPLEMENTATION = "implementation_drift"  # Code changed since application
    VALIDATION = "validation_drift"  # Validation hooks now fail


@dataclass
class DriftReport:
    """Report of detected drift for a single library in a repo."""

    library_name: str
    applied_version: str
    latest_version: str = ""
    drift_types: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    validation_still_passes: bool | None = None

    @property
    def has_drift(self) -> bool:
        return len(self.drift_types) > 0

    def summary(self) -> str:
        if not self.has_drift:
            return f"{self.library_name} v{self.applied_version}: no drift detected"
        types = ", ".join(self.drift_types)
        return f"{self.library_name} v{self.applied_version}: DRIFT [{types}]"


class DriftDetector:
    """Detects drift between applied agentic libraries and repo state."""

    def __init__(self, repo_path: str | Path):
        self.repo_path = Path(repo_path)
        self.provenance = ProvenanceStore(repo_path)

    def check(
        self,
        library_name: str,
        latest_version: str = "",
        library_path: str | Path | None = None,
    ) -> DriftReport:
        """Check for drift on a specific library.

        Args:
            library_name: Name of the library to check.
            latest_version: Latest available version (for version drift check).
            library_path: Path to the library file (for validation drift check).
        """
        latest_record = self.provenance.get_latest(library_name)

        if not latest_record:
            return DriftReport(
                library_name=library_name,
                applied_version="(never applied)",
                details=["No provenance record found — library has never been applied."],
            )

        report = DriftReport(
            library_name=library_name,
            applied_version=latest_record.library_version,
            latest_version=latest_version or latest_record.library_version,
        )

        # Check 1: Version drift
        if latest_version and latest_version != latest_record.library_version:
            report.drift_types.append(DriftType.VERSION)
            report.details.append(
                f"Applied version: {latest_record.library_version}, "
                f"latest available: {latest_version}"
            )

        # Check 2: Validation drift (re-run hooks)
        if library_path:
            runner = ReferenceRunner(working_dir=self.repo_path)
            try:
                result = runner.run(library_path)
                report.validation_still_passes = result.all_passed
                if not result.all_passed:
                    report.drift_types.append(DriftType.VALIDATION)
                    report.details.append(
                        "Validation hooks no longer pass against current repo state."
                    )
            except Exception as e:
                report.drift_types.append(DriftType.VALIDATION)
                report.details.append(f"Validation check failed: {e}")

        return report

    def check_all(self) -> list[DriftReport]:
        """Check drift for all libraries with provenance records."""
        all_records = self.provenance.get_history()
        seen = set()
        reports = []

        for record in reversed(all_records):
            if record.library_name not in seen:
                seen.add(record.library_name)
                reports.append(
                    self.check(record.library_name)
                )

        return reports
