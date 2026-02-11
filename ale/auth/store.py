"""File-based JSON storage for auth data.

Provides a DB-ready interface backed by simple JSON files under ~/.ale/auth/.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ale.auth.models import APIKey, Role, Session, User


class UserStore:
    """File-based storage for users, sessions, and API keys.

    Storage path: ``~/.ale/auth/`` with:
    - ``users.json`` -- list of user dicts
    - ``api_keys.json`` -- list of API key dicts
    - ``sessions.json`` -- list of session dicts
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        if base_dir is None:
            self._base = Path.home() / ".ale" / "auth"
        else:
            self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)
        self._users_path = self._base / "users.json"
        self._keys_path = self._base / "api_keys.json"
        self._sessions_path = self._base / "sessions.json"

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
    def _hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()

    @staticmethod
    def _user_from_dict(d: dict) -> User:
        role_val = d.get("role", "viewer")
        if isinstance(role_val, str):
            try:
                role_val = Role(role_val)
            except ValueError:
                role_val = Role.viewer
        return User(
            id=d["id"],
            username=d["username"],
            email=d["email"],
            display_name=d.get("display_name", ""),
            avatar_url=d.get("avatar_url", ""),
            provider=d.get("provider", "github"),
            provider_id=d.get("provider_id", ""),
            role=role_val,
            org_id=d.get("org_id", ""),
            created_at=d.get("created_at", ""),
            last_login=d.get("last_login", ""),
        )

    @staticmethod
    def _user_to_dict(u: User) -> dict:
        return {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "display_name": u.display_name,
            "avatar_url": u.avatar_url,
            "provider": u.provider,
            "provider_id": u.provider_id,
            "role": u.role.value if isinstance(u.role, Role) else u.role,
            "org_id": u.org_id,
            "created_at": u.created_at,
            "last_login": u.last_login,
        }

    # ------------------------------------------------------------------
    # User CRUD
    # ------------------------------------------------------------------

    def create_user(self, user: User) -> User:
        """Persist a new user. Returns the user."""
        users = self._read_json(self._users_path)
        users.append(self._user_to_dict(user))
        self._write_json(self._users_path, users)
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        for d in self._read_json(self._users_path):
            if d["id"] == user_id:
                return self._user_from_dict(d)
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        for d in self._read_json(self._users_path):
            if d.get("email", "").lower() == email.lower():
                return self._user_from_dict(d)
        return None

    def get_user_by_provider(self, provider: str, provider_id: str) -> Optional[User]:
        for d in self._read_json(self._users_path):
            if d.get("provider") == provider and d.get("provider_id") == provider_id:
                return self._user_from_dict(d)
        return None

    def list_users(self) -> list[User]:
        return [self._user_from_dict(d) for d in self._read_json(self._users_path)]

    def update_user_role(self, user_id: str, role: Role) -> Optional[User]:
        """Update a user's role. Returns the updated user or None."""
        users = self._read_json(self._users_path)
        for d in users:
            if d["id"] == user_id:
                d["role"] = role.value if isinstance(role, Role) else role
                self._write_json(self._users_path, users)
                return self._user_from_dict(d)
        return None

    # ------------------------------------------------------------------
    # API Keys
    # ------------------------------------------------------------------

    def create_api_key(self, user_id: str, name: str, expires_in_days: int = 90) -> tuple[APIKey, str]:
        """Create a new API key. Returns (APIKey, raw_key_string)."""
        raw_key = f"ale_{secrets.token_urlsafe(32)}"
        key_hash = self._hash_key(raw_key)
        prefix = raw_key[:8]

        now = datetime.utcnow()
        expires = now + timedelta(days=expires_in_days)

        api_key = APIKey(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            prefix=prefix,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            last_used="",
        )

        keys = self._read_json(self._keys_path)
        keys.append({
            "id": api_key.id,
            "user_id": api_key.user_id,
            "name": api_key.name,
            "key_hash": api_key.key_hash,
            "prefix": api_key.prefix,
            "created_at": api_key.created_at,
            "expires_at": api_key.expires_at,
            "last_used": api_key.last_used,
        })
        self._write_json(self._keys_path, keys)
        return api_key, raw_key

    def list_api_keys(self, user_id: str) -> list[APIKey]:
        return [
            APIKey(
                id=d["id"],
                user_id=d["user_id"],
                name=d["name"],
                key_hash=d["key_hash"],
                prefix=d["prefix"],
                created_at=d.get("created_at", ""),
                expires_at=d.get("expires_at", ""),
                last_used=d.get("last_used", ""),
            )
            for d in self._read_json(self._keys_path)
            if d["user_id"] == user_id
        ]

    def delete_api_key(self, key_id: str) -> bool:
        keys = self._read_json(self._keys_path)
        original_len = len(keys)
        keys = [d for d in keys if d["id"] != key_id]
        if len(keys) < original_len:
            self._write_json(self._keys_path, keys)
            return True
        return False

    def validate_api_key(self, raw_key: str) -> Optional[User]:
        """Validate a raw API key and return the associated user, or None."""
        key_hash = self._hash_key(raw_key)
        now = datetime.utcnow().isoformat()

        keys = self._read_json(self._keys_path)
        for d in keys:
            if d["key_hash"] == key_hash:
                # Check expiry
                if d.get("expires_at") and d["expires_at"] < now:
                    return None
                # Update last_used
                d["last_used"] = now
                self._write_json(self._keys_path, keys)
                return self.get_user(d["user_id"])
        return None

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, user_id: str, expires_in_hours: int = 24) -> Session:
        """Create a new session for a user."""
        now = datetime.utcnow()
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token=secrets.token_urlsafe(48),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(hours=expires_in_hours)).isoformat(),
        )

        sessions = self._read_json(self._sessions_path)
        sessions.append({
            "id": session.id,
            "user_id": session.user_id,
            "token": session.token,
            "created_at": session.created_at,
            "expires_at": session.expires_at,
        })
        self._write_json(self._sessions_path, sessions)
        return session

    def validate_session(self, token: str) -> Optional[User]:
        """Validate a session token and return the associated user, or None."""
        now = datetime.utcnow().isoformat()
        for d in self._read_json(self._sessions_path):
            if d["token"] == token:
                if d.get("expires_at") and d["expires_at"] < now:
                    # Expired -- clean it up
                    self.delete_session(token)
                    return None
                return self.get_user(d["user_id"])
        return None

    def delete_session(self, token: str) -> bool:
        sessions = self._read_json(self._sessions_path)
        original_len = len(sessions)
        sessions = [d for d in sessions if d["token"] != token]
        if len(sessions) < original_len:
            self._write_json(self._sessions_path, sessions)
            return True
        return False
