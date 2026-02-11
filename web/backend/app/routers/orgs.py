"""Organizations router -- org CRUD, member management, repository tracking."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ale.auth.models import User
from ale.auth.store import UserStore
from ale.orgs.models import OrgRole, Organization
from ale.orgs.org_store import OrgStore
from web.backend.app.middleware.auth import get_current_user, get_optional_user, get_store
from web.backend.app.models.api import (
    AddMemberRequest,
    AddRepoRequest,
    CreateOrgRequest,
    OrgDashboardResponse,
    OrgMemberResponse,
    OrganizationResponse,
    RepoResponse,
    RoleUpdateRequest,
    UpdateOrgRequest,
)

router = APIRouter(prefix="/api/orgs", tags=["organizations"])

# ---------------------------------------------------------------------------
# Shared store instance
# ---------------------------------------------------------------------------

_org_store: Optional[OrgStore] = None


def _get_org_store() -> OrgStore:
    """Return the singleton OrgStore instance."""
    global _org_store
    if _org_store is None:
        _org_store = OrgStore()
    return _org_store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(name: str) -> str:
    """Create a URL-friendly slug from an organization name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _org_response(org: Organization, store: OrgStore) -> OrganizationResponse:
    """Convert a domain Organization to the Pydantic response model."""
    members = store.list_members(org.id)
    repos = store.list_repos(org.id)
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        owner_id=org.owner_id,
        created_at=org.created_at,
        member_count=len(members),
        repo_count=len(repos),
    )


def _repo_response(repo) -> RepoResponse:
    """Convert a domain Repository to the Pydantic response model."""
    return RepoResponse(
        id=repo.id,
        org_id=repo.org_id,
        name=repo.name,
        url=repo.url,
        default_branch=repo.default_branch,
        added_at=repo.added_at,
        last_scanned=repo.last_scanned,
        scan_status=repo.scan_status.value if hasattr(repo.scan_status, "value") else repo.scan_status,
    )


def _member_response(member, user_store: UserStore) -> OrgMemberResponse:
    """Convert a domain OrgMember to the Pydantic response model."""
    user = user_store.get_user(member.user_id)
    return OrgMemberResponse(
        user_id=member.user_id,
        username=user.username if user else "",
        email=user.email if user else "",
        role=member.role.value if hasattr(member.role, "value") else member.role,
        joined_at=member.joined_at,
    )


def _require_org_admin(org_id: str, user_id: str, store: OrgStore) -> None:
    """Raise 403 if the user is not an admin of the given org."""
    member = store.get_member(org_id, user_id)
    if member is None or member.role != OrgRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin access required",
        )


def _require_org_member(org_id: str, user_id: str, store: OrgStore) -> None:
    """Raise 403 if the user is not a member of the given org."""
    member = store.get_member(org_id, user_id)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization membership required",
        )


def _get_org_or_404(slug: str, store: OrgStore) -> Organization:
    """Look up an org by slug or raise 404."""
    org = store.get_org_by_slug(slug)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{slug}' not found",
        )
    return org


# ---------------------------------------------------------------------------
# Organization CRUD
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=OrganizationResponse,
    summary="Create a new organization",
)
async def create_org(
    body: CreateOrgRequest,
    user: User = Depends(get_current_user),
):
    """Create a new organization. The authenticated user becomes the owner and admin."""
    store = _get_org_store()

    slug = _slugify(body.name)
    if not slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name must produce a valid slug",
        )

    # Check for slug uniqueness
    existing = store.get_org_by_slug(slug)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization with slug '{slug}' already exists",
        )

    org = Organization(
        id=str(uuid.uuid4()),
        name=body.name,
        slug=slug,
        description=body.description,
        owner_id=user.id,
    )
    store.create_org(org)

    # Add the creator as admin member
    store.add_member(org.id, user.id, "admin")

    return _org_response(org, store)


@router.get(
    "",
    response_model=list[OrganizationResponse],
    summary="List user's organizations",
)
async def list_orgs(user: User = Depends(get_current_user)):
    """List all organizations the authenticated user is a member of."""
    store = _get_org_store()
    all_orgs = store.list_orgs()

    # Filter to orgs the user is a member of
    user_orgs = []
    for org in all_orgs:
        member = store.get_member(org.id, user.id)
        if member is not None:
            user_orgs.append(_org_response(org, store))

    return user_orgs


@router.get(
    "/{slug}",
    response_model=OrganizationResponse,
    summary="Get organization by slug",
)
async def get_org(slug: str, user: User = Depends(get_current_user)):
    """Get an organization's details by its slug."""
    store = _get_org_store()
    org = _get_org_or_404(slug, store)
    _require_org_member(org.id, user.id, store)
    return _org_response(org, store)


@router.put(
    "/{slug}",
    response_model=OrganizationResponse,
    summary="Update organization",
)
async def update_org(
    slug: str,
    body: UpdateOrgRequest,
    user: User = Depends(get_current_user),
):
    """Update an organization. Requires admin role."""
    store = _get_org_store()
    org = _get_org_or_404(slug, store)
    _require_org_admin(org.id, user.id, store)

    kwargs = {}
    if body.name:
        kwargs["name"] = body.name
    if body.description:
        kwargs["description"] = body.description

    if kwargs:
        updated = store.update_org(org.id, **kwargs)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update organization",
            )
        org = updated

    return _org_response(org, store)


@router.delete(
    "/{slug}",
    summary="Delete organization (owner only)",
)
async def delete_org(slug: str, user: User = Depends(get_current_user)):
    """Delete an organization. Only the owner can delete it."""
    store = _get_org_store()
    org = _get_org_or_404(slug, store)

    if org.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization owner can delete it",
        )

    deleted = store.delete_org(org.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete organization",
        )

    return {"ok": True}


# ---------------------------------------------------------------------------
# Member management
# ---------------------------------------------------------------------------


@router.get(
    "/{slug}/members",
    response_model=list[OrgMemberResponse],
    summary="List organization members",
)
async def list_members(slug: str, user: User = Depends(get_current_user)):
    """List all members of an organization."""
    store = _get_org_store()
    user_store = get_store()
    org = _get_org_or_404(slug, store)
    _require_org_member(org.id, user.id, store)

    members = store.list_members(org.id)
    return [_member_response(m, user_store) for m in members]


@router.post(
    "/{slug}/members",
    response_model=OrgMemberResponse,
    summary="Add a member to the organization",
)
async def add_member(
    slug: str,
    body: AddMemberRequest,
    user: User = Depends(get_current_user),
):
    """Add a member to the organization. Requires admin role."""
    store = _get_org_store()
    user_store = get_store()
    org = _get_org_or_404(slug, store)
    _require_org_admin(org.id, user.id, store)

    # Verify the target user exists
    target_user = user_store.get_user(body.user_id)
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{body.user_id}' not found",
        )

    member = store.add_member(org.id, body.user_id, body.role)
    return _member_response(member, user_store)


@router.delete(
    "/{slug}/members/{user_id}",
    summary="Remove a member from the organization",
)
async def remove_member(
    slug: str,
    user_id: str,
    user: User = Depends(get_current_user),
):
    """Remove a member from the organization. Requires admin role (or self-remove)."""
    store = _get_org_store()
    org = _get_org_or_404(slug, store)

    # Allow self-removal or admin removal
    if user_id != user.id:
        _require_org_admin(org.id, user.id, store)

    # Prevent removing the owner
    if user_id == org.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the organization owner",
        )

    removed = store.remove_member(org.id, user_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    return {"ok": True}


@router.put(
    "/{slug}/members/{user_id}/role",
    response_model=OrgMemberResponse,
    summary="Update a member's role",
)
async def update_member_role(
    slug: str,
    user_id: str,
    body: RoleUpdateRequest,
    user: User = Depends(get_current_user),
):
    """Update a member's role within the organization. Requires admin role."""
    store = _get_org_store()
    user_store = get_store()
    org = _get_org_or_404(slug, store)
    _require_org_admin(org.id, user.id, store)

    # Validate role
    valid_roles = [r.value for r in OrgRole]
    if body.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {body.role}. Valid roles: {valid_roles}",
        )

    updated = store.update_member_role(org.id, user_id, body.role)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    return _member_response(updated, user_store)


# ---------------------------------------------------------------------------
# Repository management
# ---------------------------------------------------------------------------


@router.post(
    "/{slug}/repos",
    response_model=RepoResponse,
    summary="Add a repository to the organization",
)
async def add_repo(
    slug: str,
    body: AddRepoRequest,
    user: User = Depends(get_current_user),
):
    """Add a repository to the organization. Requires admin or member role."""
    store = _get_org_store()
    org = _get_org_or_404(slug, store)
    _require_org_member(org.id, user.id, store)

    repo = store.add_repo(org.id, body.name, body.url, body.default_branch)
    return _repo_response(repo)


@router.get(
    "/{slug}/repos",
    response_model=list[RepoResponse],
    summary="List organization repositories",
)
async def list_repos(slug: str, user: User = Depends(get_current_user)):
    """List all repositories for an organization."""
    store = _get_org_store()
    org = _get_org_or_404(slug, store)
    _require_org_member(org.id, user.id, store)

    repos = store.list_repos(org.id)
    return [_repo_response(r) for r in repos]


@router.delete(
    "/{slug}/repos/{repo_id}",
    summary="Remove a repository from the organization",
)
async def remove_repo(
    slug: str,
    repo_id: str,
    user: User = Depends(get_current_user),
):
    """Remove a repository. Requires admin role."""
    store = _get_org_store()
    org = _get_org_or_404(slug, store)
    _require_org_admin(org.id, user.id, store)

    # Verify repo belongs to this org
    repo = store.get_repo(repo_id)
    if repo is None or repo.org_id != org.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found in this organization",
        )

    removed = store.remove_repo(repo_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    return {"ok": True}


@router.post(
    "/{slug}/repos/{repo_id}/scan",
    summary="Trigger a repository scan",
)
async def scan_repo(
    slug: str,
    repo_id: str,
    user: User = Depends(get_current_user),
):
    """Trigger a scan on a repository. Sets status to 'scanning'.

    In a real implementation this would kick off an async job.
    For now, we simulate by updating the status to 'scanning' and then to 'complete'.
    """
    store = _get_org_store()
    org = _get_org_or_404(slug, store)
    _require_org_member(org.id, user.id, store)

    # Verify repo belongs to this org
    repo = store.get_repo(repo_id)
    if repo is None or repo.org_id != org.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found in this organization",
        )

    now = datetime.utcnow().isoformat()

    # In a real system, this would enqueue a background task.
    # We simulate by immediately marking it as complete.
    store.update_repo_status(repo_id, "scanning", last_scanned=now)
    updated = store.update_repo_status(repo_id, "complete", last_scanned=now)

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update scan status",
        )

    return _repo_response(updated)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get(
    "/{slug}/dashboard",
    response_model=OrgDashboardResponse,
    summary="Get organization dashboard stats",
)
async def org_dashboard(slug: str, user: User = Depends(get_current_user)):
    """Get aggregated dashboard statistics for the organization."""
    store = _get_org_store()
    org = _get_org_or_404(slug, store)
    _require_org_member(org.id, user.id, store)

    members = store.list_members(org.id)
    repos = store.list_repos(org.id)

    # Recent scans: repos sorted by last_scanned descending, limit 5
    scanned_repos = sorted(
        [r for r in repos if r.last_scanned],
        key=lambda r: r.last_scanned,
        reverse=True,
    )[:5]

    # Count libraries: for now, we use repo count as a proxy.
    # In a full implementation, this would query the registry for libraries
    # belonging to this org.
    total_libraries = len([r for r in repos if r.scan_status.value == "complete"])

    return OrgDashboardResponse(
        org=_org_response(org, store),
        total_libraries=total_libraries,
        total_members=len(members),
        total_repos=len(repos),
        recent_scans=[_repo_response(r) for r in scanned_repos],
    )
