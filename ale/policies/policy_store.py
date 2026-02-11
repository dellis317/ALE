"""File-based JSON storage for policy data.

Provides CRUD operations for policies backed by JSON files under ~/.ale/policies/.
Integrates with the core ale.sync.policy module for evaluation.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class PolicyStore:
    """File-based storage for policies.

    Storage path: ``~/.ale/policies/`` with:
    - ``policies.json`` -- list of policy dicts
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        if base_dir is None:
            self._base = Path.home() / ".ale" / "policies"
        else:
            self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._policies_path = self._base / "policies.json"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_json(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _write_json(self, path: Path, data: list[dict]) -> None:
        path.write_text(json.dumps(data, indent=2, default=str))

    # ------------------------------------------------------------------
    # Policy CRUD
    # ------------------------------------------------------------------

    def create_policy(self, name: str, description: str = "", rules: Optional[list[dict]] = None) -> dict:
        """Create a new policy and persist it. Returns the policy dict."""
        now = datetime.utcnow().isoformat()
        policy = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "rules": rules or [],
            "version": "1.0.0",
            "created_at": now,
            "updated_at": now,
            "enabled": True,
        }
        policies = self._read_json(self._policies_path)
        policies.append(policy)
        self._write_json(self._policies_path, policies)
        return policy

    def get_policy(self, policy_id: str) -> Optional[dict]:
        """Look up a policy by ID. Returns None if not found."""
        for p in self._read_json(self._policies_path):
            if p["id"] == policy_id:
                return p
        return None

    def list_policies(self) -> list[dict]:
        """Return all policies."""
        return self._read_json(self._policies_path)

    def update_policy(self, policy_id: str, **kwargs: object) -> Optional[dict]:
        """Update fields on an existing policy. Returns updated dict or None."""
        policies = self._read_json(self._policies_path)
        for p in policies:
            if p["id"] == policy_id:
                for key, value in kwargs.items():
                    if key in ("name", "description", "rules", "version", "enabled"):
                        p[key] = value
                p["updated_at"] = datetime.utcnow().isoformat()
                self._write_json(self._policies_path, policies)
                return p
        return None

    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy by ID. Returns True if deleted."""
        policies = self._read_json(self._policies_path)
        original_len = len(policies)
        policies = [p for p in policies if p["id"] != policy_id]
        if len(policies) < original_len:
            self._write_json(self._policies_path, policies)
            return True
        return False

    def toggle_policy(self, policy_id: str, enabled: bool) -> Optional[dict]:
        """Enable or disable a policy. Returns updated dict or None."""
        return self.update_policy(policy_id, enabled=enabled)

    def evaluate_policies(
        self,
        library_name: str,
        library_version: str = "1.0.0",
        target_files: Optional[list[str]] = None,
        capabilities: Optional[list[str]] = None,
    ) -> dict:
        """Evaluate ALL enabled policies against the given context.

        Uses the core ale.sync.policy module for matching logic.
        Returns a combined decision dict.
        """
        from ale.sync.policy import (
            PolicyAction,
            PolicyContext,
            PolicyRule,
            PolicyScope,
            PolicySet,
        )

        context = PolicyContext(
            library_name=library_name,
            library_version=library_version,
            target_files=target_files or [],
            capabilities_used=capabilities or [],
        )

        all_matched_rules: list[dict] = []
        combined_action = PolicyAction.ALLOW

        for policy_dict in self.list_policies():
            if not policy_dict.get("enabled", True):
                continue

            # Convert stored rule dicts into PolicyRule dataclass instances
            core_rules: list[PolicyRule] = []
            for r in policy_dict.get("rules", []):
                try:
                    scope = PolicyScope(r.get("scope", "all"))
                except ValueError:
                    scope = PolicyScope.ALL
                try:
                    action = PolicyAction(r.get("action", "allow"))
                except ValueError:
                    action = PolicyAction.ALLOW

                core_rules.append(
                    PolicyRule(
                        name=r.get("name", ""),
                        description=r.get("description", ""),
                        scope=scope,
                        action=action,
                        patterns=r.get("patterns", []),
                        conditions=r.get("conditions", {}),
                        rationale=r.get("rationale", ""),
                    )
                )

            policy_set = PolicySet(
                name=policy_dict.get("name", "unnamed"),
                version=policy_dict.get("version", "1.0.0"),
                rules=core_rules,
            )

            decision = policy_set.evaluate(context)

            for rule in decision.applied_rules:
                all_matched_rules.append({
                    "name": rule.name,
                    "description": rule.description,
                    "scope": rule.scope.value,
                    "action": rule.action.value,
                    "rationale": rule.rationale,
                    "policy_id": policy_dict["id"],
                    "policy_name": policy_dict["name"],
                })

            # Escalate: deny > require_approval > allow
            if decision.action == PolicyAction.DENY:
                combined_action = PolicyAction.DENY
            elif (
                decision.action == PolicyAction.REQUIRE_APPROVAL
                and combined_action != PolicyAction.DENY
            ):
                combined_action = PolicyAction.REQUIRE_APPROVAL

        reasons = [
            f"[{r['action']}] {r['name']}: {r['description']}"
            for r in all_matched_rules
        ]

        return {
            "allowed": combined_action == PolicyAction.ALLOW,
            "action": combined_action.value,
            "matched_rules": all_matched_rules,
            "reasons": reasons,
        }
