"""ALE_versions.md manifest management -- upsert logic for tracking pulled libraries.

When a consumer pulls a library, ALE_versions.md is updated -- either adding
a new row (new library) or updating an existing row (version update).  The
upsert is idempotent: calling it twice with the same data produces the same
file content.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Template used when the manifest file does not exist yet
# ---------------------------------------------------------------------------

_MANIFEST_TEMPLATE = """\
# ALE Library Manifest

Last updated: {timestamp}

## Installed Libraries

| Library ID | Name | Version | Downloaded | Status |
|------------|------|---------|------------|--------|

## Configuration

- **ALE Endpoint**: {endpoint}
- **User**: {user_email}

---
*Managed by ALE (Agentic Library Exchange). Updated automatically when libraries are pulled.*
"""

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# Matches the "Last updated: <timestamp>" line anywhere in the file.
_LAST_UPDATED_RE = re.compile(r"^(Last updated:\s*)(.+)$", re.MULTILINE)

# Matches the table header row so we can locate the table.
_TABLE_HEADER_RE = re.compile(
    r"^\|\s*Library ID\s*\|\s*Name\s*\|\s*Version\s*\|\s*Downloaded\s*\|\s*Status\s*\|",
    re.MULTILINE,
)

# Matches the separator row that follows the header.
_TABLE_SEP_RE = re.compile(r"^\|[-| ]+\|$", re.MULTILINE)

# Matches a single data row in the table.  Captures the five cell values.
_TABLE_ROW_RE = re.compile(
    r"^\|\s*(?P<library_id>[^|]+?)\s*"
    r"\|\s*(?P<name>[^|]+?)\s*"
    r"\|\s*(?P<version>[^|]+?)\s*"
    r"\|\s*(?P<downloaded>[^|]+?)\s*"
    r"\|\s*(?P<status>[^|]+?)\s*\|$",
    re.MULTILINE,
)

# Matches the Configuration section entries.
# Use ``[ \t]*`` instead of ``\s*`` so we never match across newlines.
_CONFIG_ENDPOINT_RE = re.compile(
    r"^(- \*\*ALE Endpoint\*\*:[ \t]*)(.*)$", re.MULTILINE
)
_CONFIG_USER_RE = re.compile(
    r"^(- \*\*User\*\*:[ \t]*)(.*)$", re.MULTILINE
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class VersionsManifest:
    """Manages the ALE_versions.md file in the consumer's ALE/ directory.

    The manifest tracks all pulled libraries in a markdown table format
    that is both human-readable and agent-parseable.
    """

    def __init__(self, manifest_path: str | Path):
        """Initialize with path to ALE_versions.md."""
        self.path = Path(manifest_path)

    # -- upsert -------------------------------------------------------------

    def upsert_library(
        self,
        library_id: str,
        name: str,
        version: str,
        status: str = "current",
    ) -> None:
        """Add or update a library entry in the manifest.

        If the *library_id* already exists, update its version, timestamp,
        and status.  If it does not exist, append a new row.

        The table rows are kept sorted alphabetically by library name (case-
        insensitive) after every upsert, and the ``Last updated`` timestamp
        at the top of the file is refreshed.
        """
        content = self._read_or_create()
        rows = self._parse_rows(content)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Upsert into the row list ----------------------------------------
        found = False
        for row in rows:
            if row["library_id"] == library_id:
                row["name"] = name
                row["version"] = version
                row["downloaded"] = today
                row["status"] = status
                found = True
                break

        if not found:
            rows.append(
                {
                    "library_id": library_id,
                    "name": name,
                    "version": version,
                    "downloaded": today,
                    "status": status,
                }
            )

        # Sort rows by name (case-insensitive) ----------------------------
        rows.sort(key=lambda r: r["name"].lower())

        # Rebuild the file content -----------------------------------------
        content = self._replace_table_rows(content, rows)
        content = self._update_timestamp(content)

        self._write(content)

    # -- query --------------------------------------------------------------

    def get_library(self, library_id: str) -> dict | None:
        """Parse the manifest and return info for a specific library.

        Returns a dict with keys ``library_id``, ``name``, ``version``,
        ``downloaded``, ``status`` -- or ``None`` if not found.
        """
        if not self.path.exists():
            return None
        rows = self._parse_rows(self.path.read_text(encoding="utf-8"))
        for row in rows:
            if row["library_id"] == library_id:
                return dict(row)
        return None

    def list_libraries(self) -> list[dict]:
        """Parse the manifest and return all library entries.

        Returns a list of dicts, each with keys ``library_id``, ``name``,
        ``version``, ``downloaded``, ``status``.
        """
        if not self.path.exists():
            return []
        return self._parse_rows(self.path.read_text(encoding="utf-8"))

    # -- remove -------------------------------------------------------------

    def remove_library(self, library_id: str) -> bool:
        """Remove a library entry from the manifest.

        Returns ``True`` if the library was found and removed, ``False``
        otherwise.
        """
        if not self.path.exists():
            return False

        content = self.path.read_text(encoding="utf-8")
        rows = self._parse_rows(content)

        original_len = len(rows)
        rows = [r for r in rows if r["library_id"] != library_id]

        if len(rows) == original_len:
            return False

        content = self._replace_table_rows(content, rows)
        content = self._update_timestamp(content)
        self._write(content)
        return True

    # -- config -------------------------------------------------------------

    def update_config(self, endpoint: str = "", user_email: str = "") -> None:
        """Update the Configuration section of the manifest.

        Only provided (non-empty) values are written; the other field is
        left unchanged.
        """
        content = self._read_or_create()

        if endpoint:
            content = _CONFIG_ENDPOINT_RE.sub(rf"\g<1>{endpoint}", content)
        if user_email:
            content = _CONFIG_USER_RE.sub(rf"\g<1>{user_email}", content)

        self._write(content)

    # ======================================================================
    # Internal helpers
    # ======================================================================

    def _read_or_create(self) -> str:
        """Return the file content, creating the file from the template if needed."""
        if self.path.exists():
            return self.path.read_text(encoding="utf-8")

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return _MANIFEST_TEMPLATE.format(
            timestamp=now,
            endpoint="",
            user_email="",
        )

    def _write(self, content: str) -> None:
        """Write *content* to the manifest file, creating parent dirs."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(content, encoding="utf-8")

    # -- table parsing / rebuilding ----------------------------------------

    @staticmethod
    def _parse_rows(content: str) -> list[dict]:
        """Extract all data rows from the markdown table in *content*.

        Returns a list of dicts with keys:
        ``library_id``, ``name``, ``version``, ``downloaded``, ``status``.
        """
        # Find the header row -- everything after the separator row is data.
        header_match = _TABLE_HEADER_RE.search(content)
        if header_match is None:
            return []

        # Find the separator row that immediately follows the header.
        sep_match = _TABLE_SEP_RE.search(content, header_match.end())
        if sep_match is None:
            return []

        # Everything between the separator and the next blank line (or
        # a line that does not start with ``|``) is table data.
        data_start = sep_match.end()
        rows: list[dict] = []
        for match in _TABLE_ROW_RE.finditer(content, data_start):
            # Stop if we have clearly left the table region (e.g. a blank
            # line or a section header between the last row and this match).
            between = content[data_start:match.start()]
            if re.search(r"\n\s*\n", between):
                break
            rows.append(
                {
                    "library_id": match.group("library_id").strip(),
                    "name": match.group("name").strip(),
                    "version": match.group("version").strip(),
                    "downloaded": match.group("downloaded").strip(),
                    "status": match.group("status").strip(),
                }
            )
            data_start = match.end()

        return rows

    def _replace_table_rows(self, content: str, rows: list[dict]) -> str:
        """Replace the data rows in the markdown table with *rows*.

        The header and separator rows are preserved; only the data rows
        between the separator and the next blank line (or non-table line)
        are replaced.
        """
        header_match = _TABLE_HEADER_RE.search(content)
        if header_match is None:
            # Should not happen if _read_or_create was used, but be safe.
            return content

        sep_match = _TABLE_SEP_RE.search(content, header_match.end())
        if sep_match is None:
            return content

        # Determine the extent of existing data rows.
        data_start = sep_match.end()
        data_end = data_start

        # Walk forward while lines start with ``|``.  The first empty
        # line (or a line that does not start with ``|``) signals the
        # end of the table data region.
        remaining = content[data_start:]
        first = True
        for line in remaining.split("\n"):
            # The split always produces a leading empty string because
            # data_start sits right before the ``\n`` at end of the
            # separator row.  Skip that initial artifact only.
            if first and line == "":
                data_end += 1  # account for the ``\n``
                first = False
                continue
            first = False
            if line.startswith("|"):
                data_end += len(line) + 1  # +1 for ``\n``
            else:
                break

        # Build new row text.
        row_lines = self._format_rows(rows)

        new_content = content[:data_start] + row_lines + content[data_end:]
        return new_content

    @staticmethod
    def _format_rows(rows: list[dict]) -> str:
        """Format a list of row dicts into markdown table row lines.

        Returns a string that starts with ``\\n`` (to follow the separator
        row) and ends with ``\\n``.
        """
        if not rows:
            return "\n"

        lines: list[str] = []
        for row in rows:
            line = (
                f"| {row['library_id']} "
                f"| {row['name']} "
                f"| {row['version']} "
                f"| {row['downloaded']} "
                f"| {row['status']} |"
            )
            lines.append(line)

        return "\n" + "\n".join(lines) + "\n"

    @staticmethod
    def _update_timestamp(content: str) -> str:
        """Replace the ``Last updated:`` value with the current UTC time."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        new_content, count = _LAST_UPDATED_RE.subn(rf"\g<1>{now}", content)
        if count == 0:
            # The timestamp line is missing -- insert it after the title.
            content = content.replace(
                "# ALE Library Manifest\n",
                f"# ALE Library Manifest\n\nLast updated: {now}\n",
                1,
            )
            return content
        return new_content
