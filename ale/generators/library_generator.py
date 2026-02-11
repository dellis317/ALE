"""Library generator — converts extraction candidates into Agentic Library specs."""

from pathlib import Path

import yaml

from ale.analyzers.repo_analyzer import RepoAnalyzer
from ale.models.agentic_library import AgenticLibrary, InstructionStep, Guardrail, ValidationCriterion


class LibraryGenerator:
    """Generates an Agentic Library specification from a repo feature."""

    def __init__(self, repo_path: str, output_dir: str = "./agentic_libs"):
        self.repo_path = repo_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, feature_name: str, enrich: bool = True) -> str | None:
        """Generate an Agentic Library for the named feature.

        Args:
            feature_name: Name of the candidate to extract.
            enrich: Whether to use LLM for enhancement.

        Returns:
            Path to the generated library file, or None on failure.
        """
        # Step 1: Re-analyze to find the candidate
        analyzer = RepoAnalyzer(self.repo_path)
        candidates = analyzer.analyze()
        candidate = next((c for c in candidates if c.name == feature_name), None)

        if not candidate:
            return None

        # Step 2: Build the initial library from source analysis
        library = self._build_from_candidate(candidate)

        # Step 3: Enrich with LLM if requested
        if enrich:
            library = self._enrich_with_llm(library)

        # Step 4: Write the output
        return self._write_library(library)

    def _build_from_candidate(self, candidate) -> AgenticLibrary:
        """Create an initial AgenticLibrary from source code analysis."""
        library = AgenticLibrary(
            name=candidate.name,
            description=candidate.description,
            source_repo=self.repo_path,
            source_paths=candidate.source_files,
            tags=candidate.tags,
        )

        # Read source files and build initial instructions
        for i, src_file in enumerate(candidate.source_files):
            path = Path(src_file)
            if path.exists():
                content = path.read_text(errors="replace")
                library.instructions.append(
                    InstructionStep(
                        order=i + 1,
                        title=f"Implement {path.stem}",
                        description=f"Recreate the functionality from {path.name}",
                        code_sketch=self._extract_code_sketch(content),
                    )
                )

        # Add default guardrails
        library.guardrails = [
            Guardrail(
                rule="Follow the target project's existing code style and conventions",
                severity="must",
            ),
            Guardrail(
                rule="Use the target project's existing dependencies where possible",
                severity="should",
            ),
            Guardrail(
                rule="Include error handling appropriate to the target project's patterns",
                severity="must",
            ),
        ]

        # Add default validation
        library.validation = [
            ValidationCriterion(
                description="Feature works as described in the overview",
                test_approach="Write a test that exercises the primary use case",
                expected_behavior="Test passes without errors",
            ),
        ]

        return library

    def _extract_code_sketch(self, source_code: str) -> str:
        """Extract a language-agnostic pseudocode sketch from source."""
        # For now, return a simplified version. LLM enrichment will improve this.
        lines = source_code.split("\n")
        # Extract function/class signatures as a sketch
        sketch_lines = []
        for line in lines:
            stripped = line.strip()
            if any(
                stripped.startswith(kw)
                for kw in ["def ", "class ", "function ", "export ", "pub fn ", "func "]
            ):
                sketch_lines.append(stripped)
        return "\n".join(sketch_lines) if sketch_lines else "# See source files for reference"

    def _enrich_with_llm(self, library: AgenticLibrary) -> AgenticLibrary:
        """Use LLM to improve the library specification.

        Enhancements:
        - Better descriptions and overview
        - Clearer, more generalizable instructions
        - Security-aware guardrails
        - More thorough validation criteria
        """
        # TODO: Implement LLM enrichment via Anthropic API
        return library

    def _write_library(self, library: AgenticLibrary) -> str:
        """Serialize the library to a YAML file."""
        output_path = self.output_dir / f"{library.name}.agentic.yaml"

        data = {
            "agentic_library": {
                "manifest": {
                    "name": library.name,
                    "version": library.version,
                    "description": library.description,
                    "source_repo": library.source_repo,
                    "complexity": library.complexity.value,
                    "tags": library.tags,
                    "language_agnostic": library.language_agnostic,
                },
                "overview": library.overview,
                "instructions": [
                    {
                        "step": s.order,
                        "title": s.title,
                        "description": s.description,
                        "code_sketch": s.code_sketch,
                        "notes": s.notes,
                    }
                    for s in library.instructions
                ],
                "guardrails": [
                    {
                        "rule": g.rule,
                        "severity": g.severity,
                        "rationale": g.rationale,
                    }
                    for g in library.guardrails
                ],
                "validation": [
                    {
                        "description": v.description,
                        "test_approach": v.test_approach,
                        "expected_behavior": v.expected_behavior,
                    }
                    for v in library.validation
                ],
                "capability_dependencies": [d.value for d in library.capability_deps],
            }
        }

        with open(output_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, width=100)

        return str(output_path)
