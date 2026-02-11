"""Tests for the executable specification (schema + semantic validator)."""

import tempfile

import yaml

from ale.spec import SPEC_VERSION
from ale.spec.schema import get_schema
from ale.spec.schema_validator import validate_schema
from ale.spec.semantic_validator import Severity, validate_semantics


def _make_valid_library(**overrides) -> dict:
    """Build a minimal valid agentic library dict."""
    data = {
        "agentic_library": {
            "manifest": {
                "name": "test-lib",
                "version": "1.0.0",
                "spec_version": SPEC_VERSION,
                "description": "A test library for validation",
            },
            "overview": "This is a test library that does useful things for testing.",
            "instructions": [
                {
                    "step": 1,
                    "title": "Implement the feature",
                    "description": "Create the main module with the core logic as described.",
                },
            ],
            "guardrails": [
                {
                    "rule": "Follow the target project coding conventions",
                    "severity": "must",
                },
            ],
            "validation": [
                {
                    "description": "Feature works correctly",
                    "test_approach": "Run the test suite",
                    "expected_behavior": "All tests pass",
                },
            ],
        }
    }
    lib = data["agentic_library"]
    for key, value in overrides.items():
        if key in lib:
            lib[key] = value
        elif key.startswith("manifest."):
            lib["manifest"][key.split(".", 1)[1]] = value
    return data


# --- Schema Tests ---


def test_schema_exists():
    schema = get_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert "agentic_library" in schema["properties"]


def test_schema_valid_library():
    data = _make_valid_library()
    issues = validate_schema(data)
    assert issues == [], f"Valid library should have no issues: {issues}"


def test_schema_missing_top_level():
    issues = validate_schema({"not_a_library": {}})
    assert any("agentic_library" in i for i in issues)


def test_schema_missing_manifest_name():
    data = _make_valid_library()
    del data["agentic_library"]["manifest"]["name"]
    issues = validate_schema(data)
    assert any("name" in i for i in issues)


def test_schema_invalid_name_pattern():
    data = _make_valid_library()
    data["agentic_library"]["manifest"]["name"] = "InvalidName"
    issues = validate_schema(data)
    assert any("pattern" in i.lower() or "match" in i.lower() for i in issues)


def test_schema_empty_instructions():
    data = _make_valid_library()
    data["agentic_library"]["instructions"] = []
    issues = validate_schema(data)
    assert any("min" in i.lower() for i in issues)


def test_schema_empty_guardrails():
    data = _make_valid_library()
    data["agentic_library"]["guardrails"] = []
    issues = validate_schema(data)
    assert any("min" in i.lower() for i in issues)


def test_schema_invalid_severity():
    data = _make_valid_library()
    data["agentic_library"]["guardrails"][0]["severity"] = "absolutely"
    issues = validate_schema(data)
    assert any("allowed" in i.lower() or "enum" in i.lower() for i in issues)


def test_schema_invalid_complexity():
    data = _make_valid_library()
    data["agentic_library"]["manifest"]["complexity"] = "impossible"
    issues = validate_schema(data)
    assert any("allowed" in i.lower() or "enum" in i.lower() for i in issues)


# --- Semantic Validator Tests ---


def test_semantic_valid_library():
    data = _make_valid_library()
    result = validate_semantics(data)
    assert result.passed, f"Valid library should pass: {[i.message for i in result.errors]}"


def test_semantic_missing_spec_version():
    data = _make_valid_library()
    del data["agentic_library"]["manifest"]["spec_version"]
    result = validate_semantics(data)
    assert not result.passed
    assert any(i.code == "SPEC_VERSION_MISSING" for i in result.errors)


def test_semantic_instruction_ordering():
    data = _make_valid_library()
    data["agentic_library"]["instructions"] = [
        {"step": 1, "title": "First", "description": "First step of the implementation"},
        {"step": 3, "title": "Third", "description": "This should be step 2 not step 3"},
    ]
    result = validate_semantics(data)
    assert any(i.code == "INSTRUCTION_ORDER" for i in result.issues)


def test_semantic_undeclared_capability():
    data = _make_valid_library()
    data["agentic_library"]["instructions"][0]["capabilities_used"] = ["http_client"]
    # No capability_dependencies declared
    result = validate_semantics(data)
    assert any(i.code == "UNDECLARED_CAPABILITY" for i in result.errors)


def test_semantic_declared_capability_passes():
    data = _make_valid_library()
    data["agentic_library"]["instructions"][0]["capabilities_used"] = ["http_client"]
    data["agentic_library"]["capability_dependencies"] = ["http_client"]
    result = validate_semantics(data)
    assert not any(i.code == "UNDECLARED_CAPABILITY" for i in result.issues)


def test_semantic_no_validation_hooks_warning():
    data = _make_valid_library()
    result = validate_semantics(data)
    assert any(i.code == "NO_VALIDATION_HOOKS" for i in result.warnings)


def test_semantic_with_validation_hook_no_warning():
    data = _make_valid_library()
    data["agentic_library"]["validation"][0]["hook"] = {
        "type": "command",
        "command": "pytest",
    }
    result = validate_semantics(data)
    assert not any(i.code == "NO_VALIDATION_HOOKS" for i in result.warnings)


def test_semantic_guardrail_enforcement_warning():
    data = _make_valid_library()
    # Must guardrail without enforcement field triggers warning
    result = validate_semantics(data)
    assert any(i.code == "GUARDRAIL_ENFORCEMENT_MISSING" for i in result.warnings)


def test_semantic_result_summary():
    data = _make_valid_library()
    result = validate_semantics(data)
    summary = result.summary()
    assert "PASS" in summary or "FAIL" in summary
