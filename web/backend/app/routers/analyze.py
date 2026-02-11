"""Analyze router -- repository analysis and library generation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ale.analyzers.repo_analyzer import RepoAnalyzer
from ale.generators.library_generator import LibraryGenerator

from app.models.api import (
    AnalyzeRequest,
    CandidateResponse,
    GenerateRequest,
    GenerateResponse,
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
        estimated_instruction_steps=candidate.estimated_instruction_steps,
        dependencies_external=candidate.dependencies_external,
        dependencies_internal=candidate.dependencies_internal,
    )


@router.post(
    "/api/analyze",
    response_model=list[CandidateResponse],
    summary="Analyze a repository for extraction candidates",
)
async def analyze_repo(request: AnalyzeRequest):
    """Scan a repository and return ranked extraction candidates.

    The ``depth`` parameter controls how thorough the analysis is:
    - ``quick``: file-level heuristics only
    - ``standard``: includes AST analysis
    - ``deep``: includes LLM-assisted analysis
    """
    if not request.repo_path:
        raise HTTPException(status_code=400, detail="repo_path is required")

    try:
        analyzer = RepoAnalyzer(request.repo_path)
        candidates = analyzer.analyze(depth=request.depth)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return [_candidate_to_response(c) for c in candidates]


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
