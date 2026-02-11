"""File-based LLM usage tracking and budget management.

Stores all records as JSON files under ``~/.ale/llm_usage/``.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class UsageRecord:
    """A single LLM usage event."""

    id: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    purpose: str = ""
    cost_estimate: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = uuid.uuid4().hex[:12]
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class Budget:
    """Monthly budget configuration."""

    monthly_limit: float = 0.0
    alert_threshold_pct: float = 80.0
    current_month_cost: float = 0.0


@dataclass
class BudgetStatus:
    """Snapshot of current budget status."""

    allowed: bool = True
    remaining: float = 0.0
    percent_used: float = 0.0
    over_limit: bool = False
    monthly_limit: float = 0.0


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

Period = Literal["today", "week", "month", "all"]


def _period_start(period: Period) -> datetime | None:
    now = datetime.now(timezone.utc)
    if period == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # Go back to Monday
        start = start.replace(day=start.day - start.weekday())
        return start
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None  # "all"


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------


class UsageTracker:
    """File-based JSON usage tracker.

    Records are stored one-per-line in monthly files under
    ``~/.ale/llm_usage/YYYY-MM.jsonl``.  Budget config lives in
    ``~/.ale/llm_usage/budget.json``.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir) if base_dir else Path.home() / ".ale" / "llm_usage"
        self._base.mkdir(parents=True, exist_ok=True)

    # -- helpers -------------------------------------------------------------

    def _records_file(self, dt: datetime | None = None) -> Path:
        dt = dt or datetime.now(timezone.utc)
        return self._base / f"{dt.strftime('%Y-%m')}.jsonl"

    def _budget_file(self) -> Path:
        return self._base / "budget.json"

    # -- recording -----------------------------------------------------------

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        purpose: str,
        cost_estimate: float,
    ) -> UsageRecord:
        """Append a usage record and return it."""
        record = UsageRecord(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            purpose=purpose,
            cost_estimate=cost_estimate,
        )
        path = self._records_file()
        with path.open("a") as fh:
            fh.write(json.dumps(asdict(record)) + "\n")
        return record

    # -- querying ------------------------------------------------------------

    def _load_all_records(self) -> list[UsageRecord]:
        records: list[UsageRecord] = []
        for path in sorted(self._base.glob("*.jsonl")):
            for line in path.read_text().splitlines():
                line = line.strip()
                if line:
                    try:
                        records.append(UsageRecord(**json.loads(line)))
                    except (json.JSONDecodeError, TypeError):
                        continue
        return records

    def _filter_by_period(
        self, records: list[UsageRecord], period: Period
    ) -> list[UsageRecord]:
        start = _period_start(period)
        if start is None:
            return records
        start_iso = start.isoformat()
        return [r for r in records if r.timestamp >= start_iso]

    def get_usage(
        self,
        period: Period = "all",
        purpose: str | None = None,
    ) -> list[UsageRecord]:
        """Return usage records filtered by *period* and optionally *purpose*."""
        records = self._load_all_records()
        records = self._filter_by_period(records, period)
        if purpose:
            records = [r for r in records if r.purpose == purpose]
        # Most recent first
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records

    def get_total_cost(self, period: Period = "all") -> float:
        """Return the total estimated cost for a period."""
        records = self.get_usage(period)
        return round(sum(r.cost_estimate for r in records), 6)

    def get_total_tokens(self, period: Period = "all") -> dict[str, int]:
        """Return aggregated token counts for a period."""
        records = self.get_usage(period)
        return {
            "input_tokens": sum(r.input_tokens for r in records),
            "output_tokens": sum(r.output_tokens for r in records),
        }

    # -- budget management ---------------------------------------------------

    def set_budget(
        self,
        monthly_limit: float,
        alert_threshold_pct: float = 80.0,
    ) -> Budget:
        """Persist budget settings."""
        budget = Budget(
            monthly_limit=monthly_limit,
            alert_threshold_pct=alert_threshold_pct,
            current_month_cost=self.get_total_cost("month"),
        )
        self._budget_file().write_text(json.dumps(asdict(budget), indent=2))
        return budget

    def get_budget(self) -> Budget | None:
        """Load budget from disk, or return *None* if not set."""
        path = self._budget_file()
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            budget = Budget(**data)
            # Always refresh current month cost
            budget.current_month_cost = self.get_total_cost("month")
            return budget
        except (json.JSONDecodeError, TypeError):
            return None

    def check_budget(self) -> BudgetStatus:
        """Evaluate current spending against the configured budget."""
        budget = self.get_budget()
        if budget is None or budget.monthly_limit <= 0:
            return BudgetStatus(
                allowed=True,
                remaining=0.0,
                percent_used=0.0,
                over_limit=False,
                monthly_limit=0.0,
            )

        current = self.get_total_cost("month")
        remaining = max(budget.monthly_limit - current, 0.0)
        percent_used = (current / budget.monthly_limit) * 100 if budget.monthly_limit > 0 else 0.0
        over_limit = current >= budget.monthly_limit

        return BudgetStatus(
            allowed=not over_limit,
            remaining=round(remaining, 6),
            percent_used=round(percent_used, 2),
            over_limit=over_limit,
            monthly_limit=budget.monthly_limit,
        )
