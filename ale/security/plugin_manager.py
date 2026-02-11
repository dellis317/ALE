"""Plugin management for ALE.

Provides registration, lifecycle management, and hook execution for
extensibility plugins.  Storage is file-based JSON in ``~/.ale/plugins/``.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------


@dataclass
class Plugin:
    """A registered ALE plugin."""

    id: str
    name: str
    description: str = ""
    hooks: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: str = ""


@dataclass
class PluginResult:
    """The result of executing a single plugin hook."""

    plugin_id: str
    hook_name: str
    success: bool = False
    output: str = ""
    error: str = ""
    duration_ms: int = 0


# Supported hook names
PLUGIN_HOOKS = [
    "pre_publish",
    "post_publish",
    "pre_conformance",
    "post_conformance",
    "pre_apply",
    "post_apply",
]


class PluginManager:
    """Manages extensibility plugins with file-based JSON persistence."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir or Path.home() / ".ale" / "plugins"
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._plugins_file = self._base_dir / "plugins.json"

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load_plugins(self) -> list[dict[str, Any]]:
        if self._plugins_file.exists():
            try:
                return json.loads(self._plugins_file.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save_plugins(self, data: list[dict[str, Any]]) -> None:
        self._plugins_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @staticmethod
    def _plugin_from_dict(d: dict[str, Any]) -> Plugin:
        return Plugin(**{k: v for k, v in d.items() if k in Plugin.__dataclass_fields__})

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def register_plugin(
        self,
        name: str,
        description: str = "",
        hooks: Optional[list[str]] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> Plugin:
        """Register a new plugin and return it."""
        plugin = Plugin(
            id=uuid.uuid4().hex[:16],
            name=name,
            description=description,
            hooks=hooks or [],
            config=config or {},
            enabled=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        plugins = self._load_plugins()
        plugins.append(asdict(plugin))
        self._save_plugins(plugins)
        return plugin

    def list_plugins(self) -> list[Plugin]:
        return [self._plugin_from_dict(d) for d in self._load_plugins()]

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        for d in self._load_plugins():
            if d.get("id") == plugin_id:
                return self._plugin_from_dict(d)
        return None

    def enable_plugin(self, plugin_id: str) -> Plugin:
        return self._set_enabled(plugin_id, True)

    def disable_plugin(self, plugin_id: str) -> Plugin:
        return self._set_enabled(plugin_id, False)

    def _set_enabled(self, plugin_id: str, enabled: bool) -> Plugin:
        plugins = self._load_plugins()
        for d in plugins:
            if d.get("id") == plugin_id:
                d["enabled"] = enabled
                self._save_plugins(plugins)
                return self._plugin_from_dict(d)
        raise ValueError(f"Plugin {plugin_id} not found")

    def update_plugin(self, plugin_id: str, **kwargs: Any) -> Plugin:
        plugins = self._load_plugins()
        for d in plugins:
            if d.get("id") == plugin_id:
                for k, v in kwargs.items():
                    if k in Plugin.__dataclass_fields__ and k != "id":
                        d[k] = v
                self._save_plugins(plugins)
                return self._plugin_from_dict(d)
        raise ValueError(f"Plugin {plugin_id} not found")

    def delete_plugin(self, plugin_id: str) -> bool:
        plugins = self._load_plugins()
        new = [d for d in plugins if d.get("id") != plugin_id]
        if len(new) == len(plugins):
            return False
        self._save_plugins(new)
        return True

    # ------------------------------------------------------------------
    # Hook execution
    # ------------------------------------------------------------------

    def execute_hook(
        self, hook_name: str, context: dict[str, Any]
    ) -> list[PluginResult]:
        """Execute all enabled plugins that match the given hook.

        Since plugins are metadata-only in this implementation (no arbitrary
        code execution), we simulate hook execution by recording that the
        hook was invoked with the given context for each matching plugin.
        """
        results: list[PluginResult] = []
        plugins = [p for p in self.list_plugins() if p.enabled and hook_name in p.hooks]

        for plugin in plugins:
            start = time.monotonic()
            try:
                # In a full implementation this would invoke the plugin's
                # handler.  For now we record a successful no-op execution.
                output = json.dumps(
                    {
                        "plugin": plugin.name,
                        "hook": hook_name,
                        "context_keys": list(context.keys()),
                        "message": f"Plugin '{plugin.name}' executed hook '{hook_name}' successfully.",
                    }
                )
                duration = int((time.monotonic() - start) * 1000)
                results.append(
                    PluginResult(
                        plugin_id=plugin.id,
                        hook_name=hook_name,
                        success=True,
                        output=output,
                        duration_ms=duration,
                    )
                )
            except Exception as exc:
                duration = int((time.monotonic() - start) * 1000)
                results.append(
                    PluginResult(
                        plugin_id=plugin.id,
                        hook_name=hook_name,
                        success=False,
                        error=str(exc),
                        duration_ms=duration,
                    )
                )

        return results
