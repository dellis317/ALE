"""ALE CLI — the main entry point for the Agentic Library Extractor."""

import click
from rich.console import Console
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


@main.command()
@click.argument("library_path")
def validate(library_path: str):
    """Validate an Agentic Library specification file."""
    from ale.utils.validator import validate_library

    console.print(f"\n[bold blue]ALE[/] — Validating: {library_path}\n")
    issues = validate_library(library_path)

    if not issues:
        console.print("[green]Valid![/] No issues found.")
    else:
        for issue in issues:
            console.print(f"  [red]•[/] {issue}")


if __name__ == "__main__":
    main()
