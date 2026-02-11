"""Repository analyzer — scans a Git repo and identifies extraction candidates."""

from __future__ import annotations

from pathlib import Path

from ale.models.candidate import CodebaseSummary, ExtractionCandidate
from ale.utils.git_ops import ensure_local_repo
from ale.utils.file_scanner import scan_project_files, classify_file


class AnalysisResult:
    """Container for the full analysis output: summary + candidates."""

    def __init__(
        self,
        summary: CodebaseSummary,
        candidates: list[ExtractionCandidate],
    ):
        self.summary = summary
        self.candidates = candidates


class RepoAnalyzer:
    """Analyzes a Git repository to find features suitable for agentic extraction."""

    def __init__(self, repo_path: str):
        self.repo_path = ensure_local_repo(repo_path)
        self.candidates: list[ExtractionCandidate] = []
        self.summary = CodebaseSummary()
        self._ir_modules: dict[str, object] = {}

    def analyze(self, depth: str = "standard") -> AnalysisResult:
        """Run analysis on the repo and return an AnalysisResult.

        Args:
            depth: Analysis depth — "quick" (file-level heuristics only),
                   "standard" (+ AST analysis), "deep" (+ LLM-assisted).
        """
        project_files = scan_project_files(self.repo_path)

        if not project_files:
            return AnalysisResult(summary=self.summary, candidates=[])

        # Build the codebase summary (always runs)
        self._build_summary(project_files)

        # Phase 1: File-level heuristic analysis (always runs)
        self._analyze_file_structure(project_files)

        # Phase 2: Code-level analysis (standard and deep)
        if depth in ("standard", "deep"):
            self._analyze_code_patterns(project_files)
            self._score_candidates()

        # Phase 3: LLM-assisted analysis (deep only)
        if depth == "deep":
            self._analyze_with_llm(project_files)

        # Add the whole-codebase candidate
        self._add_whole_codebase_candidate(project_files)

        sorted_candidates = sorted(
            self.candidates, key=lambda c: c.overall_score, reverse=True
        )
        return AnalysisResult(summary=self.summary, candidates=sorted_candidates)

    # ------------------------------------------------------------------
    # Codebase summary
    # ------------------------------------------------------------------

    def _build_summary(self, project_files: list[Path]) -> None:
        """Build an aggregate summary of the entire codebase."""
        files_by_lang: dict[str, int] = {}
        total_lines = 0
        top_level_dirs: set[str] = set()
        has_tests = False
        has_ci = False

        for f in project_files:
            lang = classify_file(f) or "other"
            files_by_lang[lang] = files_by_lang.get(lang, 0) + 1

            try:
                line_count = len(f.read_text(errors="replace").splitlines())
                total_lines += line_count
            except Exception:
                pass

            try:
                rel = f.relative_to(self.repo_path)
                if len(rel.parts) > 1:
                    top_level_dirs.add(rel.parts[0])
            except ValueError:
                pass

            rel_str = str(f.relative_to(self.repo_path))
            if "test" in rel_str.lower() or "spec" in rel_str.lower():
                has_tests = True

        ci_patterns = [
            ".github/workflows", ".gitlab-ci.yml", "Jenkinsfile",
            ".circleci", ".travis.yml", "azure-pipelines.yml",
        ]
        for pattern in ci_patterns:
            if (self.repo_path / pattern).exists():
                has_ci = True
                break

        # Parse all Python files for richer metrics
        ir_modules = self._parse_all_python_files(project_files)
        total_funcs = 0
        total_classes = 0
        total_constants = 0
        ext_packages: set[str] = set()
        documented_symbols = 0
        typed_params = 0
        total_params = 0
        total_public_symbols = 0

        from ale.ir.models import SymbolKind, Visibility

        for mod in ir_modules:
            for sym in mod.symbols:
                if sym.kind == SymbolKind.FUNCTION:
                    total_funcs += 1
                elif sym.kind == SymbolKind.CLASS:
                    total_classes += 1
                elif sym.kind == SymbolKind.CONSTANT:
                    total_constants += 1

                if sym.visibility == Visibility.PUBLIC and sym.kind in (
                    SymbolKind.FUNCTION, SymbolKind.CLASS,
                ):
                    total_public_symbols += 1
                    if sym.docstring:
                        documented_symbols += 1

                for p in sym.parameters:
                    total_params += 1
                    if p.type_hint:
                        typed_params += 1

            for dep in mod.imports:
                if dep.is_external:
                    ext_packages.add(dep.target.split(".")[0])

        purpose = self._infer_purpose(top_level_dirs, ext_packages, files_by_lang)
        capabilities = self._infer_capabilities(ir_modules)
        description = self._build_description(ir_modules)

        self.summary = CodebaseSummary(
            total_files=len(project_files),
            total_lines=total_lines,
            files_by_language=files_by_lang,
            total_modules=len(ir_modules),
            total_functions=total_funcs,
            total_classes=total_classes,
            total_constants=total_constants,
            external_packages=sorted(ext_packages),
            internal_module_count=len(ir_modules),
            docstring_coverage=(
                documented_symbols / total_public_symbols
                if total_public_symbols > 0 else 0.0
            ),
            type_hint_coverage=(
                typed_params / total_params
                if total_params > 0 else 0.0
            ),
            has_tests=has_tests,
            has_ci_config=has_ci,
            description=description,
            purpose=purpose,
            top_level_packages=sorted(top_level_dirs),
            key_capabilities=capabilities,
        )

    def _parse_all_python_files(self, project_files: list[Path]) -> list:
        """Parse all Python files and cache the IR modules."""
        from ale.ir.python_parser import parse_python_file

        modules = []
        for f in project_files:
            if f.suffix != ".py":
                continue
            try:
                ir_mod = parse_python_file(str(f), str(self.repo_path))
                modules.append(ir_mod)
                self._ir_modules[str(f)] = ir_mod
            except Exception:
                continue
        return modules

    def _build_description(self, ir_modules: list) -> str:
        """Synthesize a human-readable description of what this codebase does.

        Tries in order:
        1. pyproject.toml / setup.cfg [project] description
        2. First meaningful paragraph of README.md
        3. Top-level __init__.py or __main__.py module docstring
        4. Synthesis from the most informative module docstrings
        """
        # 1. pyproject.toml / setup.cfg
        desc = self._read_project_metadata_description()
        if desc:
            return desc

        # 2. README.md — first non-heading, non-badge paragraph
        desc = self._read_readme_description()
        if desc:
            return desc

        # 3. Top-level module docstrings (__init__.py, __main__.py, or the
        #    primary package's __init__.py)
        for mod in ir_modules:
            path_parts = mod.path.replace("\\", "/").split("/")
            basename = path_parts[-1] if path_parts else ""
            if basename in ("__init__.py", "__main__.py") and len(path_parts) <= 2:
                if mod.docstring:
                    return self._first_sentence_or_paragraph(mod.docstring)

        # 4. Gather all module docstrings, pick the most informative ones
        docstrings: list[tuple[str, str]] = []  # (module_path, docstring)
        for mod in ir_modules:
            if mod.docstring:
                docstrings.append((mod.path, mod.docstring))

        if docstrings:
            # Pick up to 3 module docstrings and combine them
            summaries = []
            for _path, ds in docstrings[:5]:
                sentence = self._first_sentence(ds)
                if sentence and len(sentence) > 15:
                    summaries.append(sentence)
                if len(summaries) >= 3:
                    break
            if summaries:
                return ". ".join(summaries)

        return ""

    def _read_project_metadata_description(self) -> str:
        """Read description from pyproject.toml or setup.cfg."""
        # pyproject.toml
        pyproject = self.repo_path / "pyproject.toml"
        if pyproject.exists():
            try:
                text = pyproject.read_text(errors="replace")
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("description"):
                        # description = "..."
                        parts = stripped.split("=", 1)
                        if len(parts) == 2:
                            val = parts[1].strip().strip('"').strip("'")
                            if val and len(val) > 10:
                                return val
            except Exception:
                pass

        # setup.cfg
        setupcfg = self.repo_path / "setup.cfg"
        if setupcfg.exists():
            try:
                text = setupcfg.read_text(errors="replace")
                in_metadata = False
                for line in text.splitlines():
                    if line.strip() == "[metadata]":
                        in_metadata = True
                        continue
                    if in_metadata and line.startswith("["):
                        break
                    if in_metadata and line.strip().startswith("description"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            val = parts[1].strip()
                            if val and len(val) > 10:
                                return val
            except Exception:
                pass

        return ""

    def _read_readme_description(self) -> str:
        """Extract the first descriptive paragraph from README."""
        for name in ("README.md", "README.rst", "README.txt", "README"):
            readme = self.repo_path / name
            if readme.exists():
                try:
                    text = readme.read_text(errors="replace")
                    return self._extract_readme_summary(text)
                except Exception:
                    pass
        return ""

    @staticmethod
    def _extract_readme_summary(text: str) -> str:
        """Pull the first real paragraph from markdown/rst README."""
        lines = text.splitlines()
        paragraph_lines: list[str] = []
        found_content = False

        for line in lines:
            stripped = line.strip()

            # Skip headings, badges, blank lines, HTML, and dividers
            if not stripped:
                if found_content and paragraph_lines:
                    break  # end of first paragraph
                continue
            if stripped.startswith(("#", "=", "-", "!", "[!", "<", "```", "---", "***")):
                if found_content and paragraph_lines:
                    break
                continue
            if stripped.startswith("[![") or stripped.startswith("!["):
                continue

            found_content = True
            paragraph_lines.append(stripped)

        if not paragraph_lines:
            return ""

        paragraph = " ".join(paragraph_lines)
        # Cap at ~200 chars
        if len(paragraph) > 200:
            cut = paragraph[:200].rfind(". ")
            if cut > 80:
                return paragraph[: cut + 1]
            return paragraph[:200].rstrip() + "..."
        return paragraph

    @staticmethod
    def _first_sentence_or_paragraph(text: str) -> str:
        """Return the first sentence or first paragraph, whichever is shorter."""
        text = text.strip()
        # First paragraph
        para = text.split("\n\n")[0].replace("\n", " ").strip()
        # First sentence
        sentence = ""
        for end in (". ", ".\n"):
            idx = para.find(end)
            if idx > 0:
                candidate = para[: idx + 1]
                if not sentence or len(candidate) < len(sentence):
                    sentence = candidate

        result = sentence if sentence and len(sentence) < len(para) else para
        if len(result) > 200:
            return result[:200].rstrip() + "..."
        return result

    @staticmethod
    def _first_sentence(text: str) -> str:
        """Return the first sentence of a string."""
        text = text.strip().split("\n\n")[0].replace("\n", " ").strip()
        for end in (". ", ".\n"):
            idx = text.find(end)
            if idx > 0:
                return text[: idx + 1]
        # If no period, return the whole first paragraph (capped)
        if len(text) > 150:
            return text[:150].rstrip() + "..."
        return text

    def _infer_purpose(
        self,
        top_dirs: set[str],
        ext_packages: set[str],
        files_by_lang: dict[str, int],
    ) -> str:
        """Infer the project's purpose from its structure and dependencies."""
        indicators = []

        web_frameworks = {"flask", "django", "fastapi", "tornado", "sanic", "starlette"}
        found_web = web_frameworks & ext_packages
        if found_web:
            indicators.append(f"Web application ({', '.join(sorted(found_web))})")

        data_pkgs = {"pandas", "numpy", "scipy", "sklearn", "tensorflow", "torch", "keras"}
        found_data = data_pkgs & ext_packages
        if found_data:
            indicators.append(f"Data/ML project ({', '.join(sorted(found_data))})")

        cli_pkgs = {"click", "typer", "argparse", "fire"}
        found_cli = cli_pkgs & ext_packages
        if found_cli:
            indicators.append("CLI tool")

        test_pkgs = {"pytest", "unittest", "nose"}
        if test_pkgs & ext_packages:
            indicators.append("Includes test suite")

        primary_lang = (
            max(files_by_lang.items(), key=lambda x: x[1])[0]
            if files_by_lang else "unknown"
        )
        indicators.append(f"Primary language: {primary_lang}")

        if not indicators:
            return f"Software project with {sum(files_by_lang.values())} source files"

        return "; ".join(indicators)

    def _infer_capabilities(self, ir_modules: list) -> list[str]:
        """Extract key capabilities from class/function names."""
        from ale.ir.models import SymbolKind, Visibility

        capability_keywords = {
            "auth": "Authentication", "login": "Authentication",
            "parse": "Parsing", "serial": "Serialization",
            "valid": "Validation", "cache": "Caching",
            "log": "Logging", "config": "Configuration",
            "route": "Routing", "api": "API",
            "database": "Database", "db": "Database",
            "queue": "Message Queue", "email": "Email",
            "upload": "File Upload", "search": "Search",
            "encrypt": "Encryption", "schedule": "Scheduling",
            "notify": "Notifications", "websocket": "WebSocket",
            "test": "Testing", "migrate": "Migration",
            "monitor": "Monitoring", "metric": "Metrics",
            "export": "Data Export", "transform": "Data Transformation",
            "generate": "Code Generation", "template": "Templating",
            "render": "Rendering", "analyze": "Analysis",
            "scan": "Scanning",
        }

        found: set[str] = set()
        for mod in ir_modules:
            for sym in mod.symbols:
                if sym.visibility != Visibility.PUBLIC:
                    continue
                if sym.kind not in (SymbolKind.FUNCTION, SymbolKind.CLASS):
                    continue
                name_lower = sym.name.lower()
                for keyword, capability in capability_keywords.items():
                    if keyword in name_lower:
                        found.add(capability)

        return sorted(found)[:10]

    # ------------------------------------------------------------------
    # Phase 1: File heuristics
    # ------------------------------------------------------------------

    def _analyze_file_structure(self, project_files: list[Path]):
        """Identify candidates based on file organization patterns."""
        utils_dirs = {"utils", "helpers", "lib", "common", "shared", "tools", "core"}
        grouped: dict[str, list[Path]] = {}

        for f in project_files:
            classification = classify_file(f)
            if classification:
                parent = f.parent.name
                if parent in utils_dirs:
                    key = f.stem
                    grouped.setdefault(key, []).append(f)

        for name, files in grouped.items():
            self.candidates.append(
                ExtractionCandidate(
                    name=name,
                    description=f"Utility module: {name}",
                    source_files=[str(f) for f in files],
                    entry_points=[f.stem for f in files],
                    tags=["utility", "auto-detected"],
                )
            )

    # ------------------------------------------------------------------
    # Phase 2: Code-level analysis + scoring
    # ------------------------------------------------------------------

    def _analyze_code_patterns(self, project_files: list[Path]):
        """Enrich candidates with IR-derived data."""
        try:
            from ale.analyzers.code_analyzer import CodeAnalyzer
            from ale.analyzers.context_builder import ContextBuilder

            code_analyzer = CodeAnalyzer(self.repo_path)
            context_builder = ContextBuilder(self.repo_path)

            for candidate in self.candidates:
                try:
                    code_analyzer.analyze_candidate(candidate, self.repo_path)
                except Exception:
                    pass

                try:
                    context_builder.build_context(candidate)
                except Exception:
                    pass

        except ImportError:
            pass

    def _score_candidates(self) -> None:
        """Apply real 7-dimension scoring and size classification to all candidates."""
        from ale.analyzers.scorer import score_candidate

        for candidate in self.candidates:
            try:
                score_candidate(candidate)
            except Exception:
                pass
            # Auto-classify size after scoring (uses symbols/files/entry_points)
            candidate.classify_size()

    # ------------------------------------------------------------------
    # Phase 3: LLM (stub)
    # ------------------------------------------------------------------

    def _analyze_with_llm(self, project_files: list[Path]):
        """Use LLM to identify higher-level extractable features."""
        # TODO: Implement LLM-assisted analysis
        pass

    # ------------------------------------------------------------------
    # Whole-codebase candidate
    # ------------------------------------------------------------------

    def _add_whole_codebase_candidate(self, project_files: list[Path]) -> None:
        """Add a special candidate representing the entire codebase."""
        from ale.ir.models import SymbolKind, Visibility

        all_files = [str(f) for f in project_files]
        all_entry_points: list[str] = []
        all_symbols: list[dict] = []

        for mod in self._ir_modules.values():
            for sym in mod.symbols:
                if sym.visibility == Visibility.PUBLIC and sym.kind in (
                    SymbolKind.FUNCTION, SymbolKind.CLASS,
                ):
                    all_entry_points.append(sym.name)
                    all_symbols.append({
                        "name": sym.name,
                        "kind": sym.kind.value if hasattr(sym.kind, "value") else str(sym.kind),
                        "signature": sym.name,
                        "docstring": sym.docstring or "",
                    })

        s = self.summary

        # Lead with what the project does, then add stats
        desc_lead = s.description or s.purpose or "Software project"
        desc = (
            f"{desc_lead}. "
            f"{s.total_files} files, {s.total_lines:,} lines, "
            f"{s.total_functions} functions, {s.total_classes} classes"
        )

        context_lead = s.description or s.purpose
        whole_candidate = ExtractionCandidate(
            name="__whole_codebase__",
            description=desc,
            source_files=all_files,
            entry_points=all_entry_points[:50],
            tags=["whole-codebase", "full-repository"],
            dependencies_external=self.summary.external_packages,
            dependencies_internal=[],
            context_summary=(
                f"Complete codebase: {context_lead}. "
                f"Contains {s.total_modules} modules with "
                f"{s.total_functions} functions and {s.total_classes} classes."
            ),
            symbols=all_symbols[:100],
        )

        try:
            from ale.analyzers.scorer import score_candidate
            score_candidate(whole_candidate)
        except Exception:
            pass

        whole_candidate.classify_size()
        self.candidates.append(whole_candidate)
