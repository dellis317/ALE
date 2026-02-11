"""Update checker — detect source repo changes for generated libraries.

Compares the current state of a source repository against the snapshot
captured when a library was generated. Classifies changes as major, minor,
or patch based on heuristics: commit volume, file-level churn, and
the presence of version tags.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from git import Repo, InvalidGitRepositoryError, GitCommandError


@dataclass
class FileChange:
    """A single changed file with its diff stats."""

    path: str
    insertions: int = 0
    deletions: int = 0
    status: str = ""  # A(dded), M(odified), D(eleted), R(enamed)


@dataclass
class UpdateCheckResult:
    """Result of checking a source repo for updates."""

    has_updates: bool = False
    severity: str = "none"  # none | patch | minor | major
    severity_reason: str = ""

    # Commit-level info
    current_commit: str = ""
    latest_commit: str = ""
    new_commit_count: int = 0
    commit_messages: list[str] = field(default_factory=list)

    # File-level changes
    files_changed: int = 0
    total_insertions: int = 0
    total_deletions: int = 0
    changed_files: list[FileChange] = field(default_factory=list)

    # Source-file-specific changes (files that overlap with library sources)
    source_files_affected: int = 0
    source_files_changed: list[str] = field(default_factory=list)

    # Version / tag info
    new_tags: list[str] = field(default_factory=list)
    latest_tag: str = ""

    # Human-readable summary
    summary: str = ""
    change_notes: list[str] = field(default_factory=list)

    @property
    def total_churn(self) -> int:
        return self.total_insertions + self.total_deletions


def check_for_updates(
    repo_path: str,
    since_commit: str = "",
    source_files: list[str] | None = None,
) -> UpdateCheckResult:
    """Check a local repo for updates since a given commit.

    Args:
        repo_path: Path to the local git repository.
        since_commit: The commit SHA the library was generated from.
                      If empty, compares HEAD~50..HEAD as a fallback.
        source_files: List of source file paths the library was built from.
                      Used to determine if changes are relevant.

    Returns:
        UpdateCheckResult with full change analysis.
    """
    result = UpdateCheckResult()
    path = Path(repo_path)

    try:
        repo = Repo(path)
    except (InvalidGitRepositoryError, Exception):
        result.summary = f"Could not open repository at {repo_path}"
        return result

    if repo.head.is_detached:
        result.latest_commit = str(repo.head.commit.hexsha)
    else:
        result.latest_commit = str(repo.head.commit.hexsha)

    result.current_commit = since_commit or ""

    # If no since_commit, try to find a reasonable baseline
    if not since_commit:
        # Use the 50th ancestor or the root commit
        try:
            commits = list(repo.iter_commits(max_count=51))
            if len(commits) > 50:
                since_commit = str(commits[50].hexsha)
            elif len(commits) > 1:
                since_commit = str(commits[-1].hexsha)
            else:
                result.summary = "Repository has only one commit — no history to compare."
                return result
        except Exception:
            result.summary = "Could not read commit history."
            return result

    # Resolve the since_commit
    try:
        base_commit = repo.commit(since_commit)
    except Exception:
        result.summary = f"Could not resolve commit {since_commit[:12]}"
        return result

    head_commit = repo.head.commit

    if base_commit.hexsha == head_commit.hexsha:
        result.summary = "Library is up to date — no new commits since generation."
        return result

    result.has_updates = True

    # Gather commits between base and HEAD
    try:
        commit_range = f"{base_commit.hexsha}..{head_commit.hexsha}"
        commits = list(repo.iter_commits(commit_range))
        result.new_commit_count = len(commits)
        result.commit_messages = [
            c.message.strip().split("\n")[0] for c in commits[:30]
        ]
    except GitCommandError:
        result.new_commit_count = 0

    # Diff stats
    try:
        diff_index = base_commit.diff(head_commit, create_patch=False)
        changed_files: list[FileChange] = []

        for diff_item in diff_index:
            file_path = diff_item.b_path or diff_item.a_path or ""
            status = "M"
            if diff_item.new_file:
                status = "A"
            elif diff_item.deleted_file:
                status = "D"
            elif diff_item.renamed_file:
                status = "R"

            changed_files.append(FileChange(
                path=file_path,
                status=status,
            ))

        result.files_changed = len(changed_files)
        result.changed_files = changed_files[:100]  # Cap at 100 for display

        # Get insertions/deletions via diff stat
        try:
            stat = base_commit.diff(head_commit).stats
            # stat is not always available, use numstat
        except Exception:
            pass

        # Use git log --stat for aggregate numbers
        try:
            stat_output = repo.git.diff(
                base_commit.hexsha, head_commit.hexsha, stat=True, stat_count=1000
            )
            # Parse the summary line like: "42 files changed, 1234 insertions(+), 567 deletions(-)"
            summary_match = re.search(
                r"(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?",
                stat_output,
            )
            if summary_match:
                result.total_insertions = int(summary_match.group(2) or 0)
                result.total_deletions = int(summary_match.group(3) or 0)
        except Exception:
            pass

    except Exception:
        pass

    # Check which source files were affected
    if source_files:
        # Normalize source paths for comparison
        norm_sources = set()
        for sf in source_files:
            # Strip repo_path prefix if present
            sf_path = Path(sf)
            try:
                rel = sf_path.relative_to(path)
                norm_sources.add(str(rel))
            except ValueError:
                norm_sources.add(sf)

        affected = []
        for fc in result.changed_files:
            if fc.path in norm_sources:
                affected.append(fc.path)
            else:
                # Check partial match (source might be specified differently)
                for ns in norm_sources:
                    if fc.path.endswith(ns) or ns.endswith(fc.path):
                        affected.append(fc.path)
                        break

        result.source_files_affected = len(affected)
        result.source_files_changed = affected

    # Check for new tags (potential version releases)
    try:
        all_tags = []
        for tag in repo.tags:
            try:
                tag_commit = tag.commit
                if repo.is_ancestor(base_commit, tag_commit) and tag_commit != base_commit:
                    all_tags.append(tag.name)
            except Exception:
                continue

        result.new_tags = all_tags
        if all_tags:
            result.latest_tag = all_tags[-1]
    except Exception:
        pass

    # Classify severity
    result.severity, result.severity_reason = _classify_severity(result)

    # Build summary and change notes
    result.summary, result.change_notes = _build_summary(result, source_files)

    return result


def _classify_severity(result: UpdateCheckResult) -> tuple[str, str]:
    """Classify update severity based on heuristics.

    Returns:
        (severity, reason) tuple.
    """
    # Major: new version tag, or massive churn (>500 lines), or >20 commits,
    #        or >50% of source files changed
    if result.new_tags:
        version_tags = [t for t in result.new_tags if re.match(r"v?\d+\.", t)]
        if version_tags:
            return "major", f"New version tag detected: {version_tags[-1]}"

    if result.source_files_affected > 0:
        if result.source_files_changed:
            source_pct = (result.source_files_affected / max(len(result.source_files_changed), 1)) * 100
            # If a high fraction of the files that actually changed are source files,
            # that's significant
            if result.source_files_affected >= 5:
                return "major", f"{result.source_files_affected} library source files were modified"

    if result.total_churn > 500:
        return "major", f"Large code churn: {result.total_insertions}+ / {result.total_deletions}-"

    if result.new_commit_count > 20:
        return "major", f"{result.new_commit_count} new commits since library was generated"

    # Minor: moderate changes — some source files touched, or moderate churn
    if result.source_files_affected > 0:
        return "minor", f"{result.source_files_affected} library source file(s) modified"

    if result.total_churn > 100:
        return "minor", f"Moderate code churn: {result.total_insertions}+ / {result.total_deletions}-"

    if result.new_commit_count > 5:
        return "minor", f"{result.new_commit_count} new commits"

    # Patch: small changes
    if result.has_updates:
        return "patch", f"{result.new_commit_count} new commit(s) with minimal changes"

    return "none", "No updates detected"


def _build_summary(
    result: UpdateCheckResult,
    source_files: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Build a human-readable summary and change notes list."""
    notes: list[str] = []

    if not result.has_updates:
        return "No updates available.", notes

    # Severity headline
    severity_label = {
        "major": "Major Update Available",
        "minor": "Minor Update Available",
        "patch": "Patch Update Available",
    }.get(result.severity, "Update Available")

    summary = f"{severity_label} — {result.severity_reason}"

    # Commit info
    if result.new_commit_count > 0:
        notes.append(f"{result.new_commit_count} new commit(s) since library was generated")

    # Version tags
    if result.new_tags:
        notes.append(f"New version tag(s): {', '.join(result.new_tags)}")

    # File changes
    if result.files_changed > 0:
        notes.append(
            f"{result.files_changed} file(s) changed "
            f"({result.total_insertions} insertions, {result.total_deletions} deletions)"
        )

    # Source file impact
    if result.source_files_affected > 0:
        notes.append(
            f"{result.source_files_affected} of the library's source files were modified:"
        )
        for sf in result.source_files_changed[:10]:
            notes.append(f"  - {sf}")
        if len(result.source_files_changed) > 10:
            notes.append(f"  ... and {len(result.source_files_changed) - 10} more")
    elif source_files:
        notes.append("None of the library's source files were directly modified")

    # Recent commit messages
    if result.commit_messages:
        notes.append("Recent commits:")
        for msg in result.commit_messages[:8]:
            notes.append(f"  - {msg}")
        if len(result.commit_messages) > 8:
            notes.append(f"  ... and {len(result.commit_messages) - 8} more")

    return summary, notes
