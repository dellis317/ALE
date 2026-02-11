"""Organization domain models for multi-repo management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrgRole(str, Enum):
    """Role within an organization."""

    admin = "admin"
    member = "member"
    viewer = "viewer"


class ScanStatus(str, Enum):
    """Repository scan status."""

    pending = "pending"
    scanning = "scanning"
    complete = "complete"
    error = "error"


@dataclass
class Organization:
    """Represents an organization that groups repos and members."""

    id: str
    name: str
    slug: str
    description: str = ""
    owner_id: str = ""
    created_at: str = ""
    settings: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class OrgMember:
    """Represents a member of an organization."""

    org_id: str
    user_id: str
    role: OrgRole = OrgRole.member
    joined_at: str = ""

    def __post_init__(self) -> None:
        if not self.joined_at:
            self.joined_at = datetime.utcnow().isoformat()
        if isinstance(self.role, str):
            self.role = OrgRole(self.role)


@dataclass
class Repository:
    """Represents a repository linked to an organization."""

    id: str
    org_id: str
    name: str
    url: str
    default_branch: str = "main"
    added_at: str = ""
    last_scanned: str = ""
    scan_status: ScanStatus = ScanStatus.pending

    def __post_init__(self) -> None:
        if not self.added_at:
            self.added_at = datetime.utcnow().isoformat()
        if isinstance(self.scan_status, str):
            self.scan_status = ScanStatus(self.scan_status)


@dataclass
class OrgSettings:
    """Configurable settings for an organization."""

    max_members: int = 50
    allow_public_libraries: bool = True
    require_conformance: bool = False
    auto_scan_interval_hours: int = 24
