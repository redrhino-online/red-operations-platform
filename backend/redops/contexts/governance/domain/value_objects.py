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


class ApprovalOutcome(Enum):
    """Outcome of a version-specific approval request (SPEC.md section 3)."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"
    SUPERSEDED = "superseded"


class StageStatus(Enum):
    """Status of a StageRun (SPEC.md section 3 aggregate table).

    A stage reaches COMPLETE only through an accepted gate decision, never by
    activity. The other states mirror the gate states so a blocked or waived
    stage never appears complete.
    """

    NOT_STARTED = "not_started"
    WORKING = "working"
    IN_REVIEW = "in_review"
    COMPLETE = "complete"
    CHANGES_REQUIRED = "changes_required"
    BLOCKED = "blocked"
    WAIVED = "waived"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class StageTransition:
    """One recorded StageRun status change (SPEC.md section 4).

    Records the actor, reason, timestamp, old and new status, and correlation
    ID so a stage's history can be reconstructed and audited.
    """

    actor: str
    reason: str
    occurred_at: date
    old_status: StageStatus
    new_status: StageStatus
    correlation_id: str

    def __post_init__(self) -> None:
        if not self.actor or not self.actor.strip():
            raise ValueError("stage transition actor is required")
        if not self.reason or not self.reason.strip():
            raise ValueError("stage transition reason is required")
        if not self.correlation_id or not self.correlation_id.strip():
            raise ValueError("stage transition correlation id is required")


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
