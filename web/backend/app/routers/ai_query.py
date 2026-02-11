"""AI Query router -- ask GenAI questions about analyzer components.

Provides endpoints for submitting natural-language queries about extraction
candidates, viewing interaction history, and managing content moderation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ale.ai_query.models import AIQueryRecord
from ale.ai_query.store import AIQueryStore
from ale.auth.models import Role, User
from ale.llm.client import LLMClient
from ale.llm.usage_tracker import UsageTracker
from ale.moderation.moderator import ContentModerator
from ale.security.audit_log import AuditLogger
from web.backend.app.middleware.auth import get_current_user
from web.backend.app.models.api import (
    AIQueryHistoryEntry,
    AIQueryRequest,
    AIQueryResponse,
    UserModerationStatusResponse,
)

router = APIRouter(prefix="/api/ai-query", tags=["ai-query"])

# ---------------------------------------------------------------------------
# Shared singletons
# ---------------------------------------------------------------------------

_llm = LLMClient()
_tracker = UsageTracker()
_store = AIQueryStore()
_moderator = ContentModerator()
_audit = AuditLogger()

# ---------------------------------------------------------------------------
# System prompt for candidate Q&A
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are an expert code analyst working inside the ALE (Agentic Library "
    "Extractor) platform. The user is looking at an extraction candidate — a "
    "component discovered during repository analysis. Answer their question "
    "using the provided context about the component. Be specific: cite file "
    "paths, function names, and class names when possible. If you don't have "
    "enough information to answer confidently, say so."
)


def _build_user_prompt(req: AIQueryRequest) -> str:
    """Assemble the user-facing prompt with candidate context."""
    parts = [
        f"## Component: {req.component_name}",
        "",
    ]
    if req.candidate_description:
        parts.append(f"**Description:** {req.candidate_description}")
        parts.append("")
    if req.context_summary:
        parts.append(f"**Context summary:** {req.context_summary}")
        parts.append("")
    if req.candidate_tags:
        parts.append(f"**Tags:** {', '.join(req.candidate_tags)}")
        parts.append("")
    if req.source_files:
        capped = req.source_files[:30]
        parts.append("**Source files:**")
        for sf in capped:
            parts.append(f"- {sf}")
        if len(req.source_files) > 30:
            parts.append(f"- ... and {len(req.source_files) - 30} more")
        parts.append("")
    parts.append(f"**Repository:** {req.repo_url}")
    parts.append(f"**Library:** {req.library_name}")
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(f"**User question:** {req.prompt}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=AIQueryResponse,
    summary="Submit an AI query about an analyzer component",
)
async def submit_query(
    request: AIQueryRequest,
    user: User = Depends(get_current_user),
):
    """Ask a GenAI question about an extraction candidate.

    The prompt is moderated before being sent to the LLM.  A first violation
    returns a 422 warning; a second violation locks the account (423).
    """
    # 1. Content moderation
    mod_result = _moderator.check_prompt(user.id, request.prompt)
    if not mod_result.allowed:
        if mod_result.violation_type == "account_locked":
            _audit.log_event(
                actor=user.username,
                action="ai_query_blocked",
                resource_type="moderation",
                resource_id=user.id,
                details={"reason": "account_locked"},
                success=False,
            )
            raise HTTPException(
                status_code=423,
                detail={
                    "reason": mod_result.reason,
                    "violation_type": mod_result.violation_type,
                    "is_locked": True,
                },
            )
        _audit.log_event(
            actor=user.username,
            action="ai_query_violation",
            resource_type="moderation",
            resource_id=user.id,
            details={
                "violation_type": mod_result.violation_type,
                "reason": mod_result.reason,
            },
            success=False,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "reason": mod_result.reason,
                "violation_type": mod_result.violation_type,
                "is_locked": False,
            },
        )

    # 2. Check LLM configuration
    if not _llm.configured:
        raise HTTPException(
            status_code=503,
            detail="LLM not configured. Set the ANTHROPIC_API_KEY environment variable.",
        )

    # 3. Check budget
    budget_status = _tracker.check_budget()
    if budget_status.over_limit:
        raise HTTPException(
            status_code=402,
            detail="Monthly LLM budget exceeded.",
        )

    # 4. Build prompt and call LLM
    user_prompt = _build_user_prompt(request)
    llm_response = _llm.complete(
        prompt=user_prompt,
        system_prompt=_SYSTEM_PROMPT,
        max_tokens=4096,
        temperature=0.3,
    )

    # 5. Record LLM usage
    _tracker.record_usage(
        model=llm_response.model,
        input_tokens=llm_response.input_tokens,
        output_tokens=llm_response.output_tokens,
        purpose="ai_query",
        cost_estimate=llm_response.cost_estimate,
    )

    # 6. Store interaction
    record = AIQueryRecord(
        id="",
        user_id=user.id,
        username=user.username,
        repo_url=request.repo_url,
        library_name=request.library_name,
        component_name=request.component_name,
        prompt=request.prompt,
        response=llm_response.content,
        input_method=request.input_method,
        model=llm_response.model,
        input_tokens=llm_response.input_tokens,
        output_tokens=llm_response.output_tokens,
        cost_estimate=llm_response.cost_estimate,
    )
    record = _store.record_query(record)

    # 7. Audit log
    _audit.log_event(
        actor=user.username,
        action="ai_query",
        resource_type="candidate",
        resource_id=request.component_name,
        details={
            "library_name": request.library_name,
            "repo_url": request.repo_url,
            "input_method": request.input_method,
            "tokens": llm_response.total_tokens,
            "cost": llm_response.cost_estimate,
        },
    )

    return AIQueryResponse(
        id=record.id,
        response=llm_response.content,
        model=llm_response.model,
        tokens_used=llm_response.total_tokens,
        cost_estimate=llm_response.cost_estimate,
        timestamp=record.timestamp,
    )


@router.get(
    "/history",
    response_model=list[AIQueryHistoryEntry],
    summary="Get Q&A history for a component",
)
async def get_history(
    library_name: str = Query(..., description="Library name"),
    component_name: str = Query(..., description="Component/candidate name"),
    limit: int = Query(50, ge=1, le=200),
):
    """Return past AI query interactions for a specific component."""
    records = _store.get_history(library_name, component_name, limit=limit)
    return [
        AIQueryHistoryEntry(
            id=r.id,
            user_id=r.user_id,
            username=r.username,
            prompt=r.prompt,
            response=r.response,
            input_method=r.input_method,
            timestamp=r.timestamp,
        )
        for r in records
    ]


@router.get(
    "/insights/{library_name}/{component_name}",
    response_model=list[AIQueryHistoryEntry],
    summary="Get top insights for inline display in analyzer",
)
async def get_insights(
    library_name: str,
    component_name: str,
    limit: int = Query(10, ge=1, le=50),
):
    """Return the most recent Q&A pairs for a component, suitable for inline
    display in the analyzer row."""
    records = _store.get_insights(library_name, component_name, limit=limit)
    return [
        AIQueryHistoryEntry(
            id=r.id,
            user_id=r.user_id,
            username=r.username,
            prompt=r.prompt,
            response=r.response,
            input_method=r.input_method,
            timestamp=r.timestamp,
        )
        for r in records
    ]


@router.get(
    "/user-status",
    response_model=UserModerationStatusResponse,
    summary="Get current user moderation status",
)
async def get_user_moderation_status(
    user: User = Depends(get_current_user),
):
    """Return the moderation status (violation count, lock status) for the
    currently authenticated user."""
    status = _moderator.get_user_status(user.id)
    return UserModerationStatusResponse(
        user_id=status.user_id,
        violation_count=status.violation_count,
        is_locked=status.is_locked,
    )


@router.post(
    "/admin/unlock/{user_id}",
    response_model=UserModerationStatusResponse,
    summary="Unlock a user account (admin only)",
)
async def admin_unlock_user(
    user_id: str,
    user: User = Depends(get_current_user),
):
    """Allow an admin to unlock a user account that was locked due to
    moderation violations."""
    if user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Admin access required.")

    status = _moderator.unlock_user(user_id)
    _audit.log_event(
        actor=user.username,
        action="moderation_unlock",
        resource_type="user",
        resource_id=user_id,
    )
    return UserModerationStatusResponse(
        user_id=status.user_id,
        violation_count=status.violation_count,
        is_locked=status.is_locked,
    )
