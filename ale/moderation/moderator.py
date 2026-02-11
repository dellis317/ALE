"""Content moderation engine with violation tracking and account locking.

Checks prompts for prompt-injection patterns, profanity, and security-sensitive
content.  Tracks violations per user in ``~/.ale/moderation/violations.json``.
A second violation locks the user's account until an admin unlocks it.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ale.moderation.models import ModerationResult, UserModerationStatus, ViolationRecord

# ---------------------------------------------------------------------------
# Blocklists / patterns
# ---------------------------------------------------------------------------

# Prompt injection patterns (case-insensitive)
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)",
        r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)",
        r"forget\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)",
        r"you\s+are\s+now\s+(in\s+)?(\w+\s+)?mode",
        r"pretend\s+you\s+are",
        r"act\s+as\s+(a\s+)?(an\s+)?unrestricted",
        r"override\s+(your\s+)?(system|safety|content)\s*(prompt|filter|policy|instructions)",
        r"reveal\s+(your\s+)?(system\s+)?prompt",
        r"print\s+(your\s+)?(system\s+)?prompt",
        r"output\s+(your\s+)?(system\s+)?prompt",
        r"<\s*script[\s>]",
        r"<\s*iframe[\s>]",
        r"javascript\s*:",
        r"\b(DROP|DELETE|INSERT|UPDATE)\s+(TABLE|FROM|INTO)\b",
        r";\s*--",
        r"SELECT\s+\*\s+FROM",
        r"\bUNION\s+SELECT\b",
        r"\bexec\s*\(",
        r"\beval\s*\(",
    ]
]

# Profanity / hate speech word list (curated, small but representative)
_PROFANITY_WORDS: set[str] = {
    "fuck", "shit", "asshole", "bitch", "bastard", "damn", "cunt",
    "nigger", "nigga", "faggot", "retard", "kike", "spic", "chink",
    "kill yourself", "kys",
}

# Build word-boundary patterns from the profanity set
_PROFANITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE)
    for w in _PROFANITY_WORDS
]
# Also match multi-word phrases
_PROFANITY_PHRASE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(re.escape(w), re.IGNORECASE)
    for w in _PROFANITY_WORDS
    if " " in w
]

# Security-sensitive content patterns
_SECURITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),
    ("api_key_aws", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b")),
    ("password_assignment", re.compile(r"(?:password|passwd|secret)\s*=\s*['\"][^'\"]{8,}", re.IGNORECASE)),
]

# Max violations before account lock
_MAX_VIOLATIONS = 2


# ---------------------------------------------------------------------------
# Moderator
# ---------------------------------------------------------------------------


class ContentModerator:
    """Stateful content moderator with per-user violation tracking."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir) if base_dir else Path.home() / ".ale" / "moderation"
        self._base.mkdir(parents=True, exist_ok=True)
        self._violations_path = self._base / "violations.json"

    # -- persistence ---------------------------------------------------------

    def _load_all(self) -> dict:
        if not self._violations_path.exists():
            return {}
        try:
            return json.loads(self._violations_path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_all(self, data: dict) -> None:
        self._violations_path.write_text(json.dumps(data, indent=2))

    def _load_user(self, user_id: str) -> UserModerationStatus:
        data = self._load_all()
        entry = data.get(user_id)
        if not entry:
            return UserModerationStatus(user_id=user_id)
        violations = [
            ViolationRecord(**v) for v in entry.get("violations", [])
        ]
        return UserModerationStatus(
            user_id=user_id,
            violation_count=entry.get("violation_count", 0),
            is_locked=entry.get("is_locked", False),
            violations=violations,
        )

    def _save_user(self, status: UserModerationStatus) -> None:
        data = self._load_all()
        data[status.user_id] = {
            "violation_count": status.violation_count,
            "is_locked": status.is_locked,
            "violations": [asdict(v) for v in status.violations],
        }
        self._save_all(data)

    # -- checks --------------------------------------------------------------

    @staticmethod
    def _check_injection(text: str) -> Optional[str]:
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                return f"Prompt contains a disallowed pattern: {pattern.pattern[:60]}"
        return None

    @staticmethod
    def _check_profanity(text: str) -> Optional[str]:
        for pattern in _PROFANITY_PATTERNS:
            if pattern.search(text):
                return "Prompt contains inappropriate or offensive language."
        for pattern in _PROFANITY_PHRASE_PATTERNS:
            if pattern.search(text):
                return "Prompt contains inappropriate or offensive language."
        return None

    @staticmethod
    def _check_security(text: str) -> Optional[str]:
        for label, pattern in _SECURITY_PATTERNS:
            if pattern.search(text):
                return f"Prompt appears to contain sensitive data ({label}). Please remove it before submitting."
        return None

    # -- public API ----------------------------------------------------------

    def check_prompt(self, user_id: str, text: str) -> ModerationResult:
        """Check a prompt for violations.  Returns a ModerationResult."""
        status = self._load_user(user_id)

        # 1. Account already locked?
        if status.is_locked:
            return ModerationResult(
                allowed=False,
                reason="Your account has been locked due to repeated policy violations. Contact an administrator.",
                violation_type="account_locked",
            )

        # 2. Prompt injection
        reason = self._check_injection(text)
        if reason:
            self._record_violation(status, "injection", text)
            return ModerationResult(allowed=False, reason=reason, violation_type="injection")

        # 3. Profanity / hate speech
        reason = self._check_profanity(text)
        if reason:
            self._record_violation(status, "profanity", text)
            return ModerationResult(allowed=False, reason=reason, violation_type="profanity")

        # 4. Security-sensitive content
        reason = self._check_security(text)
        if reason:
            self._record_violation(status, "security", text)
            return ModerationResult(allowed=False, reason=reason, violation_type="security")

        return ModerationResult(allowed=True)

    def _record_violation(
        self, status: UserModerationStatus, violation_type: str, text: str
    ) -> None:
        snippet = text[:100] + ("..." if len(text) > 100 else "")
        status.violation_count += 1
        status.violations.append(
            ViolationRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                violation_type=violation_type,
                prompt_snippet=snippet,
            )
        )
        if status.violation_count >= _MAX_VIOLATIONS:
            status.is_locked = True
        self._save_user(status)

    def get_user_status(self, user_id: str) -> UserModerationStatus:
        """Return the moderation status for *user_id*."""
        return self._load_user(user_id)

    def unlock_user(self, user_id: str) -> UserModerationStatus:
        """Reset violation count and unlock *user_id*."""
        status = self._load_user(user_id)
        status.violation_count = 0
        status.is_locked = False
        status.violations = []
        self._save_user(status)
        return status
