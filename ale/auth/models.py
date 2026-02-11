"""Auth domain models for users, organizations, teams, and sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Role(str, Enum):
    """Role hierarchy: admin > publisher > reviewer > viewer."""

    admin = "admin"
    publisher = "publisher"
    reviewer = "reviewer"
    viewer = "viewer"

    @property
    def level(self) -> int:
        """Return numeric level for comparison (higher = more privileges)."""
        return {
            Role.admin: 40,
            Role.publisher: 30,
            Role.reviewer: 20,
            Role.viewer: 10,
        }[self]


@dataclass
class User:
    """Represents an authenticated user."""

    id: str
    username: str
    email: str
    display_name: str = ""
    avatar_url: str = ""
    provider: str = "github"  # github | gitlab
    provider_id: str = ""
    role: Role = Role.viewer
    org_id: str = ""
    created_at: str = ""
    last_login: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.last_login:
            self.last_login = datetime.utcnow().isoformat()
        if isinstance(self.role, str):
            self.role = Role(self.role)


@dataclass
class Org:
    """Represents an organization."""

    id: str
    name: str
    slug: str
    description: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class Team:
    """Represents a team within an organization."""

    id: str
    name: str
    org_id: str
    members: list[str] = field(default_factory=list)


@dataclass
class Session:
    """Represents an active user session."""

    id: str
    user_id: str
    token: str
    created_at: str = ""
    expires_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class APIKey:
    """Represents an API key for programmatic access."""

    id: str
    user_id: str
    name: str
    key_hash: str
    prefix: str  # First 8 chars for display
    created_at: str = ""
    expires_at: str = ""
    last_used: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
