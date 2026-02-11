"""Models for extraction candidates and codebase summaries.

Implements the 7-dimension scoring system from the architecture doc:
1. Isolation / Modularity
2. Coupling & Entanglement Risk
3. Complexity & Change Risk
4. Reuse Potential / Standardization Leverage
5. Testability & Verifiability
6. Portability / Abstraction Boundary Clarity
7. Security / Policy Sensitivity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoreDimension:
    """A single scoring dimension with its raw score and reasoning."""

    name: str
    score: float  # 0.0 - 1.0
    weight: float  # How much this contributes to overall
    reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)  # Warnings or blockers

    @property
    def weighted_score(self) -> float:
        return self.score * self.weight


@dataclass
class ScoringBreakdown:
    """Full explainable scoring breakdown for a candidate."""

    dimensions: list[ScoreDimension] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        if not self.dimensions:
            return 0.0
        total_weight = sum(d.weight for d in self.dimensions)
        if total_weight == 0:
            return 0.0
        return sum(d.weighted_score for d in self.dimensions) / total_weight

    @property
    def all_flags(self) -> list[str]:
        return [f for d in self.dimensions for f in d.flags]

    @property
    def top_reasons(self) -> list[str]:
        """Top 3 reasons from highest-scoring dimensions."""
        sorted_dims = sorted(self.dimensions, key=lambda d: d.weighted_score, reverse=True)
        reasons = []
        for d in sorted_dims:
            for r in d.reasons:
                reasons.append(f"[{d.name}] {r}")
                if len(reasons) >= 3:
                    return reasons
        return reasons

    @staticmethod
    def default_dimensions() -> list[ScoreDimension]:
        """Create the 7 standard scoring dimensions with default weights."""
        return [
            ScoreDimension(name="isolation", score=0.0, weight=0.20),
            ScoreDimension(name="coupling_risk", score=0.0, weight=0.15),
            ScoreDimension(name="complexity_risk", score=0.0, weight=0.10),
            ScoreDimension(name="reuse_potential", score=0.0, weight=0.20),
            ScoreDimension(name="testability", score=0.0, weight=0.15),
            ScoreDimension(name="portability", score=0.0, weight=0.15),
            ScoreDimension(name="security_sensitivity", score=0.0, weight=0.05),
        ]


@dataclass
class ExtractionCandidate:
    """A feature/utility identified in a repo that could become an Agentic Library."""

    name: str
    description: str
    source_files: list[str]
    entry_points: list[str]

    # 7-dimension scoring
    scoring: ScoringBreakdown = field(default_factory=ScoringBreakdown)

    # Legacy simple scores (for backward compat during transition)
    isolation_score: float = 0.0
    reuse_score: float = 0.0
    complexity_score: float = 0.0
    clarity_score: float = 0.0

    # Metadata
    tags: list[str] = field(default_factory=list)
    estimated_instruction_steps: int = 0
    dependencies_external: list[str] = field(default_factory=list)
    dependencies_internal: list[str] = field(default_factory=list)

    # Phase 2 enrichment fields
    context_summary: str = ""
    symbols: list[dict] = field(default_factory=list)  # [{name, kind, signature, docstring}]
    callers: list[str] = field(default_factory=list)
    callees: list[str] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        """Use 7-dimension scoring if available, fallback to legacy."""
        if self.scoring.dimensions:
            return self.scoring.overall_score
        # Legacy weighted composite
        return (
            self.isolation_score * 0.30
            + self.reuse_score * 0.30
            + self.complexity_score * 0.20
            + self.clarity_score * 0.20
        )

    def summary(self) -> str:
        return (
            f"[{self.overall_score:.2f}] {self.name}: {self.description} "
            f"({len(self.source_files)} files)"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for API responses."""
        data: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "source_files": self.source_files,
            "entry_points": self.entry_points,
            "overall_score": self.overall_score,
            "isolation_score": self.isolation_score,
            "reuse_score": self.reuse_score,
            "complexity_score": self.complexity_score,
            "clarity_score": self.clarity_score,
            "tags": self.tags,
            "estimated_instruction_steps": self.estimated_instruction_steps,
            "dependencies_external": self.dependencies_external,
            "dependencies_internal": self.dependencies_internal,
            "context_summary": self.context_summary,
            "symbols": self.symbols,
            "callers": self.callers,
            "callees": self.callees,
        }
        return data

    def detailed_report(self) -> str:
        """Full report with dimension breakdown, reasons, and flags."""
        lines = [
            f"{'=' * 60}",
            f"  {self.name} — {self.description}",
            f"  Overall Score: {self.overall_score:.2f}",
            f"  Files: {', '.join(self.source_files)}",
            f"{'=' * 60}",
        ]

        if self.scoring.dimensions:
            lines.append("\n  Dimension Breakdown:")
            for d in self.scoring.dimensions:
                bar = "#" * int(d.score * 20) + "." * (20 - int(d.score * 20))
                lines.append(f"    {d.name:<25} [{bar}] {d.score:.2f} (w={d.weight:.2f})")
                for r in d.reasons:
                    lines.append(f"      + {r}")
                for f in d.flags:
                    lines.append(f"      ! {f}")

        if self.scoring.top_reasons:
            lines.append("\n  Top Reasons:")
            for r in self.scoring.top_reasons:
                lines.append(f"    - {r}")

        if self.scoring.all_flags:
            lines.append("\n  Flags:")
            for f in self.scoring.all_flags:
                lines.append(f"    ! {f}")

        return "\n".join(lines)


@dataclass
class CodebaseSummary:
    """Aggregate summary of an analyzed codebase."""

    # Size metrics
    total_files: int = 0
    total_lines: int = 0
    files_by_language: dict[str, int] = field(default_factory=dict)

    # Structure metrics
    total_modules: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_constants: int = 0

    # Dependency metrics
    external_packages: list[str] = field(default_factory=list)
    internal_module_count: int = 0

    # Quality indicators
    docstring_coverage: float = 0.0  # 0.0 - 1.0
    type_hint_coverage: float = 0.0  # 0.0 - 1.0
    has_tests: bool = False
    has_ci_config: bool = False

    # Purpose / description
    description: str = ""  # What the project does — its jobs to be done
    purpose: str = ""  # Structural classification (framework, language, type)
    top_level_packages: list[str] = field(default_factory=list)
    key_capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "files_by_language": self.files_by_language,
            "total_modules": self.total_modules,
            "total_functions": self.total_functions,
            "total_classes": self.total_classes,
            "total_constants": self.total_constants,
            "external_packages": self.external_packages,
            "internal_module_count": self.internal_module_count,
            "docstring_coverage": self.docstring_coverage,
            "type_hint_coverage": self.type_hint_coverage,
            "has_tests": self.has_tests,
            "has_ci_config": self.has_ci_config,
            "description": self.description,
            "purpose": self.purpose,
            "top_level_packages": self.top_level_packages,
            "key_capabilities": self.key_capabilities,
        }
