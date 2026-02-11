"""File-based JSON storage for organization data.

Provides a DB-ready interface backed by simple JSON files under ~/.ale/orgs/.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from ale.orgs.models import OrgMember, OrgRole, Organization, Repository, ScanStatus


class OrgStore:
    """File-based storage for organizations, members, and repositories.

    Storage path: ``~/.ale/orgs/`` with:
    - ``organizations.json`` -- list of organization dicts
    - ``members.json`` -- list of org member dicts
    - ``repositories.json`` -- list of repository dicts
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        if base_dir is None:
            self._base = Path.home() / ".ale" / "orgs"
        else:
            self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._orgs_path = self._base / "organizations.json"
        self._members_path = self._base / "members.json"
        self._repos_path = self._base / "repositories.json"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_json(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _write_json(self, path: Path, data: list[dict]) -> None:
        path.write_text(json.dumps(data, indent=2, default=str))

    @staticmethod
    def _org_from_dict(d: dict) -> Organization:
        return Organization(
            id=d["id"],
            name=d["name"],
            slug=d["slug"],
            description=d.get("description", ""),
            owner_id=d.get("owner_id", ""),
            created_at=d.get("created_at", ""),
            settings=d.get("settings", {}),
        )

    @staticmethod
    def _org_to_dict(o: Organization) -> dict:
        return {
            "id": o.id,
            "name": o.name,
            "slug": o.slug,
            "description": o.description,
            "owner_id": o.owner_id,
            "created_at": o.created_at,
            "settings": o.settings,
        }

    @staticmethod
    def _member_from_dict(d: dict) -> OrgMember:
        role_val = d.get("role", "member")
        if isinstance(role_val, str):
            try:
                role_val = OrgRole(role_val)
            except ValueError:
                role_val = OrgRole.member
        return OrgMember(
            org_id=d["org_id"],
            user_id=d["user_id"],
            role=role_val,
            joined_at=d.get("joined_at", ""),
        )

    @staticmethod
    def _member_to_dict(m: OrgMember) -> dict:
        return {
            "org_id": m.org_id,
            "user_id": m.user_id,
            "role": m.role.value if isinstance(m.role, OrgRole) else m.role,
            "joined_at": m.joined_at,
        }

    @staticmethod
    def _repo_from_dict(d: dict) -> Repository:
        status_val = d.get("scan_status", "pending")
        if isinstance(status_val, str):
            try:
                status_val = ScanStatus(status_val)
            except ValueError:
                status_val = ScanStatus.pending
        return Repository(
            id=d["id"],
            org_id=d["org_id"],
            name=d["name"],
            url=d["url"],
            default_branch=d.get("default_branch", "main"),
            added_at=d.get("added_at", ""),
            last_scanned=d.get("last_scanned", ""),
            scan_status=status_val,
        )

    @staticmethod
    def _repo_to_dict(r: Repository) -> dict:
        return {
            "id": r.id,
            "org_id": r.org_id,
            "name": r.name,
            "url": r.url,
            "default_branch": r.default_branch,
            "added_at": r.added_at,
            "last_scanned": r.last_scanned,
            "scan_status": r.scan_status.value if isinstance(r.scan_status, ScanStatus) else r.scan_status,
        }

    # ------------------------------------------------------------------
    # Organization CRUD
    # ------------------------------------------------------------------

    def create_org(self, org: Organization) -> Organization:
        """Persist a new organization. Returns the organization."""
        orgs = self._read_json(self._orgs_path)
        orgs.append(self._org_to_dict(org))
        self._write_json(self._orgs_path, orgs)
        return org

    def get_org(self, org_id: str) -> Optional[Organization]:
        """Get an organization by ID."""
        for d in self._read_json(self._orgs_path):
            if d["id"] == org_id:
                return self._org_from_dict(d)
        return None

    def get_org_by_slug(self, slug: str) -> Optional[Organization]:
        """Get an organization by slug."""
        for d in self._read_json(self._orgs_path):
            if d["slug"] == slug:
                return self._org_from_dict(d)
        return None

    def list_orgs(self) -> list[Organization]:
        """List all organizations."""
        return [self._org_from_dict(d) for d in self._read_json(self._orgs_path)]

    def update_org(self, org_id: str, **kwargs: str) -> Optional[Organization]:
        """Update an organization's fields. Returns the updated org or None."""
        orgs = self._read_json(self._orgs_path)
        for d in orgs:
            if d["id"] == org_id:
                for key, value in kwargs.items():
                    if key in d and value:
                        d[key] = value
                self._write_json(self._orgs_path, orgs)
                return self._org_from_dict(d)
        return None

    def delete_org(self, org_id: str) -> bool:
        """Delete an organization and all its members and repos."""
        orgs = self._read_json(self._orgs_path)
        original_len = len(orgs)
        orgs = [d for d in orgs if d["id"] != org_id]
        if len(orgs) < original_len:
            self._write_json(self._orgs_path, orgs)
            # Clean up members
            members = self._read_json(self._members_path)
            members = [m for m in members if m["org_id"] != org_id]
            self._write_json(self._members_path, members)
            # Clean up repos
            repos = self._read_json(self._repos_path)
            repos = [r for r in repos if r["org_id"] != org_id]
            self._write_json(self._repos_path, repos)
            return True
        return False

    # ------------------------------------------------------------------
    # Member management
    # ------------------------------------------------------------------

    def add_member(self, org_id: str, user_id: str, role: str = "member") -> OrgMember:
        """Add a member to an organization."""
        try:
            role_enum = OrgRole(role)
        except ValueError:
            role_enum = OrgRole.member

        member = OrgMember(
            org_id=org_id,
            user_id=user_id,
            role=role_enum,
        )
        members = self._read_json(self._members_path)
        # Remove existing membership for this user in this org (upsert)
        members = [m for m in members if not (m["org_id"] == org_id and m["user_id"] == user_id)]
        members.append(self._member_to_dict(member))
        self._write_json(self._members_path, members)
        return member

    def remove_member(self, org_id: str, user_id: str) -> bool:
        """Remove a member from an organization."""
        members = self._read_json(self._members_path)
        original_len = len(members)
        members = [m for m in members if not (m["org_id"] == org_id and m["user_id"] == user_id)]
        if len(members) < original_len:
            self._write_json(self._members_path, members)
            return True
        return False

    def list_members(self, org_id: str) -> list[OrgMember]:
        """List all members of an organization."""
        return [
            self._member_from_dict(d)
            for d in self._read_json(self._members_path)
            if d["org_id"] == org_id
        ]

    def get_member(self, org_id: str, user_id: str) -> Optional[OrgMember]:
        """Get a specific member of an organization."""
        for d in self._read_json(self._members_path):
            if d["org_id"] == org_id and d["user_id"] == user_id:
                return self._member_from_dict(d)
        return None

    def update_member_role(self, org_id: str, user_id: str, role: str) -> Optional[OrgMember]:
        """Update a member's role within an organization."""
        members = self._read_json(self._members_path)
        for d in members:
            if d["org_id"] == org_id and d["user_id"] == user_id:
                try:
                    role_enum = OrgRole(role)
                except ValueError:
                    role_enum = OrgRole.member
                d["role"] = role_enum.value
                self._write_json(self._members_path, members)
                return self._member_from_dict(d)
        return None

    # ------------------------------------------------------------------
    # Repository management
    # ------------------------------------------------------------------

    def add_repo(self, org_id: str, name: str, url: str, default_branch: str = "main") -> Repository:
        """Add a repository to an organization."""
        repo = Repository(
            id=str(uuid.uuid4()),
            org_id=org_id,
            name=name,
            url=url,
            default_branch=default_branch,
        )
        repos = self._read_json(self._repos_path)
        repos.append(self._repo_to_dict(repo))
        self._write_json(self._repos_path, repos)
        return repo

    def list_repos(self, org_id: str) -> list[Repository]:
        """List all repositories for an organization."""
        return [
            self._repo_from_dict(d)
            for d in self._read_json(self._repos_path)
            if d["org_id"] == org_id
        ]

    def get_repo(self, repo_id: str) -> Optional[Repository]:
        """Get a repository by ID."""
        for d in self._read_json(self._repos_path):
            if d["id"] == repo_id:
                return self._repo_from_dict(d)
        return None

    def remove_repo(self, repo_id: str) -> bool:
        """Remove a repository."""
        repos = self._read_json(self._repos_path)
        original_len = len(repos)
        repos = [d for d in repos if d["id"] != repo_id]
        if len(repos) < original_len:
            self._write_json(self._repos_path, repos)
            return True
        return False

    def update_repo_status(
        self,
        repo_id: str,
        status: str,
        last_scanned: Optional[str] = None,
    ) -> Optional[Repository]:
        """Update a repository's scan status and last_scanned timestamp."""
        repos = self._read_json(self._repos_path)
        for d in repos:
            if d["id"] == repo_id:
                try:
                    status_enum = ScanStatus(status)
                except ValueError:
                    status_enum = ScanStatus.pending
                d["scan_status"] = status_enum.value
                if last_scanned:
                    d["last_scanned"] = last_scanned
                self._write_json(self._repos_path, repos)
                return self._repo_from_dict(d)
        return None
