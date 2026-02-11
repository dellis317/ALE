"""Git operations — clone, resolve paths, inspect repos."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from git import Repo, InvalidGitRepositoryError


@dataclass
class RepoHandle:
    """Tracks a resolved local repo, including whether it was cloned from a URL.

    Use as a context manager to ensure temp clones are cleaned up::

        with ensure_local_repo(url_or_path) as handle:
            analyze(handle.local_path)
        # temp clone (if any) is deleted here
    """

    local_path: Path
    """Filesystem path to the repo root (may be a temp clone)."""

    source_url: str = ""
    """Original URL if the repo was cloned, empty for local repos."""

    is_temp_clone: bool = False
    """True when ``local_path`` is a temporary clone that should be cleaned up."""

    def __enter__(self) -> "RepoHandle":
        return self

    def __exit__(self, *exc) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        """Remove the temporary clone directory, if applicable."""
        if self.is_temp_clone and self.local_path.exists():
            shutil.rmtree(self.local_path, ignore_errors=True)

    @property
    def display_path(self) -> str:
        """Return the source URL (for cloned repos) or the local path string.

        This is the value that should be stored in library metadata so that
        end-users see the repo URL rather than an opaque temp directory.
        """
        return self.source_url if self.source_url else str(self.local_path)


def ensure_local_repo(repo_path: str) -> RepoHandle:
    """Ensure we have a local clone of the repo. Clone if it's a URL.

    Args:
        repo_path: Local path or Git URL.

    Returns:
        A ``RepoHandle`` with the resolved local path and provenance info.
        Use as a context manager so temporary clones are cleaned up.

    Raises:
        ValueError: If the path is not a valid repo and not a cloneable URL.
    """
    path = Path(repo_path)

    # If it's already a local directory with a .git, use it directly
    if path.is_dir():
        try:
            Repo(path)
            remote_url = _get_remote_url(path)
            return RepoHandle(
                local_path=path,
                source_url=remote_url,
                is_temp_clone=False,
            )
        except InvalidGitRepositoryError:
            raise ValueError(f"Directory exists but is not a Git repo: {repo_path}")

    # If it looks like a URL, clone it
    if repo_path.startswith(("http://", "https://", "git@", "git://")):
        clone_dir = _clone_repo(repo_path)
        return RepoHandle(
            local_path=clone_dir,
            source_url=repo_path,
            is_temp_clone=True,
        )

    raise ValueError(f"Not a valid repo path or URL: {repo_path}")


def _clone_repo(url: str) -> Path:
    """Clone a Git repo to a temporary directory."""
    clone_dir = Path(tempfile.mkdtemp(prefix="ale_"))
    Repo.clone_from(url, clone_dir, depth=1)
    return clone_dir


def _get_remote_url(repo_path: Path) -> str:
    """Return the origin remote URL for a local repo, or empty string."""
    try:
        repo = Repo(repo_path)
        if repo.remotes:
            return repo.remotes[0].url
    except Exception:
        pass
    return ""


def get_repo_metadata(repo_path: Path) -> dict:
    """Extract metadata from a Git repo."""
    repo = Repo(repo_path)
    return {
        "remotes": [r.url for r in repo.remotes] if repo.remotes else [],
        "branch": str(repo.active_branch) if not repo.head.is_detached else "detached",
        "commit_count": sum(1 for _ in repo.iter_commits()),
    }
