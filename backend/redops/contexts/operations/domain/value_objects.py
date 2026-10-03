"""Value objects for the Operations bounded context (pure domain).

SPEC.md section 7 ("Command center intervention fields") is the product
constraint for the command center cards: each intervention carries a client,
severity, reason, evidence, owner, next action, due time, state and affected
builds, shows why it was surfaced, can be dismissed with a rationale, and is
deduplicated. SPEC.md section 3 places intervention in the Operations domain
("Operations (queues, reminders, intervention)"), so the card and its signals
live here; the Governance read model the query consumes is a pure domain type,
not an ORM or framework dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time
from enum import Enum

from redops.contexts.operations.domain.errors import (
    InterventionDismissalError,
    InvalidInterventionDismissalError,
    InvalidInterventionError,
    InvalidNotificationError,
    InvalidQuietHoursError,
)


class InterventionSeverity(Enum):
    """How urgent an intervention is (SPEC.md section 7)."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InterventionReason(Enum):
    """The ranked reasons a card is surfaced (SPEC.md section 7).

    The SPEC ranks the command center interventions: "blocked critical path,
    overdue approvals, failed live journeys, and nearing commitments." The
    ``priority`` encodes that stated order (lower ranks earlier) and the
    ``severity`` labels how urgent the class is. Failed live journeys and
    overdue approvals are both high urgency but keep their distinct reasons.
    """

    BLOCKED_CRITICAL_PATH = "blocked_critical_path"
    OVERDUE_APPROVAL = "overdue_approval"
    FAILED_LIVE_JOURNEY = "failed_live_journey"
    NEARING_COMMITMENT = "nearing_commitment"

    @property
    def priority(self) -> int:
        return {
            InterventionReason.BLOCKED_CRITICAL_PATH: 0,
            InterventionReason.OVERDUE_APPROVAL: 1,
            InterventionReason.FAILED_LIVE_JOURNEY: 2,
            InterventionReason.NEARING_COMMITMENT: 3,
        }[self]

    @property
    def severity(self) -> InterventionSeverity:
        return {
            InterventionReason.BLOCKED_CRITICAL_PATH: InterventionSeverity.CRITICAL,
            InterventionReason.OVERDUE_APPROVAL: InterventionSeverity.HIGH,
            InterventionReason.FAILED_LIVE_JOURNEY: InterventionSeverity.HIGH,
            InterventionReason.NEARING_COMMITMENT: InterventionSeverity.MEDIUM,
        }[self]


class InterventionState(Enum):
    """The lifecycle state of a command center card (SPEC.md section 7)."""

    OPEN = "open"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class JourneyFailure:
    """A caller-supplied live-journey failure signal (SPEC.md sections 4 and 7).

    The Execution and Measurement contexts own live journey results; Operations
    never infers or fabricates one. A failure names the journey, its owning
    client, the accountable owner, the evidence, a next action and the builds the
    failure affects. The client scopes the signal so a failure from another
    client cannot surface in this client's command center (SPEC.md section 9).
    """

    journey_id: str
    client: str
    owner: str
    next_action: str
    evidence: frozenset[str]
    affected_builds: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        for label, value in (
            ("journey failure id", self.journey_id),
            ("journey failure client", self.client),
            ("journey failure owner", self.owner),
            ("journey failure next action", self.next_action),
        ):
            if not value or not value.strip():
                raise InvalidInterventionError(f"{label} is required")
        if not self.evidence:
            raise InvalidInterventionError(
                "a journey failure requires the evidence that shows it failed"
            )
        for item in self.evidence:
            if not item or not item.strip():
                raise InvalidInterventionError(
                    "journey failure evidence must be non-empty identifiers"
                )


@dataclass(frozen=True)
class Commitment:
    """A caller-supplied commitment with a due date (SPEC.md section 7).

    Commitments (a launch date, a client deliverable, a spend decision) are owned
    by the Engagement, Commercial and Governance contexts. Operations ranks a
    commitment as "nearing" when it falls inside the query's window, without
    inventing the commitment or its owner.
    """

    commitment_id: str
    client: str
    description: str
    due_on: date
    owner: str
    next_action: str
    affected_builds: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        for label, value in (
            ("commitment id", self.commitment_id),
            ("commitment client", self.client),
            ("commitment description", self.description),
            ("commitment owner", self.owner),
            ("commitment next action", self.next_action),
        ):
            if not value or not value.strip():
                raise InvalidInterventionError(f"{label} is required")
        if not isinstance(self.due_on, date):
            raise InvalidInterventionError("commitment due date is required")


@dataclass(frozen=True)
class Intervention:
    """One command center intervention card (SPEC.md section 7).

    Carries the fields the SPEC requires — client, severity, reason, evidence,
    owner, next action, due time, state and affected builds — plus the
    ``explanation`` that shows why the card was surfaced. ``subject`` is the
    stable identifier of the thing the card is about (a stage, journey or
    commitment) and ``key`` combines it with the client and reason so identical
    signals are deduplicated. The card is frozen; dismissing it returns a new
    ``DISMISSED`` card with the operator's rationale, never an edit in place.
    """

    client: str
    reason: InterventionReason
    severity: InterventionSeverity
    subject: str
    explanation: str
    evidence: frozenset[str]
    owner: str
    next_action: str
    due_on: date | None = None
    state: InterventionState = InterventionState.OPEN
    affected_builds: frozenset[str] = frozenset()
    resolution_note: str = ""

    def __post_init__(self) -> None:
        for label, value in (
            ("intervention client", self.client),
            ("intervention subject", self.subject),
            ("intervention explanation", self.explanation),
            ("intervention owner", self.owner),
            ("intervention next action", self.next_action),
        ):
            if not value or not value.strip():
                raise InvalidInterventionError(f"{label} is required")
        if not self.evidence:
            raise InvalidInterventionError(
                "an intervention requires the evidence that shows why it was "
                "surfaced"
            )
        for item in self.evidence:
            if not item or not item.strip():
                raise InvalidInterventionError(
                    "intervention evidence must be non-empty identifiers"
                )
        if self.state is InterventionState.OPEN and self.resolution_note:
            raise InvalidInterventionError(
                "an open intervention cannot carry a resolution note"
            )
        if self.state is InterventionState.DISMISSED and not (
            self.resolution_note and self.resolution_note.strip()
        ):
            raise InvalidInterventionError(
                "a dismissed intervention requires the operator's rationale"
            )

    @property
    def key(self) -> tuple[str, str, str]:
        """The deduplication key: client, reason and subject (SPEC.md section 7)."""
        return (self.client, self.reason.value, self.subject)

    def dismiss(self, rationale: str) -> "Intervention":
        """Return a dismissed copy of this card, recording the rationale.

        SPEC.md section 7 allows a card to be dismissed with rationale. Only an
        open card can be dismissed, and the rationale is required so the reason
        an operator suppressed the card survives.
        """
        if self.state is not InterventionState.OPEN:
            raise InterventionDismissalError(
                f"intervention {self.subject!r} is already {self.state.value} and "
                "cannot be dismissed again"
            )
        if not rationale or not rationale.strip():
            raise InterventionDismissalError(
                "a dismissal requires a rationale for suppressing the card"
            )
        return replace(
            self,
            state=InterventionState.DISMISSED,
            resolution_note=rationale,
        )


@dataclass(frozen=True)
class InterventionDismissal:
    """A durable operator decision to suppress one intervention card.

    SPEC.md section 7 allows a card to be dismissed with rationale. The derived
    cards themselves are not stored: the ranking query recomputes them from the
    production view on every read, so only the human decision to suppress one is
    durable. The record names the tenant and the card's deduplication key
    (client, reason, subject) plus the operator's rationale and the actor who
    dismissed it, so a later query can mark the matching surfaced card dismissed
    without the operator decision being lost on restart (SPEC.md sections 7 and
    9). A dismissal for a card that no longer surfaces is inert, never a
    fabricated card.
    """

    tenant_id: str
    client: str
    reason: InterventionReason
    subject: str
    rationale: str
    actor: str
    dismissed_on: date

    def __post_init__(self) -> None:
        for label, value in (
            ("intervention dismissal tenant id", self.tenant_id),
            ("intervention dismissal client", self.client),
            ("intervention dismissal subject", self.subject),
            ("intervention dismissal rationale", self.rationale),
            ("intervention dismissal actor", self.actor),
        ):
            if not value or not value.strip():
                raise InvalidInterventionDismissalError(f"{label} is required")
        if not isinstance(self.reason, InterventionReason):
            raise InvalidInterventionDismissalError(
                "an intervention dismissal requires a typed reason"
            )
        if not isinstance(self.dismissed_on, date):
            raise InvalidInterventionDismissalError(
                "an intervention dismissal requires a dismissal date"
            )

    @property
    def key(self) -> tuple[str, str, str]:
        """The card key this dismissal suppresses (SPEC.md section 7)."""
        return (self.client, self.reason.value, self.subject)


class NotificationState(Enum):
    """What happened to an intervention notification (SPEC.md section 7)."""

    DELIVERED = "delivered"
    SUPPRESSED = "suppressed"


@dataclass(frozen=True)
class QuietHours:
    """An owner's local quiet-hours window (SPEC.md section 7).

    The window is half open: a moment exactly at ``starts_at`` is inside the
    window and a moment exactly at ``ends_at`` is outside it. ``starts_at`` after
    ``ends_at`` means the window crosses midnight. Operations never invents an
    operator schedule; the preference is caller-supplied and an owner without one
    has no quiet hours (SPEC.md sections 3 and 9).
    """

    owner: str
    starts_at: time
    ends_at: time

    def __post_init__(self) -> None:
        if not self.owner or not self.owner.strip():
            raise InvalidQuietHoursError("quiet hours require an owner")
        for label, value in (("start", self.starts_at), ("end", self.ends_at)):
            if not isinstance(value, time):
                raise InvalidQuietHoursError(
                    f"quiet hours {label} must be a time of day"
                )
        if self.starts_at == self.ends_at:
            raise InvalidQuietHoursError(
                "quiet hours cannot start and end at the same time"
            )

    def covers(self, moment: time) -> bool:
        """Return whether ``moment`` falls inside this owner's quiet hours."""
        if self.starts_at < self.ends_at:
            return self.starts_at <= moment < self.ends_at
        return moment >= self.starts_at or moment < self.ends_at


@dataclass(frozen=True)
class Notification:
    """One delivery decision for an intervention card (SPEC.md section 7).

    Carries the intervention key (client, reason, subject) so a notification can
    be deduplicated against prior evaluations, plus the owner and delivery moment.
    A ``DELIVERED`` notification is the record that the owner was told; a
    ``SUPPRESSED`` one records that quiet hours withheld it, with the reason, so a
    suppression is never a silent drop.
    """

    client: str
    reason: InterventionReason
    subject: str
    owner: str
    at: datetime
    state: NotificationState
    suppression_reason: str = ""

    def __post_init__(self) -> None:
        for label, value in (
            ("notification client", self.client),
            ("notification subject", self.subject),
            ("notification owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidNotificationError(f"{label} is required")
        if not isinstance(self.at, datetime):
            raise InvalidNotificationError("notification moment is required")
        if self.state is NotificationState.SUPPRESSED and not (
            self.suppression_reason and self.suppression_reason.strip()
        ):
            raise InvalidNotificationError(
                "a suppressed notification requires the reason it was withheld"
            )
        if self.state is NotificationState.DELIVERED and self.suppression_reason:
            raise InvalidNotificationError(
                "a delivered notification cannot carry a suppression reason"
            )

    @property
    def key(self) -> tuple[str, str, str]:
        """The deduplication key, matching the intervention's key."""
        return (self.client, self.reason.value, self.subject)
