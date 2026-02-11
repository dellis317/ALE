"""Audit logging system for ALE.

Provides file-based JSON audit logging with filtering, export, and query
capabilities. All events are stored in ``~/.ale/audit_logs/``.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class AuditEntry:
    """A single audit log entry."""

    id: str
    timestamp: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    success: bool = True


class AuditLogger:
    """File-based JSON audit logger.

    Events are persisted as newline-delimited JSON in daily log files stored
    under ``~/.ale/audit_logs/``.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir or Path.home() / ".ale" / "audit_logs"
        self._base_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_file_for_date(self, dt: datetime) -> Path:
        """Return the log file path for a given date."""
        return self._base_dir / f"{dt.strftime('%Y-%m-%d')}.jsonl"

    def _current_log_file(self) -> Path:
        return self._log_file_for_date(datetime.now(timezone.utc))

    def _read_all_entries(self) -> list[AuditEntry]:
        """Read every entry from all log files."""
        entries: list[AuditEntry] = []
        for path in sorted(self._base_dir.glob("*.jsonl")):
            try:
                text = path.read_text(encoding="utf-8")
                for line in text.strip().splitlines():
                    if line.strip():
                        data = json.loads(line)
                        entries.append(AuditEntry(**data))
            except Exception:
                continue
        return entries

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_event(
        self,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[dict[str, Any]] = None,
        ip_address: str = "",
        user_agent: str = "",
        success: bool = True,
    ) -> AuditEntry:
        """Record an audit event and return the created entry."""
        entry = AuditEntry(
            id=uuid.uuid4().hex[:16],
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
        )
        log_file = self._current_log_file()
        with log_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(entry)) + "\n")
        return entry

    def get_events(
        self,
        *,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 200,
    ) -> list[AuditEntry]:
        """Return filtered audit events, newest first."""
        entries = self._read_all_entries()

        if actor:
            entries = [e for e in entries if e.actor == actor]
        if action:
            entries = [e for e in entries if e.action == action]
        if resource_type:
            entries = [e for e in entries if e.resource_type == resource_type]
        if start_date:
            entries = [e for e in entries if e.timestamp >= start_date]
        if end_date:
            entries = [e for e in entries if e.timestamp <= end_date]

        # Newest first
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def get_events_for_resource(
        self, resource_type: str, resource_id: str
    ) -> list[AuditEntry]:
        """Return all events for a specific resource."""
        entries = self._read_all_entries()
        result = [
            e
            for e in entries
            if e.resource_type == resource_type and e.resource_id == resource_id
        ]
        result.sort(key=lambda e: e.timestamp, reverse=True)
        return result

    def get_events_for_actor(self, actor: str) -> list[AuditEntry]:
        """Return all events performed by a specific actor."""
        return self.get_events(actor=actor)

    def export_events(
        self,
        fmt: str = "json",
        *,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """Export audit events in the specified format (``json`` or ``csv``)."""
        entries = self.get_events(
            actor=actor,
            action=action,
            resource_type=resource_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

        if fmt == "csv":
            lines = [
                "id,timestamp,actor,action,resource_type,resource_id,success,ip_address,user_agent"
            ]
            for e in entries:
                lines.append(
                    f"{e.id},{e.timestamp},{e.actor},{e.action},{e.resource_type},"
                    f"{e.resource_id},{e.success},{e.ip_address},{e.user_agent}"
                )
            return "\n".join(lines)

        # Default to JSON
        return json.dumps([asdict(e) for e in entries], indent=2)
