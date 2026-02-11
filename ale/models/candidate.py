"""Models for extraction candidates identified during repo analysis.

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
