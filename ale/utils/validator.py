"""Validator — check Agentic Library spec files for correctness.

This module provides a simplified validation interface. For full executable
spec validation (schema + semantic + reference runner), use ale.spec directly.
"""

from pathlib import Path

import yaml

from ale.spec.schema_validator import validate_schema
from ale.spec.semantic_validator import validate_semantics


REQUIRED_MANIFEST_FIELDS = {"name", "version", "description"}
VALID_SEVERITIES = {"must", "should", "may"}
VALID_COMPLEXITIES = {"trivial", "simple", "moderate", "complex"}


def validate_library(library_path: str) -> list[str]:
    """Validate an Agentic Library YAML file.

    Runs both schema validation and basic structural checks.
    Returns a list of issues found. Empty list means valid.
    """
    issues: list[str] = []
    path = Path(library_path)

    if not path.exists():
        return [f"File not found: {library_path}"]

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"Invalid YAML: {e}"]

    if not isinstance(data, dict) or "agentic_library" not in data:
        return ["Missing top-level 'agentic_library' key"]

    lib = data["agentic_library"]

    # Basic structural validation (backward-compatible checks)
    manifest = lib.get("manifest", {})
    for field_name in REQUIRED_MANIFEST_FIELDS:
        if not manifest.get(field_name):
            issues.append(f"Manifest missing required field: {field_name}")

    complexity = manifest.get("complexity", "")
    if complexity and complexity not in VALID_COMPLEXITIES:
        issues.append(f"Invalid complexity '{complexity}'. Must be one of: {VALID_COMPLEXITIES}")

    instructions = lib.get("instructions", [])
    if not instructions:
        issues.append("No instructions defined — library must have at least one step")
    else:
        for i, step in enumerate(instructions):
            if not step.get("title"):
                issues.append(f"Instruction step {i + 1} missing 'title'")
            if not step.get("description"):
                issues.append(f"Instruction step {i + 1} missing 'description'")

    for i, guardrail in enumerate(lib.get("guardrails", [])):
        if not guardrail.get("rule"):
            issues.append(f"Guardrail {i + 1} missing 'rule'")
        severity = guardrail.get("severity", "")
        if severity and severity not in VALID_SEVERITIES:
            issues.append(f"Guardrail {i + 1} invalid severity '{severity}'")

    for i, criterion in enumerate(lib.get("validation", [])):
        if not criterion.get("description"):
            issues.append(f"Validation criterion {i + 1} missing 'description'")

    return issues
