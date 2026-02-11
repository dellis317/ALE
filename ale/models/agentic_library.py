"""Core data models for the Agentic Library specification.

Aligned with the executable specification (ale.spec) and the architecture doc.
Covers: manifest, instructions, guardrails, validation, dependencies,
abstraction boundaries, compatibility matrix, migration guidance, and provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ale.spec import SPEC_VERSION


class Complexity(Enum):
    """How complex the agentic library is to implement."""

    TRIVIAL = "trivial"  # Single function, <20 lines of logic
    SIMPLE = "simple"  # A few functions, single module
    MODERATE = "moderate"  # Multiple modules, some coordination
    COMPLEX = "complex"  # Multi-module with state, side effects, integrations


class GuardrailEnforcement(Enum):
    """How a guardrail can be enforced."""

    MACHINE = "machine"  # Can be checked automatically
    REVIEW = "review"  # Requires human review
    ADVISORY = "advisory"  # Guidance only


class CompatibilityStatus(Enum):
    """Status of compatibility with a target."""

    SUPPORTED = "supported"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


# --- Instruction ---


@dataclass
class InstructionStep:
    """A single step in the implementation instructions."""

    order: int
    title: str
    description: str
    code_sketch: str = ""
    notes: str = ""
    preconditions: list[str] = field(default_factory=list)
    touched_surfaces: list[str] = field(default_factory=list)
    capabilities_used: list[str] = field(default_factory=list)


# --- Guardrails ---


@dataclass
class Guardrail:
    """A constraint or rule the implementation must follow."""

    rule: str
    severity: str = "must"  # must | should | may
    rationale: str = ""
    enforcement: GuardrailEnforcement | None = None
    check_command: str = ""


# --- Validation ---


@dataclass
class ValidationHook:
    """A runnable validation hook for the reference runner."""

    type: str  # command | script | assertion
    command: str = ""
    timeout_seconds: int = 60
    expected_exit_code: int = 0


@dataclass
class ValidationCriterion:
    """A testable condition that verifies correct implementation."""

    description: str
    test_approach: str
    expected_behavior: str
    hook: ValidationHook | None = None


# --- Dependencies ---


@dataclass
class CapabilityDep:
    """An abstract capability the target project must provide."""

    capability: str
    required: bool = True
    description: str = ""


# --- Abstraction Boundary ---


@dataclass
class AbstractionBoundary:
    """Explicit declaration of what this library assumes and touches."""

    scope: str = ""
    assumptions: list[str] = field(default_factory=list)
    integration_points: list[str] = field(default_factory=list)
    does_not_touch: list[str] = field(default_factory=list)


# --- Compatibility Matrix ---


@dataclass
class CompatibilityEntry:
    """A single row in the compatibility matrix."""

    target_id: str
    target_type: str  # language | framework | runtime
    status: CompatibilityStatus = CompatibilityStatus.EXPERIMENTAL
    target_version: str = ""
    notes: str = ""


# --- Migration Guidance ---


@dataclass
class MigrationGuide:
    """Migration guidance from one version to another."""

    from_version: str
    to_version: str
    summary: str
    breaking: bool = False
    steps: list[str] = field(default_factory=list)
    rollback_guidance: str = ""


# --- Provenance ---


@dataclass
class ProvenanceRecord:
    """Auditable record of how a library was applied."""

    library_name: str
    library_version: str
    applied_at: str = ""  # ISO 8601 timestamp
    applied_by: str = ""  # Tool/runner identifier
    target_repo: str = ""
    target_branch: str = ""
    validation_passed: bool = False
    validation_evidence: str = ""  # Summary or link to detailed results
    commit_sha: str = ""


# --- Examples ---


@dataclass
class Example:
    """Reference implementation for a specific target."""

    target: str
    description: str
    code: str = ""


# --- The Full Agentic Library ---


@dataclass
class AgenticLibrary:
    """The core Agentic Library specification.

    This is what ALE produces — a complete, self-contained blueprint that any
    AI coding agent can follow to implement the described feature natively in
    any target project.
    """

    # --- Manifest ---
    name: str
    version: str = "1.0.0"
    spec_version: str = SPEC_VERSION
    description: str = ""
    source_repo: str = ""
    source_paths: list[str] = field(default_factory=list)
    complexity: Complexity = Complexity.MODERATE
    tags: list[str] = field(default_factory=list)
    language_agnostic: bool = True
    target_languages: list[str] = field(default_factory=list)

    # --- Instructions ---
    overview: str = ""
    instructions: list[InstructionStep] = field(default_factory=list)

    # --- Guardrails ---
    guardrails: list[Guardrail] = field(default_factory=list)

    # --- Validation ---
    validation: list[ValidationCriterion] = field(default_factory=list)

    # --- Dependencies ---
    capability_deps: list[CapabilityDep] = field(default_factory=list)

    # --- Abstraction Boundary ---
    abstraction_boundary: AbstractionBoundary | None = None

    # --- Compatibility Matrix ---
    compatibility: list[CompatibilityEntry] = field(default_factory=list)

    # --- Framework Hints ---
    framework_hints: dict[str, str] = field(default_factory=dict)

    # --- Migration ---
    migrations: list[MigrationGuide] = field(default_factory=list)

    # --- Examples ---
    examples: list[Example] = field(default_factory=list)
