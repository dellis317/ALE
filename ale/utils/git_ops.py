"""Git operations — clone, resolve paths, inspect repos."""

from pathlib import Path

from git import Repo, InvalidGitRepositoryError


def ensure_local_repo(repo_path: str) -> Path:
    """Ensure we have a local clone of the repo. Clone if it's a URL.

    Args:
        repo_path: Local path or Git URL.

    Returns:
        Path to the local repo root.

    Raises:
        ValueError: If the path is not a valid repo and not a cloneable URL.
    """
    path = Path(repo_path)

    # If it's already a local directory with a .git, use it directly
    if path.is_dir():
        try:
            Repo(path)
            return path
        except InvalidGitRepositoryError:
            raise ValueError(f"Directory exists but is not a Git repo: {repo_path}")

    # If it looks like a URL, clone it
    if repo_path.startswith(("http://", "https://", "git@", "git://")):
        return _clone_repo(repo_path)

    raise ValueError(f"Not a valid repo path or URL: {repo_path}")


def _clone_repo(url: str) -> Path:
    """Clone a Git repo to a temporary directory."""
    import tempfile

    clone_dir = Path(tempfile.mkdtemp(prefix="ale_"))
    Repo.clone_from(url, clone_dir, depth=1)
    return clone_dir


def get_repo_metadata(repo_path: Path) -> dict:
    """Extract metadata from a Git repo."""
    repo = Repo(repo_path)
    return {
        "remotes": [r.url for r in repo.remotes] if repo.remotes else [],
        "branch": str(repo.active_branch) if not repo.head.is_detached else "detached",
        "commit_count": sum(1 for _ in repo.iter_commits()),
    }
