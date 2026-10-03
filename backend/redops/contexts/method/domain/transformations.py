"""The canon thirteen transformations over the stage 4 Signature Solution.

SPEC.md section 12.5 records the canon's thirteen transformations -- "the overall
shift, three phase shifts and nine step-level from/to pairs, titled from the
million dollar message" -- as a canon gap at stage 4. SPEC.md section 4, stage 4
"Package IP" names the transformation map, three phases, nine steps and starting
and final states, but not the explicit thirteen from/to pairs, so adding a
required field or gate kind there is a methodology-owner decision on the gate
contract. This module makes the thirteen transformations an explicit method
structure asset over the existing stage 4 ``SignatureSolution`` without changing
the stage 4 gate contract.

The shape comes from canon files 09 and 10. Canon file 09 (Signature Solution
Core Training) says the whole Signature Solution "is one transformation ... your
whole million dollar message is one transformation", then "a mini transformation
here, 2, 3, 4, and you have nine more. So that's 13", and "there should be a from
and a to for each step in your signature solution. 13 transformations". The canon
also requires the whole thing and each shift to be titled "from the Million Dollar
Message" (canon file 09: "we want to title your signature solution using as much
of your million dollar message as possible") and calls the named shift the shift
between the client's point A and point B (canon file 10: "from point A to point
B", "the transformation ... from here to here"). Canon file 10 shows the designed
end states are chosen "based on your target market" and the "most important
problem ... they can't live without solving", so the shifts are not invented
independently of the locked solution.

The set is a stage 4 method structure asset: it is grounded on a same-tenant
``SignatureSolution``, records all thirteen shifts (one overall, one per phase,
one per step) with their from/to states matching that solution, and is never an
observation. It does not authorize production, publishing or traffic (SPEC.md
sections 4 and 9).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from redops.contexts.method.domain.entities import SignatureSolution
from redops.contexts.method.domain.errors import (
    InvalidTransformationError,
    TransformationCoverageError,
    TransformationDependencyError,
    TransformationMismatchError,
    TransformationObservationError,
    TransformationTenantBoundaryError,
)

TRANSFORMATION_COUNT = 13
PHASE_TRANSFORMATION_COUNT = 3
STEP_TRANSFORMATION_COUNT = 9


class TransformationScope(Enum):
    """Which part of the stage 4 solution a transformation describes.

    The canon splits the thirteen shifts into the overall solution (one), the
    three phases (three) and the nine steps (nine): "the whole thing is number
    one. Then you have a mini transformation here, 2, 3, 4, and you have nine
    more. So that's 13" (canon file 09).
    """

    OVERALL = "overall"
    PHASE = "phase"
    STEP = "step"


@dataclass(frozen=True)
class Transformation:
    """One canon transformation: a titled from/to shift at a given scope.

    The canon defines each transformation as a move from a point A to a point B
    (canon file 10), so a shift is frozen and reject-only: a blank identity,
    scope, target, title or state, and a shift whose from and to states are the
    same (which moves no one and is not a transformation), cannot be represented.
    """

    transformation_id: str
    tenant_id: str
    scope: TransformationScope
    scope_id: str
    title: str
    from_state: str
    to_state: str

    def __post_init__(self) -> None:
        for label, value in (
            ("transformation id", self.transformation_id),
            ("transformation tenant id", self.tenant_id),
            ("transformation scope id", self.scope_id),
            ("transformation title", self.title),
            ("transformation from state", self.from_state),
            ("transformation to state", self.to_state),
        ):
            if not value or not value.strip():
                raise InvalidTransformationError(f"{label} is required")
        if not isinstance(self.scope, TransformationScope):
            raise InvalidTransformationError(
                "a transformation must name the overall, phase or step scope"
            )
        if self.from_state == self.to_state:
            raise InvalidTransformationError(
                f"transformation {self.transformation_id!r} keeps the client on "
                f"{self.from_state!r}; a transformation must move them from point "
                "A to a different point B"
            )


@dataclass(frozen=True)
class ThirteenTransformations:
    """The canon's thirteen shifts over one locked stage 4 Signature Solution.

    Canon file 09 requires exactly thirteen transformations: the overall shift
    (the Million Dollar Message), one shift per phase and one per step. The set is
    grounded on a same-tenant ``SignatureSolution`` so each shift's from/to states
    are the solution's own states rather than a self-declared description, and it
    enforces exact coverage (3 phase shifts, 9 step shifts, 13 in total) so a
    missing or extra shift is visible rather than presented as complete.

    The overall shift is titled with the Million Dollar Message because the canon
    says "your whole million dollar message is one transformation" (canon file
    09). The set is a method structure asset, not a new required stage 4 gate kind
    (a methodology-owner decision, SPEC.md section 12.5), and it is never an
    observation.
    """

    transformations_id: str
    tenant_id: str
    million_dollar_message: str
    solution: SignatureSolution
    overall: Transformation
    phase_transformations: tuple[Transformation, ...]
    step_transformations: tuple[Transformation, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("thirteen transformations id", self.transformations_id),
            ("thirteen transformations tenant id", self.tenant_id),
            ("thirteen transformations million dollar message", self.million_dollar_message),
        ):
            if not value or not value.strip():
                raise InvalidTransformationError(f"{label} is required")
        if not isinstance(self.solution, SignatureSolution):
            raise TransformationDependencyError(
                "the thirteen transformations must be grounded on a typed stage 4 "
                "Signature Solution, not a free-text reference"
            )
        if self.solution.tenant_id != self.tenant_id:
            raise TransformationTenantBoundaryError(
                f"thirteen transformations {self.transformations_id!r} belongs to "
                f"tenant {self.tenant_id!r}, but its solution "
                f"{self.solution.solution_id!r} belongs to tenant "
                f"{self.solution.tenant_id!r}"
            )
        self._check_overall()
        self._check_phases()
        self._check_steps()

    def _check_overall(self) -> None:
        overall = self.overall
        self._require_shift(overall)
        if overall.scope is not TransformationScope.OVERALL:
            raise TransformationCoverageError(
                "the overall transformation must name the overall scope"
            )
        if overall.scope_id != self.solution.solution_id:
            raise TransformationCoverageError(
                f"the overall transformation must describe this solution "
                f"{self.solution.solution_id!r}, got {overall.scope_id!r}"
            )
        if overall.title != self.million_dollar_message:
            raise TransformationMismatchError(
                "the overall transformation must be titled with the Million Dollar "
                "Message, because the whole solution is one transformation (canon "
                "file 09)"
            )
        if (
            overall.from_state != self.solution.starting_state
            or overall.to_state != self.solution.final_state
        ):
            raise TransformationMismatchError(
                f"overall transformation {overall.transformation_id!r} must move "
                f"from the solution's starting state {self.solution.starting_state!r} "
                f"to its final state {self.solution.final_state!r}"
            )

    def _check_phases(self) -> None:
        if len(self.phase_transformations) != PHASE_TRANSFORMATION_COUNT:
            raise TransformationCoverageError(
                "the thirteen transformations require exactly "
                f"{PHASE_TRANSFORMATION_COUNT} phase transformations, got "
                f"{len(self.phase_transformations)}"
            )
        expected = {phase.phase_id: phase for phase in self.solution.phases}
        seen: set[str] = set()
        for shift in self.phase_transformations:
            self._require_shift(shift)
            if shift.scope is not TransformationScope.PHASE:
                raise TransformationCoverageError(
                    f"phase transformation {shift.transformation_id!r} must name "
                    "the phase scope"
                )
            phase = expected.get(shift.scope_id)
            if phase is None:
                raise TransformationCoverageError(
                    f"phase transformation {shift.transformation_id!r} names "
                    f"{shift.scope_id!r}, which is not a phase of this solution"
                )
            if shift.scope_id in seen:
                raise TransformationCoverageError(
                    f"the solution phase {shift.scope_id!r} has more than one "
                    "transformation"
                )
            seen.add(shift.scope_id)
            if (
                shift.from_state != phase.steps[0].starting_state
                or shift.to_state != phase.steps[-1].final_state
            ):
                raise TransformationMismatchError(
                    f"phase transformation {shift.transformation_id!r} must move "
                    f"from {phase.steps[0].starting_state!r} to "
                    f"{phase.steps[-1].final_state!r} to match phase "
                    f"{phase.phase_id!r}"
                )
        missing = set(expected) - seen
        if missing:
            raise TransformationCoverageError(
                f"the thirteen transformations miss the solution phases {sorted(missing)!r}"
            )

    def _check_steps(self) -> None:
        if len(self.step_transformations) != STEP_TRANSFORMATION_COUNT:
            raise TransformationCoverageError(
                "the thirteen transformations require exactly "
                f"{STEP_TRANSFORMATION_COUNT} step transformations, got "
                f"{len(self.step_transformations)}"
            )
        expected = {step.step_id: step for step in self.solution.steps}
        seen: set[str] = set()
        for shift in self.step_transformations:
            self._require_shift(shift)
            if shift.scope is not TransformationScope.STEP:
                raise TransformationCoverageError(
                    f"step transformation {shift.transformation_id!r} must name "
                    "the step scope"
                )
            step = expected.get(shift.scope_id)
            if step is None:
                raise TransformationCoverageError(
                    f"step transformation {shift.transformation_id!r} names "
                    f"{shift.scope_id!r}, which is not a step of this solution"
                )
            if shift.scope_id in seen:
                raise TransformationCoverageError(
                    f"the solution step {shift.scope_id!r} has more than one "
                    "transformation"
                )
            seen.add(shift.scope_id)
            if (
                shift.from_state != step.starting_state
                or shift.to_state != step.final_state
            ):
                raise TransformationMismatchError(
                    f"step transformation {shift.transformation_id!r} must move "
                    f"from {step.starting_state!r} to {step.final_state!r} to match "
                    f"step {step.step_id!r}"
                )
        missing = set(expected) - seen
        if missing:
            raise TransformationCoverageError(
                f"the thirteen transformations miss the solution steps {sorted(missing)!r}"
            )

    def _require_shift(self, shift: Transformation) -> None:
        if not isinstance(shift, Transformation):
            raise InvalidTransformationError(
                "the thirteen transformations require typed transformation shifts"
            )
        if shift.tenant_id != self.tenant_id:
            raise TransformationTenantBoundaryError(
                f"thirteen transformations {self.transformations_id!r} belongs to "
                f"tenant {self.tenant_id!r}, but transformation "
                f"{shift.transformation_id!r} belongs to tenant "
                f"{shift.tenant_id!r}"
            )

    @property
    def count(self) -> int:
        """The total number of shifts: one overall, three phase, nine step."""
        return (
            1 + len(self.phase_transformations) + len(self.step_transformations)
        )

    @property
    def all_transformations(self) -> tuple[Transformation, ...]:
        """Every shift, overall first, then phases, then steps."""
        return (
            (self.overall,)
            + self.phase_transformations
            + self.step_transformations
        )

    def transformation_for(self, scope_id: str) -> Transformation:
        """The shift describing one phase or step of the solution."""
        for shift in self.all_transformations:
            if shift.scope_id == scope_id:
                return shift
        raise TransformationCoverageError(
            f"this solution has no transformation for {scope_id!r}"
        )

    @property
    def is_method_structure(self) -> bool:
        """The transformations are the method structure content lives inside."""
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent the transformations as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The canon
        treats the transformations as the structure a client is moved through
        (canon files 09 and 10), not a measured movement, so the structure cannot
        be recorded as an observation.
        """
        raise TransformationObservationError(
            f"thirteen transformations {claim_id!r} is a method structure asset, "
            "not an observed result, and cannot be recorded as an observation"
        )
