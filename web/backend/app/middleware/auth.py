"""Auth middleware -- FastAPI dependencies for extracting the current user.

Supports two authentication methods:
1. ``Authorization: Bearer <session_token>`` header (browser sessions)
2. ``X-API-Key: <raw_key>`` header (programmatic access)
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from ale.auth.models import User
from ale.auth.store import UserStore

# Shared store instance
_store: Optional[UserStore] = None


def get_store() -> UserStore:
    """Return the singleton UserStore instance."""
    global _store
    if _store is None:
        _store = UserStore()
    return _store


async def get_current_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> User:
    """FastAPI dependency that extracts and validates the current user.

    Checks (in order):
    1. ``Authorization: Bearer <token>`` -- session token
    2. ``X-API-Key: <key>`` -- API key

    Raises ``401 Unauthorized`` if no valid credentials are provided.
    """
    store = get_store()

    # 1. Try Bearer token
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            user = store.validate_session(token)
            if user is not None:
                return user

    # 2. Try API key
    if x_api_key:
        user = store.validate_api_key(x_api_key)
        if user is not None:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[User]:
    """Same as ``get_current_user`` but returns ``None`` instead of raising 401.

    Use this for endpoints that work for both anonymous and authenticated users.
    """
    try:
        return await get_current_user(authorization=authorization, x_api_key=x_api_key)
    except HTTPException:
        return None
