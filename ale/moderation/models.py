"""Data models for the content moderation system."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModerationResult:
    """Result of a content moderation check."""

    allowed: bool
    reason: str = ""
    violation_type: str = ""  # "injection" | "profanity" | "security" | "account_locked" | ""


@dataclass
class ViolationRecord:
    """A single recorded violation."""

    timestamp: str
    violation_type: str
    prompt_snippet: str  # first 100 chars, redacted


@dataclass
class UserModerationStatus:
    """Moderation state for a user."""

    user_id: str
    violation_count: int = 0
    is_locked: bool = False
    violations: list[ViolationRecord] = field(default_factory=list)
