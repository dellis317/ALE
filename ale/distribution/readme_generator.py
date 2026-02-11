"""README generator — produces a consumer-facing README.md for downloaded libraries.

When a library is pulled to a local workspace, this module generates a
concise ``README.md`` that describes the library, its provenance, and how to
use the accompanying ``build-plan.md``.
"""

from __future__ import annotations

from typing import Any


def _get(data: dict, *keys: str, default: Any = "") -> Any:
    """Safely traverse nested dicts, returning *default* on any miss."""
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is None:
            return default
    return current


def generate_library_readme(
    yaml_data: dict,
    library_id: str,
    version: str,
    downloaded_at: str = "",
) -> str:
    """Generate a consumer-facing ``README.md`` for a downloaded library.

    Parameters
    ----------
    yaml_data:
        The dictionary obtained by loading an ``.agentic.yaml`` file
        (e.g. via ``yaml.safe_load``).  Expected top-level key is
        ``agentic_library``.
    library_id:
        The unique library identifier in the ALE registry.
    version:
        The version string to display (e.g. ``"1.0.0"``).
    downloaded_at:
        Human-readable download timestamp.  Defaults to an empty string
        if not provided.

    Returns
    -------
    str
        A complete Markdown document suitable for writing to ``README.md``.
    """
    root = yaml_data.get("agentic_library", yaml_data)
    manifest = root.get("manifest", {}) or {}

    name = _get(manifest, "name") or "Unnamed Library"
    description = _get(manifest, "description") or ""
    complexity = _get(manifest, "complexity") or "unknown"
    tags_list = manifest.get("tags", []) or []
    tags = ", ".join(str(t) for t in tags_list) if tags_list else ""
    source_repo = _get(manifest, "source_repo") or _get(root, "source_repo") or "ALE Registry"

    lines = [
        f"# {name}",
        f"**Library ID:** {library_id}  ",
        f"**Version:** {version}  ",
        f"**Downloaded:** {downloaded_at}  ",
        f"**Complexity:** {complexity}  ",
        f"**Tags:** {tags}",
        "",
        "## Description",
        description.strip() if description else "",
        "",
        "## Source",
        source_repo,
        "",
        "## Files",
        "- `build-plan.md` — Full implementation instructions for your AI coding assistant",
        "- `README.md` — This file",
        "",
        "## Usage",
        "Point your AI coding assistant to `build-plan.md` in this directory.",
        "The build plan contains step-by-step instructions for implementing this",
        "feature natively in your project's language and framework.",
        "",
        "## Version History",
        "| Version | Downloaded | Notes |",
        "|---------|-----------|-------|",
        f"| {version} | {downloaded_at} | Initial download |",
    ]

    return "\n".join(lines) + "\n"
