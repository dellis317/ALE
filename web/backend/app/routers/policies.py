"""Policies & Approvals router -- policy CRUD, evaluation, and approval workflows."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status

from ale.policies.approval_store import ApprovalStore
from ale.policies.policy_store import PolicyStore
from web.backend.app.models.api import (
    ApprovalDecisionRequest,
    ApprovalRequestResponse,
    CreateApprovalRequest,
    CreatePolicyRequest,
    EvaluatePolicyRequest,
    PolicyEvaluationResponse,
    PolicyResponse,
    TogglePolicyRequest,
    UpdatePolicyRequest,
)

router = APIRouter(prefix="/api", tags=["policies"])


# ---------------------------------------------------------------------------
# Store singletons
# ---------------------------------------------------------------------------

_policy_store: PolicyStore | None = None
_approval_store: ApprovalStore | None = None


def _get_policy_store() -> PolicyStore:
    global _policy_store
    if _policy_store is None:
        _policy_store = PolicyStore()
    return _policy_store


def _get_approval_store() -> ApprovalStore:
    global _approval_store
    if _approval_store is None:
        _approval_store = ApprovalStore()
    return _approval_store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _policy_response(p: dict) -> PolicyResponse:
    """Convert a policy dict to a PolicyResponse."""
    return PolicyResponse(
        id=p["id"],
        name=p["name"],
        description=p.get("description", ""),
        version=p.get("version", "1.0.0"),
        rules=p.get("rules", []),
        created_at=p.get("created_at", ""),
        updated_at=p.get("updated_at", ""),
        enabled=p.get("enabled", True),
    )


def _approval_response(r: dict) -> ApprovalRequestResponse:
    """Convert an approval request dict to an ApprovalRequestResponse."""
    return ApprovalRequestResponse(
        id=r["id"],
        library_name=r["library_name"],
        library_version=r["library_version"],
        requester_id=r["requester_id"],
        policy_id=r["policy_id"],
        reason=r.get("reason", ""),
        status=r.get("status", "pending"),
        created_at=r.get("created_at", ""),
        decided_at=r.get("decided_at", ""),
        decided_by=r.get("decided_by", ""),
        decision_comment=r.get("decision_comment", ""),
    )


# ---------------------------------------------------------------------------
# Policy endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/policies",
    response_model=PolicyResponse,
    summary="Create a new policy",
    status_code=status.HTTP_201_CREATED,
)
async def create_policy(body: CreatePolicyRequest):
    """Create a new policy with the given name, description, and rules."""
    store = _get_policy_store()
    # Convert rule models to dicts for storage
    rules = [r.model_dump() for r in body.rules] if body.rules else []
    policy = store.create_policy(
        name=body.name,
        description=body.description,
        rules=rules,
    )
    return _policy_response(policy)


@router.get(
    "/policies",
    response_model=list[PolicyResponse],
    summary="List all policies",
)
async def list_policies():
    """Return all configured policies."""
    store = _get_policy_store()
    return [_policy_response(p) for p in store.list_policies()]


@router.get(
    "/policies/{policy_id}",
    response_model=PolicyResponse,
    summary="Get a specific policy",
)
async def get_policy(policy_id: str):
    """Return a single policy by ID."""
    store = _get_policy_store()
    policy = store.get_policy(policy_id)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found",
        )
    return _policy_response(policy)


@router.put(
    "/policies/{policy_id}",
    response_model=PolicyResponse,
    summary="Update a policy",
)
async def update_policy(policy_id: str, body: UpdatePolicyRequest):
    """Update an existing policy's name, description, or rules."""
    store = _get_policy_store()
    kwargs: dict = {}
    if body.name:
        kwargs["name"] = body.name
    if body.description:
        kwargs["description"] = body.description
    if body.rules is not None:
        kwargs["rules"] = [r.model_dump() for r in body.rules]

    updated = store.update_policy(policy_id, **kwargs)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found",
        )
    return _policy_response(updated)


@router.delete(
    "/policies/{policy_id}",
    summary="Delete a policy",
)
async def delete_policy(policy_id: str):
    """Delete a policy by ID."""
    store = _get_policy_store()
    deleted = store.delete_policy(policy_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found",
        )
    return {"ok": True}


@router.put(
    "/policies/{policy_id}/toggle",
    response_model=PolicyResponse,
    summary="Enable or disable a policy",
)
async def toggle_policy(policy_id: str, body: TogglePolicyRequest):
    """Toggle a policy's enabled state."""
    store = _get_policy_store()
    updated = store.toggle_policy(policy_id, body.enabled)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found",
        )
    return _policy_response(updated)


@router.post(
    "/policies/evaluate",
    response_model=PolicyEvaluationResponse,
    summary="Evaluate policies for a library application",
)
async def evaluate_policies(body: EvaluatePolicyRequest):
    """Evaluate all enabled policies against the given context."""
    store = _get_policy_store()
    result = store.evaluate_policies(
        library_name=body.library_name,
        library_version=body.library_version,
        target_files=body.target_files,
        capabilities=body.capabilities_used,
    )
    return PolicyEvaluationResponse(**result)


@router.post(
    "/policies/test",
    response_model=PolicyEvaluationResponse,
    summary="Test policies against mock context (dry run)",
)
async def test_policies(body: EvaluatePolicyRequest):
    """Dry-run evaluation of policies -- same as evaluate but semantically a test."""
    store = _get_policy_store()
    result = store.evaluate_policies(
        library_name=body.library_name,
        library_version=body.library_version,
        target_files=body.target_files,
        capabilities=body.capabilities_used,
    )
    return PolicyEvaluationResponse(**result)


# ---------------------------------------------------------------------------
# Approval endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/approvals/pending/count",
    summary="Get count of pending approvals",
)
async def get_pending_count():
    """Return the number of pending approval requests."""
    store = _get_approval_store()
    return {"count": store.get_pending_count()}


@router.post(
    "/approvals",
    response_model=ApprovalRequestResponse,
    summary="Create an approval request",
    status_code=status.HTTP_201_CREATED,
)
async def create_approval(body: CreateApprovalRequest):
    """Create a new approval request for a library application."""
    store = _get_approval_store()
    req = store.create_request(
        library_name=body.library_name,
        library_version=body.library_version,
        requester_id="current-user",  # Would come from auth in production
        policy_id=body.policy_id,
        reason=body.reason,
    )
    return _approval_response(req)


@router.get(
    "/approvals",
    response_model=list[ApprovalRequestResponse],
    summary="List approval requests",
)
async def list_approvals(status_filter: Optional[str] = None):
    """Return all approval requests, optionally filtered by status."""
    store = _get_approval_store()
    return [_approval_response(r) for r in store.list_requests(status=status_filter)]


@router.get(
    "/approvals/{request_id}",
    response_model=ApprovalRequestResponse,
    summary="Get an approval request",
)
async def get_approval(request_id: str):
    """Return a single approval request by ID."""
    store = _get_approval_store()
    req = store.get_request(request_id)
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{request_id}' not found",
        )
    return _approval_response(req)


@router.post(
    "/approvals/{request_id}/approve",
    response_model=ApprovalRequestResponse,
    summary="Approve an approval request",
)
async def approve_request(request_id: str, body: ApprovalDecisionRequest):
    """Approve a pending approval request."""
    store = _get_approval_store()
    req = store.approve(
        request_id=request_id,
        approver_id="current-user",  # Would come from auth in production
        comment=body.comment,
    )
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{request_id}' not found",
        )
    return _approval_response(req)


@router.post(
    "/approvals/{request_id}/reject",
    response_model=ApprovalRequestResponse,
    summary="Reject an approval request",
)
async def reject_request(request_id: str, body: ApprovalDecisionRequest):
    """Reject a pending approval request."""
    store = _get_approval_store()
    req = store.reject(
        request_id=request_id,
        approver_id="current-user",  # Would come from auth in production
        comment=body.comment,
    )
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{request_id}' not found",
        )
    return _approval_response(req)
