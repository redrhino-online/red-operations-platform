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


class TransformationError(MethodError):
    """Base class for canon thirteen transformations rule violations."""


class InvalidTransformationError(TransformationError, ValueError):
    """A Transformation or ThirteenTransformations violates an invariant.

    SPEC.md section 12.5 records the canon's thirteen transformations -- the
    overall shift, the three phase shifts and the nine step-level from/to pairs,
    titled from the Million Dollar Message (canon files 09 and 10) -- as a canon
    gap at stage 4. The canon states "there should be a from and a to for each
    step in your signature solution. 13 transformations" (canon file 09), so a
    shift with a blank identity, scope, title or state, or a shift that does not
    actually move the client between two distinct states, cannot be represented
    as one of the thirteen transformations.
    """


class TransformationTenantBoundaryError(TransformationError):
    """The transformations mixed in a solution or shift from another client.

    SPEC.md section 3: every child resource belongs to exactly one client. The
    thirteen transformations are a stage 4 asset over one client's Signature
    Solution, so the set and every shift must belong to the tenant of the
    solution it describes.
    """


class TransformationDependencyError(TransformationError):
    """The thirteen transformations were not grounded on a typed stage 4 solution.

    SPEC.md section 12.5 places the thirteen transformations at stage 4, where
    the Signature Solution already carries the three phases, nine steps and
    starting/final states. The transformations must therefore be grounded on a
    typed, same-tenant ``SignatureSolution`` rather than a free-text reference,
    so their shifts cannot be fabricated independently of the method structure.
    """


class TransformationCoverageError(TransformationError):
    """The thirteen transformations do not cover the solution exactly.

    The canon requires one overall shift, one shift per phase and one shift per
    step, thirteen in total (canon file 09: "13 transformations"), against the
    solution's three phases and nine steps (SPEC.md section 4, stage 4). A missing
    phase or step shift, an extra shift, a duplicated shift or a shift that names
    a phase or step the solution does not have makes the set an incomplete or
    self-declared view rather than the solution's transformations.
    """


class TransformationMismatchError(TransformationError):
    """A transformation's from/to states do not match the solution it describes.

    The canon defines each transformation as the actual from-point and
    to-point of the solution or one of its phases or steps (canon file 09: "a
    from and a to for each step"; canon file 10: "from point A to point B"). A
    shift whose states differ from the solution's own starting/final states, a
    phase's end states or a step's starting/final states would describe a
    transformation the locked solution does not contain.
    """


class TransformationObservationError(TransformationError):
    """The thirteen transformations were asked to be recorded as an observed result.

    SPEC.md section 3 keeps observations distinct from conclusions. The canon
    treats the transformations as the method structure that content and sales
    material live inside (canon files 09 and 10), not a measured movement, so the
    structure is never an observation.
    """
