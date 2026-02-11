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
        """Build a description from an IR module's content.

        Prioritizes the module-level docstring, then falls back
        to summarizing the public API.
        """
        # Lead with the module docstring — this tells us what the module does
        if module.docstring:
            first = module.docstring.strip().split("\n\n")[0].replace("\n", " ").strip()
            # Take just the first sentence if it's short enough
            dot = first.find(". ")
            if 0 < dot < 120:
                return first[: dot + 1]
            if len(first) <= 150:
                return first
            return first[:150].rstrip() + "..."

        # Fall back to class/function docstrings
        for cls in module.classes[:2]:
            if cls.docstring:
                line = cls.docstring.strip().split("\n")[0]
                return f"{cls.name}: {line}"

        for func in module.functions[:2]:
            if func.visibility == Visibility.PUBLIC and func.docstring:
                line = func.docstring.strip().split("\n")[0]
                return f"{func.name}: {line}"

        # Last resort: list the public API
        parts = []
        if module.classes:
            parts.append(f"Defines {', '.join(s.name for s in module.classes[:3])}")
        pub = [s.name for s in module.functions if s.visibility == Visibility.PUBLIC][:3]
        if pub:
            parts.append(f"provides {', '.join(pub)}")
        return "; ".join(parts) if parts else ""

    def _build_rich_description(self, modules: list[IRModule], name: str) -> str:
        """Build a human-readable description of what this component does.

        Leads with the most informative docstring to explain the use-case,
        then appends structural details.
        """
        # 1. Find the best docstring across all modules for this candidate
        lead = ""

        # Try module-level docstrings first
        for m in modules:
            if m.docstring:
                text = m.docstring.strip().split("\n\n")[0].replace("\n", " ").strip()
                dot = text.find(". ")
                if 0 < dot < 120:
                    text = text[: dot + 1]
                elif len(text) > 150:
                    text = text[:150].rstrip() + "..."
                if len(text) > len(lead):
                    lead = text

        # Try class docstrings
        if not lead:
            for m in modules:
                for cls in m.classes:
                    if cls.docstring:
                        line = cls.docstring.strip().split("\n")[0]
                        lead = f"{cls.name} -- {line}"
                        break
                if lead:
                    break

        # Try function docstrings
        if not lead:
            for m in modules:
                for func in m.functions:
                    if func.visibility == Visibility.PUBLIC and func.docstring:
                        line = func.docstring.strip().split("\n")[0]
                        lead = f"{func.name} -- {line}"
                        break
                if lead:
                    break

        # 2. Build supporting detail
        all_funcs = []
        all_classes = []
        for m in modules:
            all_funcs.extend(m.functions)
            all_classes.extend(m.classes)

        detail_parts = []
        if all_classes:
            detail_parts.append(
                f"{len(all_classes)} class{'es' if len(all_classes) != 1 else ''}"
            )
        pub_funcs = [f for f in all_funcs if f.visibility == Visibility.PUBLIC]
        if pub_funcs:
            detail_parts.append(
                f"{len(pub_funcs)} public function{'s' if len(pub_funcs) != 1 else ''}"
            )
        total_symbols = sum(len(m.symbols) for m in modules)
        if total_symbols:
            detail_parts.append(f"{total_symbols} symbols total")

        detail = ", ".join(detail_parts) if detail_parts else ""

        if lead and detail:
            return f"{lead} ({detail})"
        if lead:
            return lead
        if detail:
            return f"Utility module: {name} ({detail})"
        return f"Utility module: {name}"
