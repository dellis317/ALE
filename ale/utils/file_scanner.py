"""File scanner — discover and classify project files."""

from pathlib import Path

# Directories to always skip
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", ".env",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "target", "vendor", ".next", ".nuxt", "coverage",
}

# File extensions we care about, mapped to language
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".ex": "elixir",
    ".exs": "elixir",
    ".sh": "shell",
    ".bash": "shell",
}


def scan_project_files(repo_path: Path) -> list[Path]:
    """Recursively scan a project directory for source files.

    Skips common non-source directories and files.
    """
    files = []
    for item in repo_path.rglob("*"):
        if item.is_file() and _should_include(item):
            files.append(item)
    return files


def _should_include(path: Path) -> bool:
    """Check if a file should be included in analysis."""
    # Skip files in excluded directories
    for part in path.parts:
        if part in SKIP_DIRS:
            return False

    # Only include known source file types
    return path.suffix in LANGUAGE_MAP


def classify_file(path: Path) -> str | None:
    """Return the language classification for a file, or None if unknown."""
    return LANGUAGE_MAP.get(path.suffix)
