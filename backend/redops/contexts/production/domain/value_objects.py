"""Value objects for the Production bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class BuildState(Enum):
    """Lifecycle states of a BuildObject (SPEC.md section 3).

    A build moves from Identified through source, development and review to
    Approved, Production Ready, Deployed, Measuring and Optimizing. Superseded
    and Archived are terminal; an active build is any state that is neither.
    """

    IDENTIFIED = "identified"
    SOURCE_REQUIRED = "source_required"
    READY = "ready"
    IN_DEVELOPMENT = "in_development"
    INTERNAL_REVIEW = "internal_review"
    CLIENT_REVIEW = "client_review"
    CHANGES_REQUIRED = "changes_requested"
    APPROVED = "approved"
    PRODUCTION_READY = "production_ready"
    DEPLOYED = "deployed"
    MEASURING = "measuring"
    OPTIMIZING = "optimizing"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_BUILD_STATES


_TERMINAL_BUILD_STATES = frozenset({BuildState.SUPERSEDED, BuildState.ARCHIVED})


@dataclass(frozen=True)
class BuildTransition:
    """One recorded BuildObject state change (SPEC.md section 4).

    Records the actor, reason, timestamp, old and new state, and correlation ID
    so a build's history can be reconstructed and audited.
    """

    actor: str
    reason: str
    occurred_at: date
    old_state: BuildState
    new_state: BuildState
    correlation_id: str

    def __post_init__(self) -> None:
        if not self.actor or not self.actor.strip():
            raise ValueError("build transition actor is required")
        if not self.reason or not self.reason.strip():
            raise ValueError("build transition reason is required")
        if not self.correlation_id or not self.correlation_id.strip():
            raise ValueError("build transition correlation id is required")
