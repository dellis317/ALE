"""LLM integration router.

Provides endpoints for LLM-powered library enrichment, preview generation,
guardrail suggestions, usage tracking, and budget management.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from ale.llm.client import LLMClient, LLMResponse
from ale.llm.prompts import (
    DESCRIPTION_PROMPT,
    GUARDRAIL_PROMPT,
    LIBRARY_ENRICHMENT_PROMPT,
    PREVIEW_PROMPT,
)
from ale.llm.usage_tracker import UsageTracker
from web.backend.app.models.api import (
    BudgetResponse,
    BudgetStatusResponse,
    BudgetUpdateRequest,
    LLMDescribeRequest,
    LLMDescribeResponse,
    LLMEnrichRequest,
    LLMEnrichResponse,
    LLMPreviewRequest,
    LLMPreviewResponse,
    LLMStatusResponse,
    LLMSuggestGuardrailsRequest,
    LLMSuggestGuardrailsResponse,
    UsageRecordResponse,
    UsageSummaryResponse,
)

router = APIRouter(prefix="/api/llm", tags=["llm"])

# ---------------------------------------------------------------------------
# Shared singletons
# ---------------------------------------------------------------------------

_client = LLMClient()
_tracker = UsageTracker()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_configured() -> None:
    """Raise 503 if the LLM API key is not set."""
    if not _client.configured:
        raise HTTPException(
            status_code=503,
            detail="LLM not configured. Set the ANTHROPIC_API_KEY environment variable.",
        )


def _require_budget() -> None:
    """Raise 402 if the monthly budget has been exceeded."""
    status = _tracker.check_budget()
    if status.over_limit:
        raise HTTPException(
            status_code=402,
            detail="Monthly budget exceeded. Increase your budget or wait until next month.",
        )


def _track(response: LLMResponse, purpose: str) -> None:
    """Record an LLM call in the usage tracker."""
    _tracker.record_usage(
        model=response.model,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        purpose=purpose,
        cost_estimate=response.cost_estimate,
    )


# ---------------------------------------------------------------------------
# LLM action endpoints
# ---------------------------------------------------------------------------


@router.post("/preview", response_model=LLMPreviewResponse)
async def generate_preview(req: LLMPreviewRequest):
    """Generate a human-friendly preview of a library YAML."""
    _require_configured()
    _require_budget()

    prompt = PREVIEW_PROMPT.format(yaml_content=req.yaml_content, format=req.format)
    resp = _client.complete(prompt)
    _track(resp, "preview")

    return LLMPreviewResponse(
        preview=resp.content,
        tokens_used=resp.total_tokens,
        cost_estimate=resp.cost_estimate,
    )


@router.post("/enrich", response_model=LLMEnrichResponse)
async def enrich_library(req: LLMEnrichRequest):
    """Run LLM enrichment on library YAML."""
    _require_configured()
    _require_budget()

    prompt = LIBRARY_ENRICHMENT_PROMPT.format(yaml_content=req.yaml_content)
    resp = _client.complete(prompt)
    _track(resp, "enrich")

    # Try to extract a changes summary from the response
    changes: list[str] = []
    enriched = resp.content
    # If the model prepended commentary, try to separate it
    if "---" in enriched:
        parts = enriched.split("---", 1)
        if len(parts) == 2 and len(parts[1].strip()) > len(parts[0].strip()):
            enriched = "---" + parts[1]

    return LLMEnrichResponse(
        enriched_yaml=enriched,
        changes_summary=changes,
        tokens_used=resp.total_tokens,
        cost_estimate=resp.cost_estimate,
    )


@router.post("/suggest-guardrails", response_model=LLMSuggestGuardrailsResponse)
async def suggest_guardrails(req: LLMSuggestGuardrailsRequest):
    """Suggest guardrails for a library."""
    _require_configured()
    _require_budget()

    prompt = GUARDRAIL_PROMPT.format(yaml_content=req.yaml_content)
    resp = _client.complete(prompt)
    _track(resp, "suggest-guardrails")

    # Parse JSON array from LLM response
    guardrails: list[dict] = []
    try:
        content = resp.content.strip()
        # Strip markdown fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[: content.rfind("```")]
        guardrails = json.loads(content.strip())
        if not isinstance(guardrails, list):
            guardrails = [guardrails]
    except (json.JSONDecodeError, ValueError):
        guardrails = [{"description": resp.content, "type": "info"}]

    return LLMSuggestGuardrailsResponse(
        guardrails=guardrails,
        tokens_used=resp.total_tokens,
        cost_estimate=resp.cost_estimate,
    )


@router.post("/describe", response_model=LLMDescribeResponse)
async def describe_library(req: LLMDescribeRequest):
    """Generate a better description for a library."""
    _require_configured()
    _require_budget()

    prompt = DESCRIPTION_PROMPT.format(yaml_content=req.yaml_content)
    resp = _client.complete(prompt)
    _track(resp, "describe")

    return LLMDescribeResponse(
        description=resp.content.strip(),
        tokens_used=resp.total_tokens,
        cost_estimate=resp.cost_estimate,
    )


# ---------------------------------------------------------------------------
# Usage endpoints
# ---------------------------------------------------------------------------


@router.get("/usage", response_model=UsageSummaryResponse)
async def get_usage(
    period: Literal["today", "week", "month", "all"] = Query("month"),
):
    """Get usage stats for a period."""
    records = _tracker.get_usage(period=period)
    tokens = _tracker.get_total_tokens(period=period)
    total_cost = _tracker.get_total_cost(period=period)

    return UsageSummaryResponse(
        total_input_tokens=tokens["input_tokens"],
        total_output_tokens=tokens["output_tokens"],
        total_cost=round(total_cost, 6),
        record_count=len(records),
        records=[
            UsageRecordResponse(
                id=r.id,
                model=r.model,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                purpose=r.purpose,
                cost_estimate=r.cost_estimate,
                timestamp=r.timestamp,
            )
            for r in records
        ],
    )


@router.get("/usage/cost")
async def get_usage_cost(
    period: Literal["today", "week", "month", "all"] = Query("month"),
):
    """Get total cost for a period."""
    total_cost = _tracker.get_total_cost(period=period)
    return {"total_cost": round(total_cost, 6)}


# ---------------------------------------------------------------------------
# Budget endpoints
# ---------------------------------------------------------------------------


@router.get("/budget", response_model=BudgetResponse)
async def get_budget():
    """Get current budget settings."""
    budget = _tracker.get_budget()
    if budget is None:
        return BudgetResponse()
    return BudgetResponse(
        monthly_limit=budget.monthly_limit,
        alert_threshold_pct=budget.alert_threshold_pct,
        current_month_cost=budget.current_month_cost,
    )


@router.put("/budget", response_model=BudgetResponse)
async def set_budget(req: BudgetUpdateRequest):
    """Set budget configuration."""
    budget = _tracker.set_budget(
        monthly_limit=req.monthly_limit,
        alert_threshold_pct=req.alert_threshold_pct,
    )
    return BudgetResponse(
        monthly_limit=budget.monthly_limit,
        alert_threshold_pct=budget.alert_threshold_pct,
        current_month_cost=budget.current_month_cost,
    )


@router.get("/budget/status", response_model=BudgetStatusResponse)
async def get_budget_status():
    """Check if budget allows more usage."""
    status = _tracker.check_budget()
    return BudgetStatusResponse(
        allowed=status.allowed,
        remaining=status.remaining,
        percent_used=status.percent_used,
        over_limit=status.over_limit,
        monthly_limit=status.monthly_limit,
    )


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------


@router.get("/status", response_model=LLMStatusResponse)
async def get_status():
    """Check if LLM is configured."""
    if _client.configured:
        return LLMStatusResponse(
            configured=True,
            model=_client.model,
            message="LLM is configured and ready.",
        )
    return LLMStatusResponse(
        configured=False,
        model=_client.model,
        message="LLM not configured. Set ANTHROPIC_API_KEY environment variable.",
    )
