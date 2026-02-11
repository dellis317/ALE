"""Tests for bidirectional sync primitives (policy, provenance, drift)."""

import tempfile
from pathlib import Path

import yaml

from ale.models.agentic_library import ProvenanceRecord
from ale.sync.policy import (
    PolicyAction,
    PolicyContext,
    PolicyRule,
    PolicyScope,
    PolicySet,
    load_policy,
)
from ale.sync.provenance import ProvenanceStore


# --- Policy Tests ---


def test_policy_allow_by_default():
    policy = PolicySet(name="empty", rules=[])
    ctx = PolicyContext(library_name="test", library_version="1.0.0")
    decision = policy.evaluate(ctx)
    assert decision.allowed


def test_policy_deny_rule():
    policy = PolicySet(
        name="strict",
        rules=[
            PolicyRule(
                name="no-auth-changes",
                description="Block changes to auth files",
                scope=PolicyScope.FILE,
                action=PolicyAction.DENY,
                patterns=["*.auth.*", "*/auth/*"],
            ),
        ],
    )
    ctx = PolicyContext(
        library_name="test",
        library_version="1.0.0",
        target_files=["src/auth/handler.py"],
    )
    decision = policy.evaluate(ctx)
    assert not decision.allowed
    assert decision.action == PolicyAction.DENY


def test_policy_require_approval():
    policy = PolicySet(
        name="review",
        rules=[
            PolicyRule(
                name="review-crypto",
                description="Crypto changes need approval",
                scope=PolicyScope.CAPABILITY,
                action=PolicyAction.REQUIRE_APPROVAL,
                patterns=["crypto"],
            ),
        ],
    )
    ctx = PolicyContext(
        library_name="test",
        library_version="1.0.0",
        capabilities_used=["crypto"],
    )
    decision = policy.evaluate(ctx)
    assert decision.action == PolicyAction.REQUIRE_APPROVAL


def test_policy_no_match():
    policy = PolicySet(
        name="selective",
        rules=[
            PolicyRule(
                name="block-db",
                description="No database changes",
                scope=PolicyScope.CAPABILITY,
                action=PolicyAction.DENY,
                patterns=["database"],
            ),
        ],
    )
    ctx = PolicyContext(
        library_name="test",
        library_version="1.0.0",
        capabilities_used=["http_client"],
    )
    decision = policy.evaluate(ctx)
    assert decision.allowed


def test_policy_load_from_yaml():
    data = {
        "name": "test-policy",
        "version": "1.0.0",
        "rules": [
            {
                "name": "no-secrets",
                "description": "Block changes to secrets",
                "scope": "file",
                "action": "deny",
                "patterns": ["*.env", "*.secret"],
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(data, f)
        f.flush()
        policy = load_policy(f.name)

    assert policy.name == "test-policy"
    assert len(policy.rules) == 1
    assert policy.rules[0].action == PolicyAction.DENY


def test_policy_deny_overrides_allow():
    policy = PolicySet(
        name="mixed",
        rules=[
            PolicyRule(
                name="allow-all",
                description="Allow everything",
                scope=PolicyScope.ALL,
                action=PolicyAction.ALLOW,
            ),
            PolicyRule(
                name="block-library",
                description="Block specific library",
                scope=PolicyScope.LIBRARY,
                action=PolicyAction.DENY,
                patterns=["dangerous-*"],
            ),
        ],
    )
    ctx = PolicyContext(library_name="dangerous-lib", library_version="1.0.0")
    decision = policy.evaluate(ctx)
    assert not decision.allowed


# --- Provenance Tests ---


def test_provenance_store_record_and_retrieve():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ProvenanceStore(tmpdir)
        record = ProvenanceRecord(
            library_name="rate-limiter",
            library_version="1.0.0",
            applied_by="ale-test",
            validation_passed=True,
        )
        store.record(record)

        history = store.get_history("rate-limiter")
        assert len(history) == 1
        assert history[0].library_name == "rate-limiter"
        assert history[0].applied_at != ""  # Should be auto-filled


def test_provenance_store_multiple_records():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ProvenanceStore(tmpdir)
        store.record(
            ProvenanceRecord(library_name="lib-a", library_version="1.0.0", applied_by="test")
        )
        store.record(
            ProvenanceRecord(library_name="lib-b", library_version="2.0.0", applied_by="test")
        )
        store.record(
            ProvenanceRecord(library_name="lib-a", library_version="1.1.0", applied_by="test")
        )

        all_history = store.get_history()
        assert len(all_history) == 3

        lib_a = store.get_history("lib-a")
        assert len(lib_a) == 2

        latest = store.get_latest("lib-a")
        assert latest.library_version == "1.1.0"


def test_provenance_store_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ProvenanceStore(tmpdir)
        assert store.get_history() == []
        assert store.get_latest("nonexistent") is None
