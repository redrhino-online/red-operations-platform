"""Aggregate for the Measurement bounded context (pure domain).

SPEC.md section 4, stage 10: campaign activation alone does not complete the
engagement. After the performance baseline is established the engagement stays in
Optimization, where a performance recommendation "stays a proposal until a named
human owner approves it" before any material change and is then measured against
that baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from redops.contexts.execution.domain.entities import PerformanceBaseline
from redops.contexts.measurement.domain.errors import (
    ImprovementAuthorityError,
    ImprovementDependencyError,
    ImprovementMetricBoundaryError,
    ImprovementMetricError,
    InvalidImprovementError,
)
from redops.contexts.measurement.domain.value_objects import (
    ImprovementApproval,
    ImprovementOutcome,
    ImprovementState,
    MetricDefinition,
)


@dataclass(frozen=True)
class ImprovementProposal:
    """A stage 10 optimization recommendation (SPEC.md section 4).

    SPEC.md section 4: "performance recommendations require evidence and owner
    approval before material changes", and Phase 5 requires "one improvement is
    approved and measured". The canon's optimization discipline (canon files 23
    and 24) is that a baseline of metrics must exist before optimizing and that
    one variable changes at a time, so the proposal names the single lever, the
    evidence behind it and the measurement plan, and is grounded on an
    established same-tenant ``PerformanceBaseline``. The canon also treats the
    funnel metric as the lever to move, so the proposal pins a same-tenant,
    versioned ``MetricDefinition`` from the stage 10 registry and its subject is
    that registered metric's name, rather than an untyped free-text metric
    (SPEC.md section 3, Measurement aggregate).

    The proposal is frozen and starts PROPOSED. It becomes APPROVED only through
    the named owner's approval and MEASURED only after a grounded before-and-after
    outcome is recorded, so an agent cannot turn its own recommendation into an
    authorized change (SPEC.md sections 4 and 5).
    """

    proposal_id: str
    tenant_id: str
    baseline: PerformanceBaseline
    metric: MetricDefinition
    proposed_by: str
    owner: str
    subject: str
    lever: str
    evidence: str
    measurement_plan: str
    state: ImprovementState = ImprovementState.PROPOSED
    approval: ImprovementApproval | None = field(default=None)
    outcome: ImprovementOutcome | None = field(default=None)
    rejected_reason: str | None = field(default=None)

    def __post_init__(self) -> None:
        for label, value in (
            ("improvement proposal id", self.proposal_id),
            ("improvement proposal tenant id", self.tenant_id),
            ("improvement proposer", self.proposed_by),
            ("improvement owner", self.owner),
            ("improvement subject", self.subject),
            ("improvement lever", self.lever),
            ("improvement evidence", self.evidence),
            ("improvement measurement plan", self.measurement_plan),
        ):
            if not value or not value.strip():
                raise InvalidImprovementError(f"{label} is required")
        if not isinstance(self.metric, MetricDefinition):
            raise ImprovementMetricError(
                "an improvement proposal must name a registered, versioned "
                "metric definition rather than a free-text metric"
            )
        if self.metric.tenant_id != self.tenant_id:
            raise ImprovementMetricBoundaryError(
                f"improvement proposal {self.proposal_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its metric "
                f"{self.metric.metric_id!r} belongs to tenant "
                f"{self.metric.tenant_id!r}"
            )
        if self.subject != self.metric.name:
            raise ImprovementMetricError(
                f"improvement proposal {self.proposal_id!r} subject "
                f"{self.subject!r} does not match its registered metric name "
                f"{self.metric.name!r}"
            )
        if self.baseline.tenant_id != self.tenant_id:
            raise ImprovementDependencyError(
                f"improvement proposal {self.proposal_id!r} is grounded on "
                f"baseline {self.baseline.baseline_id!r} from tenant "
                f"{self.baseline.tenant_id!r}, not proposal tenant "
                f"{self.tenant_id!r}"
            )
        if not self.baseline.is_established:
            raise ImprovementDependencyError(
                f"improvement proposal {self.proposal_id!r} cannot be grounded "
                "on a performance baseline that has not passed Performance "
                "Baseline Established"
            )
        if self.owner == self.proposed_by:
            raise ImprovementAuthorityError(
                "the improvement proposal author cannot also be the named human "
                "owner that approves it"
            )
        self._require_state_consistency()

    def _require_state_consistency(self) -> None:
        if self.state is ImprovementState.PROPOSED:
            if self.approval is not None or self.outcome is not None:
                raise InvalidImprovementError(
                    "a proposed improvement cannot carry an approval or outcome"
                )
        elif self.state is ImprovementState.APPROVED:
            if self.approval is None or self.outcome is not None:
                raise InvalidImprovementError(
                    "an approved improvement requires its owner approval and no "
                    "outcome yet"
                )
        elif self.state is ImprovementState.MEASURED:
            if self.approval is None or self.outcome is None:
                raise InvalidImprovementError(
                    "a measured improvement requires both its owner approval and "
                    "its recorded outcome"
                )
        elif self.state is ImprovementState.REJECTED:
            if not self.rejected_reason or not self.rejected_reason.strip():
                raise InvalidImprovementError(
                    "a rejected improvement requires a rejection reason"
                )

    @property
    def is_approved(self) -> bool:
        return self.state is ImprovementState.APPROVED

    @property
    def is_measured(self) -> bool:
        return self.state is ImprovementState.MEASURED

    @property
    def is_terminal(self) -> bool:
        return self.state.is_terminal

    def approve(self, *, approval: ImprovementApproval) -> "ImprovementProposal":
        """Return an approved proposal once the named owner approves it.

        SPEC.md section 4: a performance recommendation requires owner approval
        before a material change, and an agent cannot confer human approval upon
        itself. The approval must come from the proposal's named owner and is
        pinned so the authorization is traceable to the human decision.
        """
        from redops.contexts.measurement.domain.policies import (
            ImprovementApprovalPolicy,
        )

        ImprovementApprovalPolicy().require(self, approval)
        return replace(self, state=ImprovementState.APPROVED, approval=approval)

    def record_outcome(
        self, *, outcome: ImprovementOutcome
    ) -> "ImprovementProposal":
        """Return a measured proposal once its grounded outcome is recorded.

        SPEC.md section 4, stage 10 and Phase 5: only an approved improvement can
        be measured, and the before-and-after is grounded on the same established
        baseline the improvement was approved against. The outcome is pinned so
        the measured movement stays traceable to its observations.
        """
        from redops.contexts.measurement.domain.policies import (
            ImprovementMeasurementPolicy,
        )

        ImprovementMeasurementPolicy().require(self, outcome)
        return replace(self, state=ImprovementState.MEASURED, outcome=outcome)

    def reject(self, *, reason: str) -> "ImprovementProposal":
        """Return this proposal rejected with a recorded reason.

        SPEC.md section 4: reject illegal transitions rather than silently
        coercing state, and a rejection is a human decision. A terminal proposal
        cannot be rejected again.
        """
        if not reason or not reason.strip():
            raise InvalidImprovementError(
                "improvement rejection reason is required"
            )
        if self.state.is_terminal:
            raise InvalidImprovementError(
                "a terminal improvement cannot be rejected again"
            )
        return replace(
            self, state=ImprovementState.REJECTED, rejected_reason=reason
        )
