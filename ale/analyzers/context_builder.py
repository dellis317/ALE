"""Context builder -- builds import graphs and finds callers/callees.

Scans all Python files in a repository to build an import graph, then
for a given candidate's modules, identifies who imports them (callers)
and what they import (callees).
"""

from __future__ import annotations

from pathlib import Path

from ale.ir.python_parser import parse_python_file
from ale.ir.models import IRModule


class ContextBuilder:
    """Builds import-level context for extraction candidates.

    Scans all Python files to build a module-level import graph,
    then determines callers and callees for a given set of modules.
    """

    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root)
        self._modules: dict[str, IRModule] = {}
        self._scanned = False

    def scan(self) -> None:
        """Scan all Python files in the repo to build the import graph.

        This is called lazily on first use or can be called explicitly.
        """
        if self._scanned:
            return

        for py_file in self.repo_root.rglob("*.py"):
            # Skip common non-source directories
            parts = py_file.relative_to(self.repo_root).parts
            if any(
                p.startswith(".")
                or p in ("__pycache__", "node_modules", ".git", "venv", ".venv", "env")
                for p in parts
            ):
                continue

            try:
                ir_module = parse_python_file(str(py_file), str(self.repo_root))
                self._modules[ir_module.path] = ir_module
            except Exception:
                continue

        self._scanned = True

    def get_callers(self, module_paths: list[str]) -> list[str]:
        """Find modules that import any of the given module paths.

        Args:
            module_paths: List of relative paths (from repo root) of
                          the candidate's source files.

        Returns:
            Sorted list of module paths that import the candidate's modules.
        """
        self.scan()

        # Build a set of module names that could be import targets
        target_names = set()
        for mp in module_paths:
            # Convert file path to possible import target
            # e.g., "ale/utils/helpers.py" -> "ale.utils.helpers", "ale.utils", etc.
            mp_clean = mp.replace("/", ".").replace("\\", ".")
            if mp_clean.endswith(".py"):
                mp_clean = mp_clean[:-3]
            target_names.add(mp_clean)

            # Also add individual parts for partial matching
            parts = mp_clean.split(".")
            for i in range(1, len(parts) + 1):
                target_names.add(".".join(parts[:i]))

        callers = set()
        for mod_path, mod in self._modules.items():
            if mod_path in module_paths:
                continue  # Skip the candidate's own modules

            for dep in mod.imports:
                # Check if this import targets one of our modules
                dep_target = dep.target
                if any(dep_target.startswith(t) or t.startswith(dep_target) for t in target_names):
                    callers.add(mod_path)
                    break

        return sorted(callers)

    def get_callees(self, module_paths: list[str]) -> list[str]:
        """Find internal modules that the given modules import.

        Args:
            module_paths: List of relative paths of the candidate's source files.

        Returns:
            Sorted list of module paths that the candidate imports (internal only).
        """
        self.scan()

        # Collect all internal import targets from the candidate's modules
        callees = set()
        known_module_names = set()

        # Build a lookup from import target to module path
        for mod_path in self._modules:
            mod_name = mod_path.replace("/", ".").replace("\\", ".")
            if mod_name.endswith(".py"):
                mod_name = mod_name[:-3]
            known_module_names.add((mod_name, mod_path))

        for mp in module_paths:
            mod = self._modules.get(mp)
            if mod is None:
                continue

            for dep in mod.imports:
                if dep.is_external:
                    continue

                # Try to resolve the import target to a known module
                for mod_name, mod_path in known_module_names:
                    if mod_path in module_paths:
                        continue  # Skip self-references
                    if dep.target.startswith(mod_name) or mod_name.startswith(dep.target):
                        callees.add(mod_path)

        return sorted(callees)

    def build_context(self, candidate) -> None:
        """Enrich a candidate with caller/callee information.

        Mutates the candidate in place, setting callers and callees fields.

        Args:
            candidate: An ExtractionCandidate with source_files set.
        """
        self.scan()

        # Normalize source file paths to be relative to repo root
        relative_paths = []
        for sf in candidate.source_files:
            sf_path = Path(sf)
            if sf_path.is_absolute():
                try:
                    relative_paths.append(str(sf_path.relative_to(self.repo_root)))
                except ValueError:
                    relative_paths.append(sf)
            else:
                relative_paths.append(sf)

        candidate.callers = self.get_callers(relative_paths)
        candidate.callees = self.get_callees(relative_paths)
