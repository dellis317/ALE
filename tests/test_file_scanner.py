"""Tests for the file scanner utility."""

import tempfile
from pathlib import Path

from ale.utils.file_scanner import scan_project_files, classify_file, SKIP_DIRS


def test_classify_known_extensions():
    assert classify_file(Path("foo.py")) == "python"
    assert classify_file(Path("bar.js")) == "javascript"
    assert classify_file(Path("baz.ts")) == "typescript"
    assert classify_file(Path("qux.go")) == "go"
    assert classify_file(Path("main.rs")) == "rust"


def test_classify_unknown_extension():
    assert classify_file(Path("readme.md")) is None
    assert classify_file(Path("data.csv")) is None
    assert classify_file(Path("image.png")) is None


def test_scan_finds_source_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "main.py").write_text("print('hello')")
        (root / "utils").mkdir()
        (root / "utils" / "helper.py").write_text("def help(): pass")
        (root / "readme.md").write_text("# readme")

        files = scan_project_files(root)
        names = {f.name for f in files}
        assert "main.py" in names
        assert "helper.py" in names
        assert "readme.md" not in names


def test_scan_skips_excluded_dirs():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("pass")
        (root / "node_modules").mkdir()
        (root / "node_modules" / "lib.js").write_text("pass")
        (root / "__pycache__").mkdir()
        (root / "__pycache__" / "app.cpython-311.pyc").write_text("pass")

        files = scan_project_files(root)
        paths_str = [str(f) for f in files]
        assert any("app.py" in p for p in paths_str)
        assert not any("node_modules" in p for p in paths_str)


def test_skip_dirs_contains_expected():
    assert ".git" in SKIP_DIRS
    assert "node_modules" in SKIP_DIRS
    assert "__pycache__" in SKIP_DIRS
