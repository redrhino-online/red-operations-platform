"""Value objects for the Governance bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class GateState(Enum):
    """Gate states from SPEC.md section 4."""

    NOT_STARTED = "not_started"
    WORKING = "working"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    CHANGES_REQUIRED = "changes_required"
    BLOCKED = "blocked"
    WAIVED = "waived"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class AssetVersionRef:
    """An exact, pinned asset version. Gate approval pins these, not bare asset names."""

    asset_id: str
    version: int

    def __post_init__(self) -> None:
        if not self.asset_id or not self.asset_id.strip():
            raise ValueError("asset_id must be a non-empty identifier")
        if self.version < 1:
            raise ValueError("asset version must be >= 1")

    def __str__(self) -> str:
        return f"{self.asset_id}@{self.version}"


@dataclass(frozen=True)
class Waiver:
    """A scoped human decision. It never creates or substitutes for an asset."""

    reason: str
    risk_owner: str
    review_trigger: str = ""
    expires_on: date | None = None

    def __post_init__(self) -> None:
        if not self.reason or not self.reason.strip():
            raise ValueError("waiver reason is required")
        if not self.risk_owner or not self.risk_owner.strip():
            raise ValueError("waiver risk owner is required")
        if (not self.review_trigger or not self.review_trigger.strip()) and self.expires_on is None:
            raise ValueError("waiver requires an expiry or review trigger")
