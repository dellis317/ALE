"""Role-based access control (RBAC) logic.

Role hierarchy: admin > publisher > reviewer > viewer
"""

from __future__ import annotations

from typing import Callable

from fastapi import HTTPException, status

from ale.auth.models import Role, User


def has_permission(user: User, required_role: Role) -> bool:
    """Check if a user's role meets or exceeds the required role level.

    Parameters
    ----------
    user:
        The authenticated user to check.
    required_role:
        The minimum role required.

    Returns
    -------
    bool
        True if user's role level >= required role level.
    """
    user_role = user.role if isinstance(user.role, Role) else Role(user.role)
    return user_role.level >= required_role.level


def require_role(user: User, role: Role) -> None:
    """Validate that a user has at least the given role.

    Raises ``HTTPException(403)`` if the user lacks the required role.

    Usage in a router::

        @router.get("/admin-only")
        async def admin_only(user: User = Depends(get_current_user)):
            require_role(user, Role.admin)
            ...
    """
    if not has_permission(user, role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires role '{role.value}' or higher",
        )
