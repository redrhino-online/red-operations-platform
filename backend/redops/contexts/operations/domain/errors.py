"""Named domain errors for the Operations bounded context (pure domain)."""

from __future__ import annotations


class OperationsError(Exception):
    """Base class for operations domain rule violations."""


class InvalidInterventionError(OperationsError, ValueError):
    """An intervention card was built without the fields SPEC.md section 7 requires.

    SPEC.md section 7 lists the command center intervention fields as client,
    severity, reason, evidence, owner, next action, due time, state and affected
    builds, and requires the card to show why it was surfaced. A card missing its
    owner, evidence or explanation would present an unexplained intervention with
    no accountable party, so it is refused rather than rendered.
    """


class InterventionDismissalError(OperationsError):
    """An intervention was dismissed without a rationale or after it was closed.

    SPEC.md section 7 allows a card to be dismissed with rationale. A dismissal
    without a rationale would erase why an operator suppressed the card, and a
    card that is already dismissed or resolved is no longer open to dismiss.
    """


class InvalidInterventionQueryError(OperationsError, ValueError):
    """The intervention query was configured in a way its rules forbid.

    The nearing-commitment window must be a positive number of days; a zero or
    negative window would make "nearing" meaningless.
    """


class InvalidInterventionDismissalError(OperationsError, ValueError):
    """A recorded intervention dismissal is missing a field or is malformed.

    SPEC.md section 7 allows a card to be dismissed with rationale and requires
    the card to show who owns it and why it was surfaced. A durable dismissal
    record therefore names the tenant, client, reason and subject of the card it
    suppresses, the operator's rationale and the actor who dismissed it; a record
    missing any of these would suppress an intervention without a traceable
    decision or cross a client boundary.
    """


class InterventionDismissalConflictError(OperationsError):
    """A stored dismissal was re-stated with different content under its key.

    A dismissal is an operator decision and is append only: recording the exact
    same dismissal again is idempotent, but reusing a card's key with a different
    rationale or actor would rewrite the decision history rather than add to it.
    """


class InterventionDismissalTenantBoundaryError(OperationsError):
    """A dismissal was stored or resolved without a client tenant.

    SPEC.md sections 3 and 9 make an intervention a client resource that must
    carry its tenant on every command and query; storing or reading one without a
    client would either leak across clients or create an orphaned decision.
    """


class InvalidQuietHoursError(OperationsError, ValueError):
    """An owner's quiet-hours preference is missing or ambiguous.

    SPEC.md section 7 requires notifications to respect owner quiet hours. A
    preference with no owner cannot be routed, a non-time boundary cannot define
    a window, and one owner with two conflicting preferences cannot have an
    unambiguous schedule. Every case is refused rather than guessed.
    """


class InvalidNotificationError(OperationsError, ValueError):
    """A notification record is missing a required field or is self-contradictory.

    A notification must identify the intervention it carries (client, reason,
    subject) and its owner, and it must be exactly one of delivered or
    suppressed: a delivered notification cannot claim a suppression reason, and a
    suppressed notification must record why it was withheld rather than dropped
    silently (SPEC.md section 7).
    """
