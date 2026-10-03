"""Value objects for the Measurement bounded context (pure domain).

SPEC.md section 4, stage 10: after "Performance Baseline Established" the
engagement continues into Optimization, where "performance recommendations
require evidence and owner approval before material changes". The improvement
loop is shaped by the canon's optimization discipline (canon files 23 and 24):
optimization starts only once a baseline of metrics exists, changes one variable
at a time, and logs what was changed so the before-and-after movement can be
read. The recorded movement is an observation, kept distinct from a causal
conclusion (SPEC.md section 3, Measurement invariant).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from redops.contexts.execution.domain.value_objects import (
    ClaimKind,
    PerformanceClaim,
)
from redops.contexts.measurement.domain.errors import (
    InvalidImprovementError,
    InvalidImprovementOutcomeError,
)


class ImprovementState(Enum):
    """Lifecycle of a stage 10 improvement (SPEC.md section 4).

    A PROPOSED recommendation stays a proposal until a named human owner
    APPROVES it, then becomes MEASURED once a grounded before-and-after outcome is
    recorded. A REJECTED proposal is terminal and can never be approved or
    measured.
    """

    PROPOSED = "proposed"
    APPROVED = "approved"
    MEASURED = "measured"
    REJECTED = "rejected"

    @property
    def is_terminal(self) -> bool:
        return self is ImprovementState.REJECTED


@dataclass(frozen=True)
class ImprovementApproval:
    """A named human owner's approval of an improvement (SPEC.md section 4).

    SPEC.md section 4: performance recommendations require owner approval before
    material changes. The record names the approving human, the intended use the
    approval authorizes and the date, so an approval is scoped and traceable
    rather than an implicit grant of authority.
    """

    approved_by: str
    intended_use: str
    approved_on: date

    def __post_init__(self) -> None:
        for label, value in (
            ("improvement approver", self.approved_by),
            ("improvement approval intended use", self.intended_use),
        ):
            if not value or not value.strip():
                raise InvalidImprovementError(f"{label} is required")
        if not isinstance(self.approved_on, date):
            raise InvalidImprovementError(
                "improvement approval date is required"
            )


@dataclass(frozen=True)
class ImprovementOutcome:
    """The measured before-and-after of an approved improvement (SPEC.md section 3).

    SPEC.md section 4, stage 10 and Phase 5: an improvement is "approved and
    measured", and a performance review "records baseline and observed result".
    The before and after are both observations of the same subject for the same
    tenant, so the outcome reports a movement rather than asserting a cause. A
    causal conclusion is a separate PerformanceClaim that an established baseline
    and an adequate sample must support (SPEC.md section 3, Measurement
    invariant; Phase 5 TDD example "low sample size keeps causal claim as
    interpretation").
    """

    outcome_id: str
    tenant_id: str
    before: PerformanceClaim
    after: PerformanceClaim
    measured_on: date
    summary: str

    def __post_init__(self) -> None:
        for label, value in (
            ("improvement outcome id", self.outcome_id),
            ("improvement outcome tenant id", self.tenant_id),
            ("improvement outcome summary", self.summary),
        ):
            if not value or not value.strip():
                raise InvalidImprovementOutcomeError(f"{label} is required")
        if not isinstance(self.measured_on, date):
            raise InvalidImprovementOutcomeError(
                "improvement outcome measured date is required"
            )
        for label, claim in (("before", self.before), ("after", self.after)):
            if claim.tenant_id != self.tenant_id:
                raise InvalidImprovementOutcomeError(
                    f"the improvement outcome {label} observation belongs to "
                    f"tenant {claim.tenant_id!r}, not outcome tenant "
                    f"{self.tenant_id!r}"
                )
        if self.before.subject != self.after.subject:
            raise InvalidImprovementOutcomeError(
                "an improvement outcome measures the same subject before and "
                "after"
            )
        if self.before.kind is not ClaimKind.OBSERVATION:
            raise InvalidImprovementOutcomeError(
                "the before state of an improvement outcome must be an "
                "observation"
            )
        if self.after.kind is not ClaimKind.OBSERVATION:
            raise InvalidImprovementOutcomeError(
                "the after state of an improvement outcome must be an observed "
                "movement, not a causal conclusion or interpretation"
            )
