"""File-based JSON storage for approval requests.

Provides CRUD and decision operations for approval workflows,
backed by JSON files under ~/.ale/approvals/.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class ApprovalStore:
    """File-based storage for approval requests.

    Storage path: ``~/.ale/approvals/`` with:
    - ``requests.json`` -- list of approval request dicts
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        if base_dir is None:
            self._base = Path.home() / ".ale" / "approvals"
        else:
            self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._requests_path = self._base / "requests.json"

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
    # Approval request CRUD
    # ------------------------------------------------------------------

    def create_request(
        self,
        library_name: str,
        library_version: str,
        requester_id: str,
        policy_id: str,
        reason: str = "",
    ) -> dict:
        """Create a new approval request. Returns the request dict."""
        now = datetime.utcnow().isoformat()
        request = {
            "id": str(uuid.uuid4()),
            "library_name": library_name,
            "library_version": library_version,
            "requester_id": requester_id,
            "policy_id": policy_id,
            "reason": reason,
            "status": "pending",
            "created_at": now,
            "decided_at": "",
            "decided_by": "",
            "decision_comment": "",
        }
        requests = self._read_json(self._requests_path)
        requests.append(request)
        self._write_json(self._requests_path, requests)
        return request

    def get_request(self, request_id: str) -> Optional[dict]:
        """Look up an approval request by ID. Returns None if not found."""
        for r in self._read_json(self._requests_path):
            if r["id"] == request_id:
                return r
        return None

    def list_requests(self, status: Optional[str] = None) -> list[dict]:
        """Return all approval requests, optionally filtered by status."""
        requests = self._read_json(self._requests_path)
        if status:
            requests = [r for r in requests if r.get("status") == status]
        return requests

    def approve(self, request_id: str, approver_id: str, comment: str = "") -> Optional[dict]:
        """Approve a pending request. Returns updated dict or None."""
        requests = self._read_json(self._requests_path)
        for r in requests:
            if r["id"] == request_id:
                if r["status"] != "pending":
                    return r  # Already decided
                r["status"] = "approved"
                r["decided_at"] = datetime.utcnow().isoformat()
                r["decided_by"] = approver_id
                r["decision_comment"] = comment
                self._write_json(self._requests_path, requests)
                return r
        return None

    def reject(self, request_id: str, approver_id: str, comment: str = "") -> Optional[dict]:
        """Reject a pending request. Returns updated dict or None."""
        requests = self._read_json(self._requests_path)
        for r in requests:
            if r["id"] == request_id:
                if r["status"] != "pending":
                    return r  # Already decided
                r["status"] = "rejected"
                r["decided_at"] = datetime.utcnow().isoformat()
                r["decided_by"] = approver_id
                r["decision_comment"] = comment
                self._write_json(self._requests_path, requests)
                return r
        return None

    def get_pending_count(self) -> int:
        """Return the number of pending approval requests."""
        return len(self.list_requests(status="pending"))
