"""Approval and measurement policy for the stage 10 improvement loop (pure domain).

SPEC.md section 4, stage 10: "performance recommendations require evidence and
owner approval before material changes". An improvement stays a proposal until a
named human owner approves it, and only an approved improvement grounded on the
same established same-tenant baseline can be measured. This mirrors the owner and
designated-authority separation used for the launch and baseline gates.
"""

from __future__ import annotations

from redops.contexts.measurement.domain.entities import ImprovementProposal
from redops.contexts.measurement.domain.errors import (
    ImprovementApprovalPrecedenceError,
    ImprovementAuthorityError,
    ImprovementDependencyError,
    ImprovementMetricMismatchError,
    ImprovementNotApprovedError,
    ImprovementObservationError,
    ImprovementObservationWindowError,
    ImprovementOutcomeSupportError,
    ImprovementStateError,
    MetricBaselineNotObservedError,
    MetricSampleTooSmallError,
)
from redops.contexts.measurement.domain.value_objects import (
    ImprovementApproval,
    ImprovementOutcome,
    ImprovementState,
    MeasurementBasis,
    MeasurementRecord,
    MetricDefinition,
)


class ImprovementApprovalPolicy:
    """Refuses an improvement approval that is out of state or not the owner's.

    SPEC.md section 4: a performance recommendation becomes a material change
    only when a named human owner approves it, and an agent cannot confer human
    approval upon itself. A rejected or already-decided proposal cannot be
    approved, and the approval must come from the proposal's owner rather than the
    proposer or anyone else. The canon's optimization discipline (canon files 23
    and 24: "you need a baseline of metrics" before optimizing) also requires the
    baseline to exist before a change is authorized, so an approval dated before
    the baseline it optimizes was established is refused.
    """

    def require(
        self, proposal: ImprovementProposal, approval: ImprovementApproval
    ) -> None:
        if proposal.state.is_terminal:
            raise ImprovementStateError(
                f"terminal improvement {proposal.proposal_id!r} cannot be "
                "approved"
            )
        if proposal.state is not ImprovementState.PROPOSED:
            raise ImprovementStateError(
                f"improvement {proposal.proposal_id!r} is "
                f"{proposal.state.value!r} and cannot be approved again"
            )
        if not proposal.baseline.is_established:
            raise ImprovementDependencyError(
                f"improvement {proposal.proposal_id!r} cannot be approved: its "
                "performance baseline is no longer established"
            )
        established_on = proposal.baseline.established_on
        if established_on is not None and approval.approved_on < established_on:
            raise ImprovementApprovalPrecedenceError(
                f"improvement {proposal.proposal_id!r} was approved on "
                f"{approval.approved_on}, before its performance baseline was "
                f"established on {established_on}; a change cannot be authorized "
                "before the baseline of metrics it optimizes exists"
            )
        if approval.approved_by != proposal.owner:
            raise ImprovementAuthorityError(
                f"improvement {proposal.proposal_id!r} was not approved by its "
                f"named owner {proposal.owner!r}"
            )
        if approval.approved_by == proposal.proposed_by:
            raise ImprovementAuthorityError(
                "the improvement proposer cannot approve its own proposal"
            )


class ImprovementMeasurementPolicy:
    """Refuses an outcome on an unapproved or ungrounded improvement.

    SPEC.md sections 3 and 4: only an approved improvement can be measured, and
    the before-and-after must be typed observed ``MeasurementRecord`` values
    attached to the improvement's registered metric, grounded on the same
    established same-tenant baseline the improvement was approved against. The
    canon's optimization discipline (canon files 23 and 24) does not accept a
    placeholder figure as a real metric, so an observed record is required and the
    projected observations must cite the approved baseline so the movement stays
    traceable and distinct from a causal conclusion. The canon also reads the
    result only after the change was authorized ("I wait 10 days to see how it
    does"; "don't touch anything for 10 days"), so the after observation window
    cannot begin before the owner's approval date.
    """

    def require(
        self, proposal: ImprovementProposal, outcome: ImprovementOutcome
    ) -> None:
        if proposal.state is not ImprovementState.APPROVED:
            raise ImprovementNotApprovedError(
                f"improvement {proposal.proposal_id!r} is "
                f"{proposal.state.value!r}; only an owner-approved improvement "
                "can be measured"
            )
        if proposal.baseline.tenant_id != outcome.tenant_id:
            raise ImprovementOutcomeSupportError(
                f"improvement {proposal.proposal_id!r} is grounded on tenant "
                f"{proposal.baseline.tenant_id!r}, but the outcome belongs to "
                f"tenant {outcome.tenant_id!r}"
            )
        if outcome.metric != proposal.metric:
            raise ImprovementMetricMismatchError(
                f"improvement {proposal.proposal_id!r} was approved against "
                f"metric {proposal.metric.metric_id!r} version "
                f"{proposal.metric.version}, but the outcome measures metric "
                f"{outcome.metric.metric_id!r} version {outcome.metric.version}"
            )
        if not proposal.baseline.is_established:
            raise ImprovementDependencyError(
                f"improvement {proposal.proposal_id!r} cannot be measured: its "
                "performance baseline is no longer established"
            )
        approval = proposal.approval
        if approval is not None and outcome.after.window.start < approval.approved_on:
            raise ImprovementObservationWindowError(
                f"improvement {proposal.proposal_id!r} was approved on "
                f"{approval.approved_on}, but its after observation window "
                f"starts {outcome.after.window.start}; a result window cannot "
                "read before the owner approved the change"
            )
        for label, record in (("before", outcome.before), ("after", outcome.after)):
            if not record.is_observed:
                raise ImprovementObservationError(
                    f"the improvement outcome {label} must be an observed "
                    "measurement; a placeholder figure cannot be a measured "
                    "before or after"
                )
            if record.metric != proposal.metric:
                raise ImprovementMetricMismatchError(
                    f"the improvement outcome {label} measurement attaches to "
                    f"metric {record.metric.metric_id!r} version "
                    f"{record.metric.version}, not the approved metric "
                    f"{proposal.metric.metric_id!r} version "
                    f"{proposal.metric.version}"
                )
            if record.tenant_id != proposal.tenant_id:
                raise ImprovementOutcomeSupportError(
                    f"the improvement outcome {label} measurement belongs to "
                    f"tenant {record.tenant_id!r}, not improvement tenant "
                    f"{proposal.tenant_id!r}"
                )
        baseline_id = proposal.baseline.baseline_id
        before_claim, after_claim = outcome.observations(baseline_id=baseline_id)
        for label, claim in (("before", before_claim), ("after", after_claim)):
            if claim.baseline_id != baseline_id:
                raise ImprovementOutcomeSupportError(
                    f"the improvement outcome {label} observation must cite the "
                    f"approved baseline {baseline_id!r}"
                )


class MetricBaselinePolicy:
    """Requires a real observed measurement before a metric can be optimized.

    SPEC.md section 4, stage 10 and the canon's optimization discipline (canon
    files 23 and 24): optimization starts only after a baseline of metrics
    exists, placeholder figures are not real metrics until measured over enough
    instances, and a rate read from too few leads is irrelevant. The policy
    selects the newest observed, same-tenant record for a metric at or above the
    caller-supplied minimum sample; a placeholder-only series or an undersized
    sample is refused with a named error rather than accepted as a baseline.
    """

    def require(
        self,
        metric: MetricDefinition,
        records: "tuple[MeasurementRecord, ...] | list[MeasurementRecord]",
        *,
        minimum_sample: int = 0,
    ) -> MeasurementRecord:
        observed = [
            record
            for record in records
            if record.metric.metric_id == metric.metric_id
            and record.metric.tenant_id == metric.tenant_id
            and record.tenant_id == metric.tenant_id
            and record.basis is MeasurementBasis.OBSERVED
        ]
        if not observed:
            raise MetricBaselineNotObservedError(
                f"metric {metric.metric_id!r} has no observed measurement for "
                f"tenant {metric.tenant_id!r}; placeholder figures cannot serve "
                "as a baseline"
            )
        adequate = [
            record
            for record in observed
            if record.sample_size >= minimum_sample
        ]
        if not adequate:
            raise MetricSampleTooSmallError(
                f"metric {metric.metric_id!r} has no observed sample of at least "
                f"{minimum_sample}; the largest observed sample is "
                f"{max(record.sample_size for record in observed)}"
            )
        return max(adequate, key=lambda record: record.recorded_on)
