"""Analyze router -- repository analysis, library generation, and GitHub search."""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, HTTPException

from ale.analyzers.repo_analyzer import RepoAnalyzer
from ale.generators.library_generator import LibraryGenerator

from web.backend.app.models.api import (
    AnalyzeRequest,
    AnalyzeResponse,
    CandidateResponse,
    CodebaseSummaryResponse,
    GenerateRequest,
    GenerateResponse,
    GitHubRepoResult,
    GitHubSearchRequest,
    GitHubSearchResponse,
    ScoreDimensionResponse,
    ScoringBreakdownResponse,
)

router = APIRouter(tags=["analyze"])


def _candidate_to_response(candidate) -> CandidateResponse:
    """Convert an ExtractionCandidate dataclass to a Pydantic response."""
    scoring = candidate.scoring
    dimensions = [
        ScoreDimensionResponse(
            name=d.name,
            score=d.score,
            weight=d.weight,
            weighted_score=d.weighted_score,
            reasons=d.reasons,
            flags=d.flags,
        )
        for d in scoring.dimensions
    ]

    return CandidateResponse(
        name=candidate.name,
        description=candidate.description,
        source_files=candidate.source_files,
        entry_points=candidate.entry_points,
        scoring=ScoringBreakdownResponse(
            dimensions=dimensions,
            overall_score=scoring.overall_score,
            all_flags=scoring.all_flags,
            top_reasons=scoring.top_reasons,
        ),
        overall_score=candidate.overall_score,
        isolation_score=candidate.isolation_score,
        reuse_score=candidate.reuse_score,
        complexity_score=candidate.complexity_score,
        clarity_score=candidate.clarity_score,
        tags=candidate.tags,
        size_class=getattr(candidate, "size_class", ""),
        estimated_instruction_steps=candidate.estimated_instruction_steps,
        dependencies_external=candidate.dependencies_external,
        dependencies_internal=candidate.dependencies_internal,
        context_summary=getattr(candidate, "context_summary", ""),
        symbols=getattr(candidate, "symbols", []),
        callers=getattr(candidate, "callers", []),
        callees=getattr(candidate, "callees", []),
    )


def _summary_to_response(summary) -> CodebaseSummaryResponse:
    """Convert a CodebaseSummary dataclass to a Pydantic response."""
    return CodebaseSummaryResponse(
        total_files=summary.total_files,
        total_lines=summary.total_lines,
        files_by_language=summary.files_by_language,
        total_modules=summary.total_modules,
        total_functions=summary.total_functions,
        total_classes=summary.total_classes,
        total_constants=summary.total_constants,
        external_packages=summary.external_packages,
        internal_module_count=summary.internal_module_count,
        docstring_coverage=summary.docstring_coverage,
        type_hint_coverage=summary.type_hint_coverage,
        has_tests=summary.has_tests,
        has_ci_config=summary.has_ci_config,
        description=summary.description,
        purpose=summary.purpose,
        top_level_packages=summary.top_level_packages,
        key_capabilities=summary.key_capabilities,
    )


@router.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze a repository for extraction candidates",
)
async def analyze_repo(request: AnalyzeRequest):
    """Scan a repository and return a codebase summary with ranked candidates.

    The ``depth`` parameter controls how thorough the analysis is:
    - ``quick``: file-level heuristics only
    - ``standard``: includes AST analysis and real scoring
    - ``deep``: includes LLM-assisted analysis
    """
    if not request.repo_path:
        raise HTTPException(status_code=400, detail="repo_path is required")

    try:
        analyzer = RepoAnalyzer(request.repo_path)
        result = analyzer.analyze(depth=request.depth)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return AnalyzeResponse(
        summary=_summary_to_response(result.summary),
        candidates=[_candidate_to_response(c) for c in result.candidates],
    )


@router.post(
    "/api/generate",
    response_model=GenerateResponse,
    summary="Generate a library from a candidate",
)
async def generate_library(request: GenerateRequest):
    """Generate an Agentic Library specification for a named feature.

    The feature must have been previously identified by the analyzer. If
    ``enrich`` is true, LLM-assisted enrichment is applied to the output.
    """
    if not request.repo_path or not request.feature_name:
        raise HTTPException(
            status_code=400,
            detail="repo_path and feature_name are required",
        )

    try:
        generator = LibraryGenerator(
            repo_path=request.repo_path,
            output_dir=request.output_dir,
        )
        output_path = generator.generate(
            feature_name=request.feature_name,
            enrich=request.enrich,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if output_path is None:
        return GenerateResponse(
            success=False,
            message=f"Feature '{request.feature_name}' not found in repository analysis",
        )

    return GenerateResponse(
        success=True,
        output_path=output_path,
        message=f"Library generated at {output_path}",
    )


# ---------------------------------------------------------------------------
# GitHub Repository Search
# ---------------------------------------------------------------------------

GITHUB_API_BASE = "https://api.github.com"


@router.post(
    "/api/analyze/search-repos",
    response_model=GitHubSearchResponse,
    summary="Search GitHub repositories by keyword",
)
async def search_github_repos(request: GitHubSearchRequest):
    """Search GitHub for repositories matching a query.

    Useful for discovering repos to analyze without needing the URL upfront.
    Supports optional language filtering and sort order (stars, forks, updated).
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query is required")

    # Build the GitHub search query
    q = request.query.strip()
    if request.language:
        q += f" language:{request.language}"

    params = {
        "q": q,
        "sort": request.sort or "stars",
        "order": "desc",
        "per_page": min(request.per_page, 30),
    }

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Use GitHub token if available for higher rate limits
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GITHUB_API_BASE}/search/repositories",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:
            raise HTTPException(
                status_code=429,
                detail="GitHub API rate limit exceeded. Set GITHUB_TOKEN for higher limits.",
            )
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API error: {exc.response.status_code}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to reach GitHub API: {exc}",
        )

    results = []
    for item in data.get("items", []):
        results.append(
            GitHubRepoResult(
                full_name=item.get("full_name", ""),
                description=item.get("description") or "",
                html_url=item.get("html_url", ""),
                clone_url=item.get("clone_url", ""),
                stargazers_count=item.get("stargazers_count", 0),
                forks_count=item.get("forks_count", 0),
                language=item.get("language") or "",
                updated_at=item.get("updated_at", ""),
                topics=item.get("topics", []),
            )
        )

    return GitHubSearchResponse(
        total_count=data.get("total_count", 0),
        results=results,
    )
