"""Security, Audit, Webhooks & Plugins API router.

Prefix: ``/api/security``
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ale.security.audit_log import AuditLogger
from ale.security.plugin_manager import PluginManager
from ale.security.webhook_manager import WebhookManager
from web.backend.app.models.api import (
    AuditEntryResponse,
    AuditExportResponse,
    CreatePluginRequest,
    CreateWebhookRequest,
    PluginResponse,
    SecurityDashboardResponse,
    TogglePluginRequest,
    ToggleWebhookRequest,
    UpdatePluginRequest,
    UpdateWebhookRequest,
    WebhookDeliveryResponse,
    WebhookResponse,
)

router = APIRouter(prefix="/api/security", tags=["security"])

# ---------------------------------------------------------------------------
# Shared manager instances (singletons for the running process)
# ---------------------------------------------------------------------------
_audit = AuditLogger()
_webhooks = WebhookManager()
_plugins = PluginManager()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _audit_entry_to_response(e) -> AuditEntryResponse:
    d = asdict(e) if hasattr(e, "__dataclass_fields__") else e
    return AuditEntryResponse(**d)


def _webhook_to_response(w) -> WebhookResponse:
    d = asdict(w) if hasattr(w, "__dataclass_fields__") else w
    return WebhookResponse(
        id=d["id"],
        name=d["name"],
        url=d["url"],
        events=d.get("events", []),
        active=d.get("active", True),
        created_at=d.get("created_at", ""),
        updated_at=d.get("updated_at", ""),
    )


def _delivery_to_response(d) -> WebhookDeliveryResponse:
    data = asdict(d) if hasattr(d, "__dataclass_fields__") else d
    return WebhookDeliveryResponse(**data)


def _plugin_to_response(p) -> PluginResponse:
    d = asdict(p) if hasattr(p, "__dataclass_fields__") else p
    return PluginResponse(**d)


# =========================================================================
# Audit Log endpoints
# =========================================================================


@router.get("/audit", response_model=list[AuditEntryResponse])
async def list_audit_events(
    actor: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=10000),
):
    """List audit events with optional filters."""
    events = _audit.get_events(
        actor=actor,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return [_audit_entry_to_response(e) for e in events]


@router.get("/audit/export", response_model=AuditExportResponse)
async def export_audit_log(
    format: str = Query("json", regex="^(json|csv)$"),
    actor: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Export the audit log in JSON or CSV format."""
    content = _audit.export_events(
        format,
        actor=actor,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
    )
    events = _audit.get_events(
        actor=actor,
        action=action,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
    )
    return AuditExportResponse(
        format=format, content=content, record_count=len(events)
    )


@router.get(
    "/audit/{resource_type}/{resource_id}",
    response_model=list[AuditEntryResponse],
)
async def get_events_for_resource(resource_type: str, resource_id: str):
    """Get audit events for a specific resource."""
    events = _audit.get_events_for_resource(resource_type, resource_id)
    return [_audit_entry_to_response(e) for e in events]


# =========================================================================
# Webhook endpoints
# =========================================================================


@router.post("/webhooks", response_model=WebhookResponse)
async def create_webhook(req: CreateWebhookRequest):
    """Register a new webhook."""
    wh = _webhooks.register_webhook(
        url=req.url,
        events=req.events,
        secret=req.secret,
        name=req.name,
    )
    _audit.log_event(
        actor="system",
        action="webhook.create",
        resource_type="webhook",
        resource_id=wh.id,
        details={"name": wh.name, "url": wh.url},
    )
    return _webhook_to_response(wh)


@router.get("/webhooks", response_model=list[WebhookResponse])
async def list_webhooks_endpoint():
    """List all registered webhooks."""
    return [_webhook_to_response(w) for w in _webhooks.list_webhooks()]


@router.get("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(webhook_id: str):
    """Get details of a specific webhook."""
    wh = _webhooks.get_webhook(webhook_id)
    if wh is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return _webhook_to_response(wh)


@router.put("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(webhook_id: str, req: UpdateWebhookRequest):
    """Update a webhook's configuration."""
    kwargs = {}
    if req.name:
        kwargs["name"] = req.name
    if req.url:
        kwargs["url"] = req.url
    if req.events:
        kwargs["events"] = req.events
    try:
        wh = _webhooks.update_webhook(webhook_id, **kwargs)
    except ValueError:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return _webhook_to_response(wh)


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook."""
    if not _webhooks.delete_webhook(webhook_id):
        raise HTTPException(status_code=404, detail="Webhook not found")
    _audit.log_event(
        actor="system",
        action="webhook.delete",
        resource_type="webhook",
        resource_id=webhook_id,
    )
    return {"detail": "Webhook deleted"}


@router.put("/webhooks/{webhook_id}/toggle", response_model=WebhookResponse)
async def toggle_webhook(webhook_id: str, req: ToggleWebhookRequest):
    """Enable or disable a webhook."""
    try:
        wh = _webhooks.toggle_webhook(webhook_id, req.active)
    except ValueError:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return _webhook_to_response(wh)


@router.post("/webhooks/{webhook_id}/test", response_model=WebhookDeliveryResponse)
async def test_webhook(webhook_id: str):
    """Send a test event to a webhook."""
    wh = _webhooks.get_webhook(webhook_id)
    if wh is None:
        raise HTTPException(status_code=404, detail="Webhook not found")

    test_payload = {
        "event": "test",
        "webhook_id": webhook_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "This is a test delivery from ALE.",
    }

    delivery = _webhooks._deliver(wh, "test", test_payload)

    # Persist the delivery
    deliveries = _webhooks._load_deliveries()
    deliveries.append(asdict(delivery))
    _webhooks._save_deliveries(deliveries)

    return _delivery_to_response(delivery)


@router.get(
    "/webhooks/{webhook_id}/deliveries",
    response_model=list[WebhookDeliveryResponse],
)
async def get_webhook_deliveries(
    webhook_id: str, limit: int = Query(50, ge=1, le=500)
):
    """Get delivery history for a webhook."""
    wh = _webhooks.get_webhook(webhook_id)
    if wh is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    deliveries = _webhooks.get_deliveries(webhook_id=webhook_id, limit=limit)
    return [_delivery_to_response(d) for d in deliveries]


# =========================================================================
# Plugin endpoints
# =========================================================================


@router.post("/plugins", response_model=PluginResponse)
async def create_plugin(req: CreatePluginRequest):
    """Register a new plugin."""
    plugin = _plugins.register_plugin(
        name=req.name,
        description=req.description,
        hooks=req.hooks,
        config=req.config,
    )
    _audit.log_event(
        actor="system",
        action="plugin.create",
        resource_type="plugin",
        resource_id=plugin.id,
        details={"name": plugin.name},
    )
    return _plugin_to_response(plugin)


@router.get("/plugins", response_model=list[PluginResponse])
async def list_plugins_endpoint():
    """List all registered plugins."""
    return [_plugin_to_response(p) for p in _plugins.list_plugins()]


@router.get("/plugins/{plugin_id}", response_model=PluginResponse)
async def get_plugin(plugin_id: str):
    """Get details of a specific plugin."""
    plugin = _plugins.get_plugin(plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return _plugin_to_response(plugin)


@router.put("/plugins/{plugin_id}", response_model=PluginResponse)
async def update_plugin(plugin_id: str, req: UpdatePluginRequest):
    """Update a plugin's configuration."""
    kwargs = {}
    if req.name:
        kwargs["name"] = req.name
    if req.description:
        kwargs["description"] = req.description
    if req.hooks:
        kwargs["hooks"] = req.hooks
    if req.config:
        kwargs["config"] = req.config
    try:
        plugin = _plugins.update_plugin(plugin_id, **kwargs)
    except ValueError:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return _plugin_to_response(plugin)


@router.delete("/plugins/{plugin_id}")
async def delete_plugin(plugin_id: str):
    """Delete a plugin."""
    if not _plugins.delete_plugin(plugin_id):
        raise HTTPException(status_code=404, detail="Plugin not found")
    _audit.log_event(
        actor="system",
        action="plugin.delete",
        resource_type="plugin",
        resource_id=plugin_id,
    )
    return {"detail": "Plugin deleted"}


@router.put("/plugins/{plugin_id}/toggle", response_model=PluginResponse)
async def toggle_plugin(plugin_id: str, req: TogglePluginRequest):
    """Enable or disable a plugin."""
    try:
        if req.enabled:
            plugin = _plugins.enable_plugin(plugin_id)
        else:
            plugin = _plugins.disable_plugin(plugin_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return _plugin_to_response(plugin)


# =========================================================================
# Dashboard
# =========================================================================


@router.get("/dashboard", response_model=SecurityDashboardResponse)
async def security_dashboard():
    """Security posture overview with summary statistics."""
    # Audit stats
    all_events = _audit.get_events(limit=10000)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    events_today = [e for e in all_events if e.timestamp.startswith(today_str)]
    recent_events = all_events[:10]

    # Webhook stats
    webhooks = _webhooks.list_webhooks()
    active_webhooks = [w for w in webhooks if w.active]

    # Failed deliveries in last 24h
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    all_deliveries = _webhooks.get_deliveries(limit=10000)
    failed_24h = [
        d for d in all_deliveries if not d.success and d.delivered_at >= cutoff
    ]

    # Plugin stats
    plugins = _plugins.list_plugins()
    enabled_plugins = [p for p in plugins if p.enabled]

    return SecurityDashboardResponse(
        total_events=len(all_events),
        events_today=len(events_today),
        active_webhooks=len(active_webhooks),
        total_webhooks=len(webhooks),
        enabled_plugins=len(enabled_plugins),
        total_plugins=len(plugins),
        recent_events=[_audit_entry_to_response(e) for e in recent_events],
        failed_deliveries_24h=len(failed_24h),
    )
