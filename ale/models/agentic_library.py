"""Core data models for the Agentic Library specification."""

from dataclasses import dataclass, field
from enum import Enum


class Complexity(Enum):
    """How complex the agentic library is to implement."""

    TRIVIAL = "trivial"  # Single function, <20 lines of logic
    SIMPLE = "simple"  # A few functions, single module
    MODERATE = "moderate"  # Multiple modules, some coordination
    COMPLEX = "complex"  # Multi-module with state, side effects, integrations


class CapabilityDependency(Enum):
    """Abstract capabilities the target project must provide (not specific libraries)."""

    HTTP_CLIENT = "http_client"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    CRYPTO = "crypto"
    LOGGING = "logging"
    CACHING = "caching"
    QUEUE = "queue"
    AUTH = "auth"
    WEBSOCKET = "websocket"
    CLI = "cli"


@dataclass
class Guardrail:
    """A constraint or rule the implementation must follow."""

    rule: str
    severity: str = "must"  # must | should | may
    rationale: str = ""


@dataclass
class ValidationCriterion:
    """A testable condition that verifies correct implementation."""

    description: str
    test_approach: str  # How an agent should verify this
    expected_behavior: str


@dataclass
class InstructionStep:
    """A single step in the implementation instructions."""

    order: int
    title: str
    description: str
    code_sketch: str = ""  # Pseudocode or language-agnostic sketch
    notes: str = ""


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
    description: str = ""
    source_repo: str = ""  # Git URL of the source repo
    source_paths: list[str] = field(default_factory=list)  # Files in source that informed this
    complexity: Complexity = Complexity.MODERATE
    tags: list[str] = field(default_factory=list)

    # --- Instructions ---
    overview: str = ""  # High-level explanation of what this does and why
    instructions: list[InstructionStep] = field(default_factory=list)

    # --- Guardrails ---
    guardrails: list[Guardrail] = field(default_factory=list)

    # --- Validation ---
    validation: list[ValidationCriterion] = field(default_factory=list)

    # --- Dependencies ---
    capability_deps: list[CapabilityDependency] = field(default_factory=list)

    # --- Metadata ---
    language_agnostic: bool = True  # Can this be implemented in any language?
    target_languages: list[str] = field(default_factory=list)  # If not agnostic, which languages?
    framework_hints: dict[str, str] = field(default_factory=dict)  # framework -> implementation notes
