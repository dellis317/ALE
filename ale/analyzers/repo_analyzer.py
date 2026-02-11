"""Repository analyzer — scans a Git repo and identifies extraction candidates."""

from pathlib import Path

from ale.models.candidate import ExtractionCandidate
from ale.utils.git_ops import ensure_local_repo
from ale.utils.file_scanner import scan_project_files, classify_file


class RepoAnalyzer:
    """Analyzes a Git repository to find features suitable for agentic extraction."""

    def __init__(self, repo_path: str):
        self.repo_path = ensure_local_repo(repo_path)
        self.candidates: list[ExtractionCandidate] = []

    def analyze(self, depth: str = "standard") -> list[ExtractionCandidate]:
        """Run analysis on the repo and return ranked candidates.

        Args:
            depth: Analysis depth — "quick" (file-level heuristics only),
                   "standard" (+ AST analysis), "deep" (+ LLM-assisted).
        """
        project_files = scan_project_files(self.repo_path)

        if not project_files:
            return []

        # Phase 1: File-level heuristic analysis (always runs)
        self._analyze_file_structure(project_files)

        # Phase 2: Code-level analysis (standard and deep)
        if depth in ("standard", "deep"):
            self._analyze_code_patterns(project_files)

        # Phase 3: LLM-assisted analysis (deep only)
        if depth == "deep":
            self._analyze_with_llm(project_files)

        return sorted(self.candidates, key=lambda c: c.overall_score, reverse=True)

    def _analyze_file_structure(self, project_files: list[Path]):
        """Identify candidates based on file organization patterns.

        Looks for:
        - utils/ or helpers/ directories (high isolation potential)
        - Standalone modules with few imports
        - Well-named files suggesting a single responsibility
        """
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
                    isolation_score=0.7,
                    reuse_score=0.5,
                    complexity_score=0.6,
                    clarity_score=0.5,
                    tags=["utility", "auto-detected"],
                )
            )

    def _analyze_code_patterns(self, project_files: list[Path]):
        """Analyze code structure for extractable patterns.

        Uses the IR-based CodeAnalyzer and ContextBuilder to enrich
        each candidate with real symbol data, dependency information,
        and caller/callee context.
        """
        try:
            from ale.analyzers.code_analyzer import CodeAnalyzer
            from ale.analyzers.context_builder import ContextBuilder

            code_analyzer = CodeAnalyzer(self.repo_path)
            context_builder = ContextBuilder(self.repo_path)

            for candidate in self.candidates:
                try:
                    # Enrich with IR-derived symbols, deps, descriptions
                    code_analyzer.analyze_candidate(candidate, self.repo_path)
                except Exception:
                    pass  # Keep candidate with Phase 1 data

                try:
                    # Enrich with caller/callee context
                    context_builder.build_context(candidate)
                except Exception:
                    pass  # Keep candidate without context data

        except ImportError:
            # If analyzers are not available, skip Phase 2 gracefully
            pass

    def _analyze_with_llm(self, project_files: list[Path]):
        """Use LLM to identify higher-level extractable features.

        This catches things heuristics miss:
        - Business logic patterns that are broadly applicable
        - Design patterns implemented across multiple files
        - Features that could be generalized
        """
        # TODO: Implement LLM-assisted analysis
        pass
