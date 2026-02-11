"""ALE CLI — the main entry point for the Agentic Library Extractor."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ale import __version__

console = Console()


@click.group()
@click.version_option(version=__version__)
def main():
    """ALE — Agentic Library Extractor.

    Analyze Git repos, discover extractable features, and generate
    agentic library blueprints that AI agents can follow to recreate
    functionality in any project.
    """


# ── Analyze ──────────────────────────────────────────────────────────


@main.command()
@click.argument("repo_path")
@click.option("--depth", default="standard", type=click.Choice(["quick", "standard", "deep"]))
@click.option("--output", "-o", default=None, help="Output directory for results")
def analyze(repo_path: str, depth: str, output: str | None):
    """Analyze a Git repo and surface extraction candidates.

    REPO_PATH can be a local path or a Git URL (will be cloned).
    """
    from ale.analyzers.repo_analyzer import RepoAnalyzer

    console.print(f"\n[bold blue]ALE[/] — Analyzing repository: {repo_path}\n")

    analyzer = RepoAnalyzer(repo_path)
    candidates = analyzer.analyze(depth=depth)

    if not candidates:
        console.print("[yellow]No extraction candidates found.[/]")
        return

    table = Table(title=f"Extraction Candidates ({len(candidates)} found)")
    table.add_column("Rank", style="dim", width=4)
    table.add_column("Name", style="cyan")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Files", justify="right")
    table.add_column("Description")

    for i, candidate in enumerate(sorted(candidates, key=lambda c: c.overall_score, reverse=True)):
        table.add_row(
            str(i + 1),
            candidate.name,
            f"{candidate.overall_score:.2f}",
            str(len(candidate.source_files)),
            candidate.description[:60],
        )

    console.print(table)


# ── Extract ──────────────────────────────────────────────────────────


@main.command()
@click.argument("repo_path")
@click.argument("feature_name")
@click.option("--output", "-o", default="./agentic_libs", help="Output directory")
@click.option("--enrich/--no-enrich", default=True, help="Use LLM to enrich the output")
def extract(repo_path: str, feature_name: str, output: str, enrich: bool):
    """Extract a specific feature into an Agentic Library blueprint.

    First run 'ale analyze' to discover candidates, then use this command
    to extract a specific one.
    """
    from ale.generators.library_generator import LibraryGenerator

    console.print(f"\n[bold blue]ALE[/] — Extracting: {feature_name}\n")

    generator = LibraryGenerator(repo_path, output_dir=output)
    result = generator.generate(feature_name, enrich=enrich)

    if result:
        console.print(f"\n[green]Agentic Library written to:[/] {result}")
    else:
        console.print("[red]Extraction failed. See errors above.[/]")


# ── Validate ─────────────────────────────────────────────────────────


@main.command()
@click.argument("library_path")
@click.option("--strict", is_flag=True, help="Treat warnings as errors")
def validate(library_path: str, strict: bool):
    """Validate an Agentic Library against the executable spec.

    Runs all three gates: schema validation, semantic validation,
    and (if hooks are declared) the reference runner.
    """
    import yaml

    from ale.spec.schema_validator import validate_schema
    from ale.spec.semantic_validator import validate_semantics, Severity

    console.print(f"\n[bold blue]ALE[/] — Validating: {library_path}\n")

    try:
        with open(library_path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        console.print(f"  [red]Failed to parse:[/] {e}")
        return

    # Gate 1: Schema
    schema_issues = validate_schema(data)
    if schema_issues:
        console.print("[red]Schema validation FAILED:[/]")
        for issue in schema_issues:
            console.print(f"  [red]x[/] {issue}")
        return
    console.print("  [green]v[/] Schema validation passed")

    # Gate 2: Semantic
    sem_result = validate_semantics(data)
    if sem_result.errors:
        console.print("[red]Semantic validation FAILED:[/]")
        for issue in sem_result.errors:
            console.print(f"  [red]x[/] [{issue.code}] {issue.message}")
    else:
        console.print("  [green]v[/] Semantic validation passed")

    for w in sem_result.warnings:
        console.print(f"  [yellow]![/] [{w.code}] {w.message}")

    if strict and sem_result.warnings:
        console.print("\n[red]FAIL[/] (strict mode: warnings treated as errors)")
        return

    if sem_result.passed:
        console.print("\n[green]Valid![/]")


# ── Conformance ──────────────────────────────────────────────────────


@main.command()
@click.argument("library_path")
@click.option("--working-dir", "-w", default=".", help="Directory to run hooks in")
def conformance(library_path: str, working_dir: str):
    """Run the full executable spec conformance check (schema + semantics + hooks).

    This runs the reference runner against a library, including executing
    any declared validation hooks.
    """
    from ale.spec.reference_runner import ReferenceRunner

    console.print(f"\n[bold blue]ALE[/] — Conformance check: {library_path}\n")

    runner = ReferenceRunner(working_dir=working_dir)
    result = runner.run(library_path)

    # Summary
    console.print(Panel(result.summary(), title="Conformance Result"))

    # Details
    if result.schema_errors:
        console.print("\n[red]Schema Errors:[/]")
        for e in result.schema_errors:
            console.print(f"  [red]x[/] {e}")

    if result.semantic_errors:
        console.print("\n[red]Semantic Errors:[/]")
        for e in result.semantic_errors:
            console.print(f"  [red]x[/] {e}")

    if result.semantic_warnings:
        console.print("\n[yellow]Semantic Warnings:[/]")
        for w in result.semantic_warnings:
            console.print(f"  [yellow]![/] {w}")

    if result.hook_results:
        console.print("\n[bold]Hook Results:[/]")
        for h in result.hook_results:
            status = "[green]PASS[/]" if h.passed else "[red]FAIL[/]"
            console.print(f"  {status} {h.description} ({h.duration_ms}ms)")
            if h.error:
                console.print(f"       [red]{h.error}[/]")


# ── Registry ─────────────────────────────────────────────────────────


@main.group()
def registry():
    """Manage the Agentic Library registry."""


@registry.command()
@click.argument("library_path")
@click.option("--registry-dir", "-r", default=".ale_registry", help="Registry directory")
def publish(library_path: str, registry_dir: str):
    """Publish an Agentic Library to the local registry."""
    from ale.registry.local_registry import LocalRegistry

    console.print(f"\n[bold blue]ALE[/] — Publishing: {library_path}\n")

    reg = LocalRegistry(registry_dir)
    entry = reg.publish(library_path)

    verified = "[green]verified[/]" if entry.is_verified else "[yellow]unverified[/]"
    console.print(f"  Published: {entry.qualified_id} ({verified})")


@registry.command(name="list")
@click.option("--registry-dir", "-r", default=".ale_registry", help="Registry directory")
def list_entries(registry_dir: str):
    """List all libraries in the registry."""
    from ale.registry.local_registry import LocalRegistry

    reg = LocalRegistry(registry_dir)
    entries = reg.list_all()

    if not entries:
        console.print("[yellow]Registry is empty.[/]")
        return

    table = Table(title=f"Registry ({len(entries)} libraries)")
    table.add_column("Name", style="cyan")
    table.add_column("Version")
    table.add_column("Verified", justify="center")
    table.add_column("Description")

    for entry in entries:
        verified = "[green]Y[/]" if entry.is_verified else "[red]N[/]"
        table.add_row(entry.name, entry.version, verified, entry.description[:50])

    console.print(table)


@registry.command()
@click.argument("query")
@click.option("--registry-dir", "-r", default=".ale_registry", help="Registry directory")
@click.option("--tag", "-t", multiple=True, help="Filter by tag")
@click.option("--verified-only", is_flag=True, help="Only show verified libraries")
def search(query: str, registry_dir: str, tag: tuple, verified_only: bool):
    """Search the registry for libraries."""
    from ale.registry.local_registry import LocalRegistry
    from ale.registry.models import SearchQuery

    reg = LocalRegistry(registry_dir)
    result = reg.search(
        SearchQuery(text=query, tags=list(tag), verified_only=verified_only)
    )

    if not result.entries:
        console.print("[yellow]No matching libraries found.[/]")
        return

    for entry in result.entries:
        verified = "[green]verified[/]" if entry.is_verified else ""
        console.print(f"  [cyan]{entry.qualified_id}[/] {verified}")
        console.print(f"    {entry.description}")


# ── Drift ────────────────────────────────────────────────────────────


@main.command()
@click.argument("repo_path")
@click.option("--library", "-l", default=None, help="Check specific library (default: all)")
def drift(repo_path: str, library: str | None):
    """Check for drift between applied libraries and repo state."""
    from ale.sync.drift import DriftDetector

    console.print(f"\n[bold blue]ALE[/] — Drift detection: {repo_path}\n")

    detector = DriftDetector(repo_path)

    if library:
        report = detector.check(library)
        reports = [report]
    else:
        reports = detector.check_all()

    if not reports:
        console.print("[yellow]No applied libraries found (no provenance records).[/]")
        return

    for report in reports:
        if report.has_drift:
            console.print(f"  [red]DRIFT[/] {report.summary()}")
            for detail in report.details:
                console.print(f"    - {detail}")
        else:
            console.print(f"  [green]OK[/] {report.summary()}")


# ── Schema ───────────────────────────────────────────────────────────


@main.command(name="schema")
def dump_schema():
    """Print the JSON Schema for the Agentic Library specification."""
    import json

    from ale.spec.schema import get_schema

    console.print(json.dumps(get_schema(), indent=2))


if __name__ == "__main__":
    main()
