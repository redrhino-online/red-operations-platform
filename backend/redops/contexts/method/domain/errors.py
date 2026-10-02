"""Named domain errors for the Method bounded context (pure domain)."""

from __future__ import annotations


class MethodError(Exception):
    """Base class for method domain rule violations."""


class InvalidMethodError(MethodError, ValueError):
    """A MethodVersion was built without its required identity or content."""


class InvalidMethodVersionError(MethodError, ValueError):
    """A semantic version was malformed or a revision was not a newer version."""


class MethodApprovalError(MethodError):
    """A method approval was requested without a valid intended use.

    SPEC.md section 3: approval pins an exact version and intended use.
    """


class MethodChangeImpactError(MethodError):
    """A change impact assessment was requested for a change it cannot describe.

    SPEC.md section 4: only a change to an approved method emits an impact
    assessment, and a version must actually advance to represent a change.
    """


class InvalidCurrencyError(MethodError, ValueError):
    """A primary currency was built without a specific person or measurable movement.

    SPEC.md section 4, stage 2 "Currency Locked": one primary outcome connects a
    specific person, a measurable movement and a distinct mechanism. A currency
    that leaves any of these unspecified cannot be locked.
    """
