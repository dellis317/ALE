"""Tests for the local registry."""

import tempfile
from pathlib import Path

import yaml

from ale.registry.local_registry import LocalRegistry
from ale.registry.models import SearchQuery
from ale.spec import SPEC_VERSION


def _write_library(tmpdir: str, name: str = "test-lib", **overrides) -> str:
    """Write a valid agentic library YAML to a temp file."""
    data = {
        "agentic_library": {
            "manifest": {
                "name": name,
                "version": overrides.get("version", "1.0.0"),
                "spec_version": SPEC_VERSION,
                "description": f"A test library called {name} for testing",
                "tags": overrides.get("tags", ["test"]),
                "complexity": "simple",
            },
            "overview": "This is a test library for registry testing purposes.",
            "instructions": [
                {
                    "step": 1,
                    "title": "Implement the feature",
                    "description": "Create the implementation as described in the overview.",
                },
            ],
            "guardrails": [
                {
                    "rule": "Follow project conventions and coding standards",
                    "severity": "must",
                },
            ],
            "validation": [
                {
                    "description": "Feature works as expected",
                    "test_approach": "Run test suite",
                    "expected_behavior": "Tests pass",
                },
            ],
            "capability_dependencies": overrides.get("capabilities", []),
        }
    }
    path = Path(tmpdir) / f"{name}.agentic.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f)
    return str(path)


def test_publish_and_get():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = LocalRegistry(Path(tmpdir) / "registry")
        lib_path = _write_library(tmpdir, "my-lib")

        entry = reg.publish(lib_path)
        assert entry.name == "my-lib"
        assert entry.version == "1.0.0"
        assert entry.is_verified  # Should pass schema + semantics

        retrieved = reg.get("my-lib")
        assert retrieved is not None
        assert retrieved.name == "my-lib"


def test_publish_multiple_versions():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = LocalRegistry(Path(tmpdir) / "registry")

        _write_library(tmpdir, "versioned-lib")
        reg.publish(Path(tmpdir) / "versioned-lib.agentic.yaml")

        # Overwrite with v2
        path2 = _write_library(tmpdir, "versioned-lib", version="2.0.0")
        reg.publish(path2)

        entries = reg.list_all()
        assert len(entries) == 2

        # Get latest
        latest = reg.get("versioned-lib")
        assert latest.version == "2.0.0"

        # Get specific version
        v1 = reg.get("versioned-lib", "1.0.0")
        assert v1 is not None
        assert v1.version == "1.0.0"


def test_list_all():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = LocalRegistry(Path(tmpdir) / "registry")
        _write_library(tmpdir, "lib-a")
        _write_library(tmpdir, "lib-b")
        reg.publish(Path(tmpdir) / "lib-a.agentic.yaml")
        reg.publish(Path(tmpdir) / "lib-b.agentic.yaml")

        entries = reg.list_all()
        assert len(entries) == 2
        names = {e.name for e in entries}
        assert "lib-a" in names
        assert "lib-b" in names


def test_search_by_text():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = LocalRegistry(Path(tmpdir) / "registry")
        _write_library(tmpdir, "rate-limiter")
        _write_library(tmpdir, "auth-helper")
        reg.publish(Path(tmpdir) / "rate-limiter.agentic.yaml")
        reg.publish(Path(tmpdir) / "auth-helper.agentic.yaml")

        result = reg.search(SearchQuery(text="rate"))
        assert len(result.entries) == 1
        assert result.entries[0].name == "rate-limiter"


def test_search_by_tag():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = LocalRegistry(Path(tmpdir) / "registry")
        _write_library(tmpdir, "tagged-lib", tags=["networking", "security"])
        _write_library(tmpdir, "other-lib", tags=["ui"])
        reg.publish(Path(tmpdir) / "tagged-lib.agentic.yaml")
        reg.publish(Path(tmpdir) / "other-lib.agentic.yaml")

        result = reg.search(SearchQuery(tags=["security"]))
        assert len(result.entries) == 1
        assert result.entries[0].name == "tagged-lib"


def test_search_verified_only():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = LocalRegistry(Path(tmpdir) / "registry")
        _write_library(tmpdir, "valid-lib")
        reg.publish(Path(tmpdir) / "valid-lib.agentic.yaml")

        result = reg.search(SearchQuery(verified_only=True))
        assert all(e.is_verified for e in result.entries)


def test_get_nonexistent():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = LocalRegistry(Path(tmpdir) / "registry")
        assert reg.get("nonexistent") is None


def test_empty_registry():
    with tempfile.TemporaryDirectory() as tmpdir:
        reg = LocalRegistry(Path(tmpdir) / "registry")
        assert reg.list_all() == []
        result = reg.search(SearchQuery(text="anything"))
        assert result.total_count == 0
