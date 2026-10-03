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
