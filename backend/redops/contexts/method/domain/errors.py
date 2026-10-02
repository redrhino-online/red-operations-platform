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


class InvalidProfitPyramidLevelError(MethodError, ValueError):
    """A Profit Pyramid level was built without its observable criteria.

    SPEC.md section 4, stage 3 "Model": each level records observable measures,
    symptoms, behaviors and problems. A level missing any of these cannot be
    recognized by a prospect and cannot be part of an approved model.
    """


class InvalidDiagnosticModelError(MethodError):
    """A diagnostic model was built without distinguishable adjacent levels.

    SPEC.md section 4, stage 3 "Diagnostic Model Approved": a prospect must be
    able to recognize their current level and desired next level using
    observable differences, so adjacent levels with an identical observable
    signature cannot represent an approvable model.
    """


class MethodDependencyError(MethodError):
    """A method pinned a missing, foreign or unapproved upstream dependency.

    SPEC.md section 3: "Production requires approved dependencies." An approved
    Signature Solution is downstream of the stage 2 primary currency and the
    stage 3 diagnostic model, so it must pin those exact tenant assets and may
    not mix another client's asset into its own evidence.
    """
