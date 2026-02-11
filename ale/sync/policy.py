"""Policy-as-code — machine-enforceable rules governing change application.

Policies define what kinds of changes can be applied, where, and under
what conditions. They act as gates in the bidirectional sync pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml


class PolicyAction(Enum):
    """What happens when a policy rule matches."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PolicyScope(Enum):
    """What a policy rule applies to."""

    FILE = "file"  # Specific files or patterns
    DIRECTORY = "directory"  # Specific directories
    CAPABILITY = "capability"  # Capability dependencies
    LIBRARY = "library"  # Specific agentic libraries
    ALL = "all"  # Everything


@dataclass
class PolicyRule:
    """A single policy rule."""

    name: str
    description: str
    scope: PolicyScope
    action: PolicyAction
    patterns: list[str] = field(default_factory=list)  # Glob patterns for file/dir scope
    conditions: dict[str, str] = field(default_factory=dict)  # Key-value conditions
    rationale: str = ""


@dataclass
class PolicySet:
    """A collection of policy rules that govern sync behavior."""

    name: str
    version: str = "1.0.0"
    rules: list[PolicyRule] = field(default_factory=list)

    def evaluate(self, context: PolicyContext) -> PolicyDecision:
        """Evaluate all rules against a context and return a decision."""
        applied_rules = []
        denied = False
        needs_approval = False

        for rule in self.rules:
            if _rule_matches(rule, context):
                applied_rules.append(rule)
                if rule.action == PolicyAction.DENY:
                    denied = True
                elif rule.action == PolicyAction.REQUIRE_APPROVAL:
                    needs_approval = True

        if denied:
            action = PolicyAction.DENY
        elif needs_approval:
            action = PolicyAction.REQUIRE_APPROVAL
        else:
            action = PolicyAction.ALLOW

        return PolicyDecision(
            action=action,
            applied_rules=applied_rules,
            context=context,
        )


@dataclass
class PolicyContext:
    """Context for evaluating policies — what change is being proposed."""

    library_name: str
    library_version: str
    target_files: list[str] = field(default_factory=list)
    capabilities_used: list[str] = field(default_factory=list)
    target_repo: str = ""
    target_branch: str = ""


@dataclass
class PolicyDecision:
    """Result of evaluating policies."""

    action: PolicyAction
    applied_rules: list[PolicyRule] = field(default_factory=list)
    context: PolicyContext | None = None

    @property
    def allowed(self) -> bool:
        return self.action == PolicyAction.ALLOW

    @property
    def reasons(self) -> list[str]:
        return [
            f"[{r.action.value}] {r.name}: {r.description}" for r in self.applied_rules
        ]


def load_policy(path: str | Path) -> PolicySet:
    """Load a policy set from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    rules = []
    for rule_data in data.get("rules", []):
        rules.append(
            PolicyRule(
                name=rule_data["name"],
                description=rule_data.get("description", ""),
                scope=PolicyScope(rule_data.get("scope", "all")),
                action=PolicyAction(rule_data.get("action", "allow")),
                patterns=rule_data.get("patterns", []),
                conditions=rule_data.get("conditions", {}),
                rationale=rule_data.get("rationale", ""),
            )
        )

    return PolicySet(
        name=data.get("name", "unnamed"),
        version=data.get("version", "1.0.0"),
        rules=rules,
    )


def _rule_matches(rule: PolicyRule, context: PolicyContext) -> bool:
    """Check if a policy rule matches the given context."""
    if rule.scope == PolicyScope.ALL:
        return True

    if rule.scope == PolicyScope.LIBRARY:
        return any(
            _glob_match(pattern, context.library_name) for pattern in rule.patterns
        )

    if rule.scope == PolicyScope.FILE:
        return any(
            _glob_match(pattern, f)
            for pattern in rule.patterns
            for f in context.target_files
        )

    if rule.scope == PolicyScope.DIRECTORY:
        return any(
            any(f.startswith(pattern.rstrip("/")) for f in context.target_files)
            for pattern in rule.patterns
        )

    if rule.scope == PolicyScope.CAPABILITY:
        return any(
            cap in context.capabilities_used for cap in rule.patterns
        )

    return False


def _glob_match(pattern: str, value: str) -> bool:
    """Simple glob matching (supports * wildcard)."""
    import fnmatch

    return fnmatch.fnmatch(value, pattern)
