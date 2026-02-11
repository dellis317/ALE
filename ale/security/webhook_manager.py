"""Webhook management for ALE.

Provides registration, firing, delivery tracking, and retry capabilities
for outbound webhooks.  Webhook payloads are signed with HMAC-SHA256 and
delivered via ``urllib.request`` (no extra dependencies).

Storage is file-based JSON in ``~/.ale/webhooks/``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------


@dataclass
class Webhook:
    """A registered outbound webhook."""

    id: str
    name: str
    url: str
    events: list[str] = field(default_factory=list)
    secret: str = ""
    active: bool = True
    created_at: str = ""
    updated_at: str = ""


@dataclass
class WebhookDelivery:
    """Record of a single webhook delivery attempt."""

    id: str
    webhook_id: str
    event: str
    payload: dict[str, Any] = field(default_factory=dict)
    response_status: int = 0
    response_body: str = ""
    success: bool = False
    delivered_at: str = ""
    duration_ms: int = 0


# All supported webhook event types
WEBHOOK_EVENTS = [
    "library.published",
    "library.deleted",
    "conformance.passed",
    "conformance.failed",
    "policy.violated",
    "approval.requested",
    "approval.decided",
]


class WebhookManager:
    """Manages webhooks with file-based JSON persistence."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir or Path.home() / ".ale" / "webhooks"
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._hooks_file = self._base_dir / "webhooks.json"
        self._deliveries_file = self._base_dir / "deliveries.json"

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load_webhooks(self) -> list[dict[str, Any]]:
        if self._hooks_file.exists():
            try:
                return json.loads(self._hooks_file.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_webhooks(self, data: list[dict[str, Any]]) -> None:
        self._hooks_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_deliveries(self) -> list[dict[str, Any]]:
        if self._deliveries_file.exists():
            try:
                return json.loads(self._deliveries_file.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_deliveries(self, data: list[dict[str, Any]]) -> None:
        self._deliveries_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @staticmethod
    def _webhook_from_dict(d: dict[str, Any]) -> Webhook:
        return Webhook(**{k: v for k, v in d.items() if k in Webhook.__dataclass_fields__})

    @staticmethod
    def _delivery_from_dict(d: dict[str, Any]) -> WebhookDelivery:
        return WebhookDelivery(
            **{k: v for k, v in d.items() if k in WebhookDelivery.__dataclass_fields__}
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def register_webhook(
        self,
        url: str,
        events: list[str],
        secret: str = "",
        name: str = "",
        active: bool = True,
    ) -> Webhook:
        """Register a new webhook and return it."""
        now = datetime.now(timezone.utc).isoformat()
        wh = Webhook(
            id=uuid.uuid4().hex[:16],
            name=name or url,
            url=url,
            events=events,
            secret=secret,
            active=active,
            created_at=now,
            updated_at=now,
        )
        hooks = self._load_webhooks()
        hooks.append(asdict(wh))
        self._save_webhooks(hooks)
        return wh

    def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        for d in self._load_webhooks():
            if d.get("id") == webhook_id:
                return self._webhook_from_dict(d)
        return None

    def list_webhooks(self) -> list[Webhook]:
        return [self._webhook_from_dict(d) for d in self._load_webhooks()]

    def update_webhook(self, webhook_id: str, **kwargs: Any) -> Webhook:
        hooks = self._load_webhooks()
        for d in hooks:
            if d.get("id") == webhook_id:
                for k, v in kwargs.items():
                    if k in Webhook.__dataclass_fields__ and k != "id":
                        d[k] = v
                d["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_webhooks(hooks)
                return self._webhook_from_dict(d)
        raise ValueError(f"Webhook {webhook_id} not found")

    def delete_webhook(self, webhook_id: str) -> bool:
        hooks = self._load_webhooks()
        new = [d for d in hooks if d.get("id") != webhook_id]
        if len(new) == len(hooks):
            return False
        self._save_webhooks(new)
        return True

    def toggle_webhook(self, webhook_id: str, active: bool) -> Webhook:
        return self.update_webhook(webhook_id, active=active)

    # ------------------------------------------------------------------
    # Firing
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_signature(payload_bytes: bytes, secret: str) -> str:
        """Compute HMAC-SHA256 signature for a payload."""
        mac = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256)
        return f"sha256={mac.hexdigest()}"

    def fire_webhook(self, event: str, payload: dict[str, Any]) -> list[WebhookDelivery]:
        """Fire an event to all matching active webhooks.

        Returns a list of delivery records, one per matching webhook.
        """
        hooks = [w for w in self.list_webhooks() if w.active and event in w.events]
        deliveries_data = self._load_deliveries()
        results: list[WebhookDelivery] = []

        for wh in hooks:
            delivery = self._deliver(wh, event, payload)
            deliveries_data.append(asdict(delivery))
            results.append(delivery)

        self._save_deliveries(deliveries_data)
        return results

    def _deliver(
        self, wh: Webhook, event: str, payload: dict[str, Any]
    ) -> WebhookDelivery:
        """Attempt a single delivery and return the result."""
        body = json.dumps(payload).encode("utf-8")
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-ALE-Event": event,
        }
        if wh.secret:
            headers["X-ALE-Signature"] = self._compute_signature(body, wh.secret)

        delivery_id = uuid.uuid4().hex[:16]
        start = time.monotonic()
        status = 0
        resp_body = ""
        success = False

        try:
            req = urllib.request.Request(
                wh.url, data=body, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                resp_body = resp.read().decode("utf-8", errors="replace")[:2000]
                success = 200 <= status < 300
        except Exception as exc:
            resp_body = str(exc)[:2000]

        duration = int((time.monotonic() - start) * 1000)

        return WebhookDelivery(
            id=delivery_id,
            webhook_id=wh.id,
            event=event,
            payload=payload,
            response_status=status,
            response_body=resp_body,
            success=success,
            delivered_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=duration,
        )

    # ------------------------------------------------------------------
    # Delivery history
    # ------------------------------------------------------------------

    def get_deliveries(
        self,
        webhook_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[WebhookDelivery]:
        """Return delivery records, optionally filtered by webhook, newest first."""
        data = self._load_deliveries()
        deliveries = [self._delivery_from_dict(d) for d in data]
        if webhook_id:
            deliveries = [d for d in deliveries if d.webhook_id == webhook_id]
        deliveries.sort(key=lambda d: d.delivered_at, reverse=True)
        return deliveries[:limit]

    def retry_delivery(self, delivery_id: str) -> WebhookDelivery:
        """Retry a previous delivery by replaying the same event/payload."""
        for d in self._load_deliveries():
            if d.get("id") == delivery_id:
                original = self._delivery_from_dict(d)
                wh = self.get_webhook(original.webhook_id)
                if wh is None:
                    raise ValueError(f"Webhook {original.webhook_id} not found")
                delivery = self._deliver(wh, original.event, original.payload)
                # Persist the new delivery
                deliveries = self._load_deliveries()
                deliveries.append(asdict(delivery))
                self._save_deliveries(deliveries)
                return delivery
        raise ValueError(f"Delivery {delivery_id} not found")
