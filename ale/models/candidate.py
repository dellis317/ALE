"""Models for extraction candidates identified during repo analysis."""

from dataclasses import dataclass, field


@dataclass
class ExtractionCandidate:
    """A feature/utility identified in a repo that could become an Agentic Library."""

    name: str
    description: str
    source_files: list[str]  # Paths within the repo
    entry_points: list[str]  # Main functions/classes

    # Scoring dimensions (0.0 - 1.0)
    isolation_score: float = 0.0  # How self-contained is it?
    reuse_score: float = 0.0  # How broadly useful across projects?
    complexity_score: float = 0.0  # How feasible to extract? (higher = simpler = better)
    clarity_score: float = 0.0  # How well-documented / readable is the source?

    # Derived
    tags: list[str] = field(default_factory=list)
    estimated_instruction_steps: int = 0
    dependencies_external: list[str] = field(default_factory=list)
    dependencies_internal: list[str] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        """Weighted composite score for ranking candidates."""
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
