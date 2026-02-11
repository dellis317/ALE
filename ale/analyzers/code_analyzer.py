"""Code analyzer -- enriches extraction candidates with IR data.

Uses the Python IR parser to extract real symbols, entry points,
dependencies, and build rich descriptions from source code analysis.
"""

from __future__ import annotations

from pathlib import Path

from ale.ir.python_parser import parse_python_file
from ale.ir.models import IRModule, IRSymbol, SymbolKind, Visibility


class CodeAnalyzer:
    """Analyzes a candidate's source files using the IR parser.

    Extracts real symbols, builds rich descriptions, and identifies
    entry points and dependencies from parsed IR data.
    """

    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root)

    def analyze_candidate(self, candidate, repo_root: str | Path | None = None) -> None:
        """Enrich an ExtractionCandidate with IR-derived data in place.

        Parses each source file, extracts symbols, entry points, dependencies,
        and builds a rich context summary. Mutates the candidate directly.

        Args:
            candidate: An ExtractionCandidate to enrich.
            repo_root: Optional override for repo root path.
        """
        root = Path(repo_root) if repo_root else self.repo_root
        all_symbols: list[dict] = []
        all_entry_points: list[str] = []
        external_deps: set[str] = set()
        internal_deps: set[str] = set()
        modules: list[IRModule] = []
        descriptions: list[str] = []

        for source_file in candidate.source_files:
            file_path = Path(source_file)
            if not file_path.is_absolute():
                file_path = root / file_path

            if not file_path.exists() or not file_path.suffix == ".py":
                continue

            try:
                ir_module = parse_python_file(str(file_path), str(root))
            except Exception:
                continue

            modules.append(ir_module)

            # Extract symbols
            for sym in ir_module.symbols:
                sym_dict = {
                    "name": sym.name,
                    "kind": sym.kind.value if hasattr(sym.kind, "value") else str(sym.kind),
                    "signature": self._build_signature(sym),
                    "docstring": sym.docstring or "",
                }
                all_symbols.append(sym_dict)

                # Public functions/classes become entry points
                if sym.visibility == Visibility.PUBLIC and sym.kind in (
                    SymbolKind.FUNCTION,
                    SymbolKind.CLASS,
                ):
                    all_entry_points.append(sym.name)

            # Extract dependencies
            for dep in ir_module.imports:
                if dep.is_external:
                    # Extract the top-level package name
                    pkg = dep.target.split(".")[0]
                    external_deps.add(pkg)
                else:
                    internal_deps.add(dep.target)

            # Build description from module docstring + symbols
            module_desc = self._build_module_description(ir_module)
            if module_desc:
                descriptions.append(module_desc)

        # Update candidate fields
        candidate.symbols = all_symbols

        if all_entry_points:
            candidate.entry_points = all_entry_points

        if external_deps:
            candidate.dependencies_external = sorted(external_deps)

        if internal_deps:
            candidate.dependencies_internal = sorted(internal_deps)

        # Build context summary
        if descriptions:
            candidate.context_summary = " ".join(descriptions)
        else:
            candidate.context_summary = candidate.description

        # Build rich description from IR data
        rich_desc = self._build_rich_description(modules, candidate.name)
        if rich_desc:
            candidate.description = rich_desc

    def _build_signature(self, symbol: IRSymbol) -> str:
        """Build a human-readable signature for a symbol."""
        if symbol.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            params = ", ".join(
                f"{p.name}: {p.type_hint}" if p.type_hint else p.name
                for p in symbol.parameters
            )
            ret = f" -> {symbol.return_type}" if symbol.return_type else ""
            async_prefix = "async " if symbol.is_async else ""
            return f"{async_prefix}def {symbol.name}({params}){ret}"
        elif symbol.kind == SymbolKind.CLASS:
            bases = ", ".join(symbol.base_classes) if symbol.base_classes else ""
            return f"class {symbol.name}({bases})" if bases else f"class {symbol.name}"
        else:
            return symbol.name

    def _build_module_description(self, module: IRModule) -> str:
        """Build a description from an IR module's content."""
        parts = []

        # Check for module-level docstring (first symbol might give a clue)
        # Count symbol types
        func_count = len(module.functions)
        class_count = len(module.classes)

        if class_count > 0:
            class_names = [s.name for s in module.classes[:3]]
            parts.append(f"Defines classes: {', '.join(class_names)}")
        if func_count > 0:
            func_names = [s.name for s in module.functions if s.visibility == Visibility.PUBLIC][:3]
            if func_names:
                parts.append(f"Public functions: {', '.join(func_names)}")

        return ". ".join(parts)

    def _build_rich_description(self, modules: list[IRModule], name: str) -> str:
        """Build a rich description from all parsed modules."""
        all_funcs = []
        all_classes = []

        for m in modules:
            all_funcs.extend(m.functions)
            all_classes.extend(m.classes)

        parts = []

        if all_classes:
            class_descriptions = []
            for cls in all_classes[:3]:
                desc = cls.name
                if cls.docstring:
                    first_line = cls.docstring.strip().split("\n")[0]
                    desc = f"{cls.name} -- {first_line}"
                class_descriptions.append(desc)
            parts.append(f"Provides: {'; '.join(class_descriptions)}")

        if all_funcs:
            pub_funcs = [f for f in all_funcs if f.visibility == Visibility.PUBLIC][:5]
            if pub_funcs:
                func_names = [f.name for f in pub_funcs]
                parts.append(f"Key functions: {', '.join(func_names)}")

        total_symbols = sum(len(m.symbols) for m in modules)
        total_deps_ext = sum(
            len([d for d in m.imports if d.is_external]) for m in modules
        )
        total_deps_int = sum(
            len([d for d in m.imports if not d.is_external]) for m in modules
        )

        parts.append(
            f"{total_symbols} symbols, {total_deps_ext} external deps, "
            f"{total_deps_int} internal deps"
        )

        return ". ".join(parts) if parts else f"Utility module: {name}"
