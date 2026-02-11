"""Tests for the Agentic Library validator."""

import tempfile
from pathlib import Path

import yaml

from ale.utils.validator import validate_library


def _write_yaml(data: dict) -> str:
    """Write a dict to a temporary YAML file and return the path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(data, f)
    f.close()
    return f.name


def test_valid_library():
    data = {
        "agentic_library": {
            "manifest": {
                "name": "test",
                "version": "1.0.0",
                "description": "A test library",
                "complexity": "simple",
            },
            "instructions": [
                {"step": 1, "title": "Do it", "description": "Do the thing"},
            ],
            "guardrails": [
                {"rule": "Be safe", "severity": "must"},
            ],
            "validation": [
                {"description": "It works"},
            ],
        }
    }
    issues = validate_library(_write_yaml(data))
    assert issues == []


def test_missing_manifest_fields():
    data = {
        "agentic_library": {
            "manifest": {"name": "test"},
            "instructions": [{"step": 1, "title": "X", "description": "Y"}],
        }
    }
    issues = validate_library(_write_yaml(data))
    assert any("version" in i for i in issues)
    assert any("description" in i for i in issues)


def test_missing_instructions():
    data = {
        "agentic_library": {
            "manifest": {"name": "test", "version": "1.0.0", "description": "X"},
            "instructions": [],
        }
    }
    issues = validate_library(_write_yaml(data))
    assert any("No instructions" in i for i in issues)


def test_invalid_complexity():
    data = {
        "agentic_library": {
            "manifest": {
                "name": "test",
                "version": "1.0.0",
                "description": "X",
                "complexity": "impossible",
            },
            "instructions": [{"step": 1, "title": "X", "description": "Y"}],
        }
    }
    issues = validate_library(_write_yaml(data))
    assert any("complexity" in i.lower() for i in issues)


def test_invalid_guardrail_severity():
    data = {
        "agentic_library": {
            "manifest": {"name": "test", "version": "1.0.0", "description": "X"},
            "instructions": [{"step": 1, "title": "X", "description": "Y"}],
            "guardrails": [{"rule": "Be safe", "severity": "absolutely"}],
        }
    }
    issues = validate_library(_write_yaml(data))
    assert any("severity" in i for i in issues)


def test_file_not_found():
    issues = validate_library("/nonexistent/path.yaml")
    assert any("not found" in i.lower() for i in issues)


def test_invalid_yaml():
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write("{{invalid yaml::: [")
    f.close()
    issues = validate_library(f.name)
    assert any("yaml" in i.lower() for i in issues)
