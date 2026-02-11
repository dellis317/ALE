"""Auth router -- login, logout, user management, and API key endpoints."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ale.auth.models import Role, User
from ale.auth.oauth import (
    exchange_github_code,
    exchange_gitlab_code,
    get_github_auth_url,
    get_gitlab_auth_url,
    is_demo_mode,
)
from ale.auth.permissions import has_permission
from ale.auth.store import UserStore
from web.backend.app.middleware.auth import get_current_user, get_store
from web.backend.app.models.api import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyResponse,
    AuthStatusResponse,
    LoginResponse,
    RoleUpdateRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_response(u: User) -> UserResponse:
    """Convert a domain User to a Pydantic UserResponse."""
    return UserResponse(
        id=u.id,
        username=u.username,
        email=u.email,
        display_name=u.display_name,
        avatar_url=u.avatar_url,
        provider=u.provider,
        role=u.role.value if isinstance(u.role, Role) else u.role,
        org_id=u.org_id,
        created_at=u.created_at,
        last_login=u.last_login,
    )


def _find_or_create_user(store: UserStore, info: dict) -> User:
    """Look up an existing user by provider+id, or create a new one."""
    user = store.get_user_by_provider(info["provider"], info["provider_id"])
    if user is not None:
        return user

    # Check by email as fallback
    user = store.get_user_by_email(info["email"])
    if user is not None:
        return user

    # Determine role -- first user gets admin
    existing_users = store.list_users()
    role = Role.admin if len(existing_users) == 0 else Role.viewer

    new_user = User(
        id=str(uuid.uuid4()),
        username=info["username"],
        email=info["email"],
        display_name=info.get("display_name", info["username"]),
        avatar_url=info.get("avatar_url", ""),
        provider=info["provider"],
        provider_id=info["provider_id"],
        role=role,
    )
    return store.create_user(new_user)


# ---------------------------------------------------------------------------
# Login endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/login/github",
    response_model=LoginResponse,
    summary="Login via GitHub OAuth (or demo mode)",
)
async def login_github(
    code: Optional[str] = None,
    state: Optional[str] = None,
):
    """Initiate GitHub OAuth login.

    **Demo mode** (no ``GITHUB_CLIENT_ID`` env var):
    Returns a session token directly for a demo admin user -- no redirect needed.

    **Production mode**: If ``code`` is not provided, returns the GitHub OAuth
    URL in ``token`` field for the client to redirect to. If ``code`` is
    provided, exchanges it for user info and creates a session.
    """
    store = get_store()

    if is_demo_mode():
        # Demo: create / retrieve demo user and return session immediately
        from ale.auth.oauth import _demo_user_info

        info = _demo_user_info()
        user = _find_or_create_user(store, info)
        session = store.create_session(user.id)
        return LoginResponse(token=session.token, user=_user_response(user))

    if not code:
        # Redirect URL
        auth_url = get_github_auth_url(state=state or "")
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": auth_url},
        )

    # Exchange code
    info = await exchange_github_code(code)
    user = _find_or_create_user(store, info)
    session = store.create_session(user.id)
    return LoginResponse(token=session.token, user=_user_response(user))


@router.get(
    "/callback/github",
    response_model=LoginResponse,
    summary="Handle GitHub OAuth callback",
)
async def callback_github(code: str, state: Optional[str] = None):
    """Handle the GitHub OAuth callback with the authorization code."""
    store = get_store()
    info = await exchange_github_code(code)
    user = _find_or_create_user(store, info)
    session = store.create_session(user.id)
    return LoginResponse(token=session.token, user=_user_response(user))


@router.get(
    "/login/gitlab",
    response_model=LoginResponse,
    summary="Login via GitLab OAuth",
)
async def login_gitlab(
    code: Optional[str] = None,
    state: Optional[str] = None,
):
    """Initiate GitLab OAuth login (same pattern as GitHub)."""
    store = get_store()

    if is_demo_mode():
        from ale.auth.oauth import _demo_user_info

        info = _demo_user_info()
        user = _find_or_create_user(store, info)
        session = store.create_session(user.id)
        return LoginResponse(token=session.token, user=_user_response(user))

    if not code:
        auth_url = get_gitlab_auth_url(state=state or "")
        if not auth_url:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="GitLab OAuth is not configured",
            )
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": auth_url},
        )

    info = await exchange_gitlab_code(code)
    user = _find_or_create_user(store, info)
    session = store.create_session(user.id)
    return LoginResponse(token=session.token, user=_user_response(user))


@router.get(
    "/callback/gitlab",
    response_model=LoginResponse,
    summary="Handle GitLab OAuth callback",
)
async def callback_gitlab(code: str, state: Optional[str] = None):
    """Handle the GitLab OAuth callback."""
    store = get_store()
    info = await exchange_gitlab_code(code)
    user = _find_or_create_user(store, info)
    session = store.create_session(user.id)
    return LoginResponse(token=session.token, user=_user_response(user))


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


@router.post("/logout", summary="Logout / invalidate session")
async def logout(user: User = Depends(get_current_user)):
    """Invalidate the current session."""
    # We need the raw token to delete; re-extract from header
    # Since we already validated, just delete all sessions for user
    store = get_store()
    sessions = store._read_json(store._sessions_path)
    user_sessions = [s for s in sessions if s["user_id"] == user.id]
    for s in user_sessions:
        store.delete_session(s["token"])
    return {"ok": True}


@router.get(
    "/me",
    response_model=AuthStatusResponse,
    summary="Get current user info",
)
async def me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return AuthStatusResponse(
        authenticated=True,
        user=_user_response(user),
    )


# ---------------------------------------------------------------------------
# User management (admin only)
# ---------------------------------------------------------------------------


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List all users (admin only)",
)
async def list_users(user: User = Depends(get_current_user)):
    """List all users. Requires admin role."""
    if not has_permission(user, Role.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    store = get_store()
    return [_user_response(u) for u in store.list_users()]


@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Update user role (admin only)",
)
async def update_user_role(
    user_id: str,
    body: RoleUpdateRequest,
    user: User = Depends(get_current_user),
):
    """Update another user's role. Requires admin role."""
    if not has_permission(user, Role.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        new_role = Role(body.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {body.role}. Valid roles: {[r.value for r in Role]}",
        )

    store = get_store()
    updated = store.update_user_role(user_id, new_role)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )
    return _user_response(updated)


# ---------------------------------------------------------------------------
# API key management
# ---------------------------------------------------------------------------


@router.post(
    "/api-keys",
    response_model=APIKeyCreateResponse,
    summary="Create a new API key",
)
async def create_api_key(
    body: APIKeyCreateRequest,
    user: User = Depends(get_current_user),
):
    """Create a new API key for the authenticated user."""
    store = get_store()
    api_key, raw_key = store.create_api_key(
        user_id=user.id,
        name=body.name,
        expires_in_days=body.expires_in_days,
    )
    return APIKeyCreateResponse(
        key=APIKeyResponse(
            id=api_key.id,
            name=api_key.name,
            prefix=api_key.prefix,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            last_used=api_key.last_used,
        ),
        raw_key=raw_key,
    )


@router.get(
    "/api-keys",
    response_model=list[APIKeyResponse],
    summary="List your API keys",
)
async def list_api_keys(user: User = Depends(get_current_user)):
    """List all API keys for the authenticated user."""
    store = get_store()
    keys = store.list_api_keys(user.id)
    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            prefix=k.prefix,
            created_at=k.created_at,
            expires_at=k.expires_at,
            last_used=k.last_used,
        )
        for k in keys
    ]


@router.delete(
    "/api-keys/{key_id}",
    summary="Revoke an API key",
)
async def delete_api_key(key_id: str, user: User = Depends(get_current_user)):
    """Delete / revoke an API key."""
    store = get_store()

    # Verify the key belongs to this user
    user_keys = store.list_api_keys(user.id)
    if not any(k.id == key_id for k in user_keys):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    deleted = store.delete_api_key(key_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    return {"ok": True}
