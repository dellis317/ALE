"""Semantic validator for Agentic Libraries.

Goes beyond JSON Schema structural validation to check semantic rules:
- Instruction steps are ordered and scoped
- Capabilities referenced in instructions are declared in dependencies
- Guardrails have enforceable content (not purely prose)
- Validation has at least one runnable hook
- Examples correspond to declared compatibility targets
- Abstraction boundary is consistent with instructions

This is gate 2 of 3 in the executable specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    ERROR = "error"  # Blocks conformance
    WARNING = "warning"  # Should fix but not blocking
    INFO = "info"  # Suggestion


@dataclass
class ValidationIssue:
    """A single issue found during semantic validation."""

    severity: Severity
    code: str  # Machine-readable issue code
    message: str
    path: str = ""  # JSONPath-style location (e.g., "instructions[2].capabilities_used")


@dataclass
class SemanticValidationResult:
    """Result of semantic validation on an Agentic Library."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    def summary(self) -> str:
        e = len(self.errors)
        w = len(self.warnings)
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {e} error(s), {w} warning(s)"


def validate_semantics(data: dict) -> SemanticValidationResult:
    """Run semantic validation on a parsed Agentic Library dict.

    Args:
        data: The full parsed YAML/JSON dict (with top-level 'agentic_library' key).

    Returns:
        SemanticValidationResult with all issues found.
    """
    result = SemanticValidationResult()
    lib = data.get("agentic_library", {})

    _check_spec_version(lib, result)
    _check_instruction_ordering(lib, result)
    _check_capability_references(lib, result)
    _check_guardrail_enforceability(lib, result)
    _check_validation_hooks(lib, result)
    _check_compatibility_coverage(lib, result)
    _check_abstraction_boundary(lib, result)

    return result


def _check_spec_version(lib: dict, result: SemanticValidationResult):
    """Verify spec_version is declared in manifest."""
    manifest = lib.get("manifest", {})
    if not manifest.get("spec_version"):
        result.issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="SPEC_VERSION_MISSING",
                message="Manifest must declare 'spec_version' to indicate which spec it targets.",
                path="manifest.spec_version",
            )
        )


def _check_instruction_ordering(lib: dict, result: SemanticValidationResult):
    """Verify instructions are sequentially ordered starting from 1."""
    instructions = lib.get("instructions", [])
    if not instructions:
        return

    steps = [s.get("step", 0) for s in instructions]
    expected = list(range(1, len(instructions) + 1))

    if steps != expected:
        result.issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code="INSTRUCTION_ORDER",
                message=(
                    f"Instruction steps must be sequentially ordered starting from 1. "
                    f"Got: {steps}, expected: {expected}"
                ),
                path="instructions",
            )
        )


def _check_capability_references(lib: dict, result: SemanticValidationResult):
    """Verify capabilities used in instructions are declared in dependencies."""
    declared_deps = set()
    for dep in lib.get("capability_dependencies", []):
        if isinstance(dep, str):
            declared_deps.add(dep)
        elif isinstance(dep, dict):
            declared_deps.add(dep.get("capability", ""))

    for i, step in enumerate(lib.get("instructions", [])):
        for cap in step.get("capabilities_used", []):
            if cap not in declared_deps:
                result.issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        code="UNDECLARED_CAPABILITY",
                        message=(
                            f"Instruction step {i + 1} references capability '{cap}' "
                            f"but it is not declared in capability_dependencies."
                        ),
                        path=f"instructions[{i}].capabilities_used",
                    )
                )


def _check_guardrail_enforceability(lib: dict, result: SemanticValidationResult):
    """Check that guardrails marked 'must' have some form of enforcement signal."""
    for i, guardrail in enumerate(lib.get("guardrails", [])):
        severity = guardrail.get("severity", "")
        enforcement = guardrail.get("enforcement")
        rule = guardrail.get("rule", "")

        # 'must' guardrails should indicate how they can be enforced
        if severity == "must" and not enforcement:
            result.issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="GUARDRAIL_ENFORCEMENT_MISSING",
                    message=(
                        f"Guardrail {i + 1} has severity 'must' but no 'enforcement' field. "
                        f"Consider specifying 'machine', 'review', or 'advisory'."
                    ),
                    path=f"guardrails[{i}].enforcement",
                )
            )

        # Guardrails should have enough content to be actionable
        if len(rule) < 15:
            result.issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="GUARDRAIL_TOO_TERSE",
                    message=(
                        f"Guardrail {i + 1} rule is very short ({len(rule)} chars). "
                        f"Guardrails should be specific enough to enforce."
                    ),
                    path=f"guardrails[{i}].rule",
                )
            )


def _check_validation_hooks(lib: dict, result: SemanticValidationResult):
    """Check that validation has at least one runnable hook."""
    validations = lib.get("validation", [])
    has_hook = any(v.get("hook") for v in validations)

    if not has_hook:
        result.issues.append(
            ValidationIssue(
                severity=Severity.WARNING,
                code="NO_VALIDATION_HOOKS",
                message=(
                    "No validation criteria declare a runnable 'hook'. "
                    "Without hooks, the reference runner cannot execute validation automatically. "
                    "Consider adding at least one hook with type 'command' or 'assertion'."
                ),
                path="validation",
            )
        )


def _check_compatibility_coverage(lib: dict, result: SemanticValidationResult):
    """Check that examples reference declared compatibility targets."""
    compat_targets = {c.get("target_id") for c in lib.get("compatibility", [])}
    for i, example in enumerate(lib.get("examples", [])):
        target = example.get("target", "")
        if compat_targets and target not in compat_targets:
            result.issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="EXAMPLE_TARGET_MISMATCH",
                    message=(
                        f"Example {i + 1} targets '{target}' but that target "
                        f"is not declared in the compatibility matrix."
                    ),
                    path=f"examples[{i}].target",
                )
            )


def _check_abstraction_boundary(lib: dict, result: SemanticValidationResult):
    """Check that abstraction boundary is present and consistent."""
    boundary = lib.get("abstraction_boundary")
    manifest = lib.get("manifest", {})

    if not boundary:
        if not manifest.get("language_agnostic", True):
            result.issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    code="MISSING_ABSTRACTION_BOUNDARY",
                    message=(
                        "Library is not language-agnostic but has no 'abstraction_boundary'. "
                        "Consider declaring scope, assumptions, and integration points."
                    ),
                    path="abstraction_boundary",
                )
            )
        return

    if not boundary.get("assumptions"):
        result.issues.append(
            ValidationIssue(
                severity=Severity.INFO,
                code="NO_ASSUMPTIONS_DECLARED",
                message=(
                    "Abstraction boundary has no 'assumptions'. "
                    "Consider declaring what must be true about the target project."
                ),
                path="abstraction_boundary.assumptions",
            )
        )
