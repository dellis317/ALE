"""OAuth helpers for GitHub and GitLab authentication.

When the corresponding environment variables are not set, the helpers
fall back to a **demo mode** that creates a local test user without
hitting any external OAuth provider.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
GITLAB_CLIENT_ID = os.environ.get("GITLAB_CLIENT_ID", "")
GITLAB_CLIENT_SECRET = os.environ.get("GITLAB_CLIENT_SECRET", "")


def is_demo_mode() -> bool:
    """Return True when OAuth credentials are not configured."""
    return not (GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET)


# ---------------------------------------------------------------------------
# GitHub OAuth
# ---------------------------------------------------------------------------

def get_github_auth_url(state: str, redirect_uri: str = "") -> str:
    """Return the GitHub OAuth authorization URL.

    In demo mode, returns an empty string (caller should use demo flow).
    """
    if is_demo_mode():
        return ""
    params = (
        f"client_id={GITHUB_CLIENT_ID}"
        f"&state={state}"
        f"&scope=read:user user:email"
    )
    if redirect_uri:
        params += f"&redirect_uri={redirect_uri}"
    return f"https://github.com/login/oauth/authorize?{params}"


async def exchange_github_code(code: str) -> dict:
    """Exchange a GitHub OAuth code for user information.

    Returns a dict with keys: ``id``, ``username``, ``email``,
    ``display_name``, ``avatar_url``, ``provider``, ``provider_id``.

    In demo mode, returns a synthetic demo user.
    """
    if is_demo_mode():
        return _demo_user_info()

    if httpx is None:
        raise RuntimeError("httpx is required for OAuth. Install it with: pip install httpx")

    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token", "")

        if not access_token:
            raise ValueError(f"GitHub OAuth error: {token_data}")

        # Fetch user profile
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_data = user_resp.json()

        # Fetch primary email
        email = user_data.get("email", "")
        if not email:
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            for em in emails_resp.json():
                if em.get("primary"):
                    email = em.get("email", "")
                    break

        return {
            "username": user_data.get("login", ""),
            "email": email,
            "display_name": user_data.get("name", "") or user_data.get("login", ""),
            "avatar_url": user_data.get("avatar_url", ""),
            "provider": "github",
            "provider_id": str(user_data.get("id", "")),
        }


# ---------------------------------------------------------------------------
# GitLab OAuth
# ---------------------------------------------------------------------------

def get_gitlab_auth_url(state: str, redirect_uri: str = "") -> str:
    """Return the GitLab OAuth authorization URL.

    In demo mode (no credentials), returns an empty string.
    """
    if not (GITLAB_CLIENT_ID and GITLAB_CLIENT_SECRET):
        return ""
    params = (
        f"client_id={GITLAB_CLIENT_ID}"
        f"&state={state}"
        f"&response_type=code"
        f"&scope=read_user"
    )
    if redirect_uri:
        params += f"&redirect_uri={redirect_uri}"
    return f"https://gitlab.com/oauth/authorize?{params}"


async def exchange_gitlab_code(code: str) -> dict:
    """Exchange a GitLab OAuth code for user information.

    Returns a dict with the same shape as ``exchange_github_code``.

    In demo mode, returns a synthetic demo user.
    """
    if not (GITLAB_CLIENT_ID and GITLAB_CLIENT_SECRET):
        return _demo_user_info()

    if httpx is None:
        raise RuntimeError("httpx is required for OAuth. Install it with: pip install httpx")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://gitlab.com/oauth/token",
            data={
                "client_id": GITLAB_CLIENT_ID,
                "client_secret": GITLAB_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token", "")

        if not access_token:
            raise ValueError(f"GitLab OAuth error: {token_data}")

        user_resp = await client.get(
            "https://gitlab.com/api/v4/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_data = user_resp.json()

        return {
            "username": user_data.get("username", ""),
            "email": user_data.get("email", ""),
            "display_name": user_data.get("name", "") or user_data.get("username", ""),
            "avatar_url": user_data.get("avatar_url", ""),
            "provider": "gitlab",
            "provider_id": str(user_data.get("id", "")),
        }


# ---------------------------------------------------------------------------
# Demo mode helper
# ---------------------------------------------------------------------------

_DEMO_USER_ID: Optional[str] = None


def _demo_user_info() -> dict:
    """Return deterministic demo user info for local development."""
    global _DEMO_USER_ID
    if _DEMO_USER_ID is None:
        _DEMO_USER_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "ale-demo-user"))
    return {
        "username": "demo-admin",
        "email": "admin@ale-demo.local",
        "display_name": "Demo Admin",
        "avatar_url": "",
        "provider": "github",
        "provider_id": _DEMO_USER_ID,
    }
