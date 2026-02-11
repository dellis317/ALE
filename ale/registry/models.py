"""Registry data models — catalog entries, quality signals, and search."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VerificationResult:
    """Result of running the executable spec against a library."""

    schema_passed: bool = False
    validator_passed: bool = False
    hooks_runnable: bool = False
    verified_at: str = ""  # ISO 8601
    verified_by: str = ""  # Tool identifier


@dataclass
class QualitySignals:
    """Quality signals visible at discovery/selection time."""

    verification: VerificationResult = field(default_factory=VerificationResult)
    rating: float = 0.0  # 0.0 - 5.0 aggregate
    rating_count: int = 0
    download_count: int = 0
    maintained: bool = True
    maintainer: str = ""
    last_updated: str = ""


@dataclass
class RegistryEntry:
    """A single entry in the Agentic Library registry."""

    # Identity
    name: str
    version: str
    spec_version: str = ""
    description: str = ""

    # Classification
    tags: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    complexity: str = ""
    language_agnostic: bool = True
    target_languages: list[str] = field(default_factory=list)

    # Quality
    quality: QualitySignals = field(default_factory=QualitySignals)

    # Source
    source_repo: str = ""
    library_path: str = ""  # Path to the .agentic.yaml file

    # Compatibility
    compatibility_targets: list[str] = field(default_factory=list)

    @property
    def qualified_id(self) -> str:
        return f"{self.name}@{self.version}"

    @property
    def is_verified(self) -> bool:
        v = self.quality.verification
        return v.schema_passed and v.validator_passed


@dataclass
class SearchQuery:
    """Query for searching the registry."""

    text: str = ""
    tags: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)
    verified_only: bool = False
    min_rating: float = 0.0
    max_complexity: str = ""


@dataclass
class SearchResult:
    """Result of a registry search."""

    entries: list[RegistryEntry] = field(default_factory=list)
    total_count: int = 0
    query: SearchQuery = field(default_factory=SearchQuery)
