"""Data models for AI query interaction records."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class AIQueryRecord:
    """A single AI query interaction."""

    id: str
    user_id: str
    username: str
    repo_url: str
    library_name: str
    component_name: str
    prompt: str
    response: str
    input_method: str  # "text" | "voice"
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_estimate: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = uuid.uuid4().hex[:16]
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
