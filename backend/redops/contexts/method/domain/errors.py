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


class InvalidSignatureStepError(MethodError, ValueError):
    """A transformation step was built without its name, states or deliverables.

    SPEC.md section 4, stage 4: each named stage records starting and final
    states and its inputs, actions and outputs. A step that does not move the
    client between two distinct states cannot describe part of the transformation.
    """


class InvalidTransformationPhaseError(MethodError, ValueError):
    """A transformation phase was built without an identity, a name or any step.

    SPEC.md section 4, stage 4: three named phases group the named stages, and a
    phase that contains no step cannot carry part of the transformation.
    """


class InvalidSignatureSolutionError(MethodError):
    """A Signature Solution was not a coherent stage 4 transformation.

    SPEC.md section 4, stage 4 "IP Architecture Locked": the transformation must
    be coherent and explainable without listing every tactic. The canonical
    template fixes the shape at three phases and nine steps, the named stages
    must form one continuous chain, and the declared starting and final states
    must be the ends of that chain.
    """
