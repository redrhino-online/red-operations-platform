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
    ImprovementBeforeWindowError,
    ImprovementDependencyError,
    ImprovementMetricMismatchError,
    ImprovementNotApprovedError,
    ImprovementObservationError,
    ImprovementObservationWindowError,
    ImprovementOutcomeSupportError,
    ImprovementStateError,
    InvalidScalingRecommendationError,
    MetricBaselineNotObservedError,
    MetricSampleTooSmallError,
    ScalingLearningPhaseError,
    ScalingMetricError,
    ScalingObservationError,
    ScalingTenantBoundaryError,
)
from redops.contexts.measurement.domain.value_objects import (
    FunnelEconomics,
    ImprovementApproval,
    ImprovementOutcome,
    ImprovementState,
    LearningPhase,
    MeasurementBasis,
    MeasurementRecord,
    MetricDefinition,
    MetricDirection,
    MetricFunnelStep,
    MetricUnit,
    ScalingAction,
    ScalingRecommendation,
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
    cannot begin before the owner's approval date, and the before window -- the
    established baseline period -- cannot close after that approval date, so the
    pre-change state is genuinely observed before the material change.
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
        if (
            approval is not None
            and outcome.before.window.end > approval.approved_on
        ):
            raise ImprovementBeforeWindowError(
                f"improvement {proposal.proposal_id!r} was approved on "
                f"{approval.approved_on}, but its before observation window ends "
                f"{outcome.before.window.end}; the pre-change measurement cannot "
                "extend past the owner's authorization of the change"
            )
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


class AdScalingPolicy:
    """Decides the canon's stage 10 advertising scaling action (canon 22, 23, 24).

    SPEC.md section 4, stage 10: after the performance baseline, "performance
    recommendations require evidence and owner approval before material changes",
    and SPEC.md section 12.3 maps the advertising forecast and scaling rules to the
    stage 10 canon files. The canon's scaling discipline is: do nothing while the
    campaign is still in its learning phase; then decide from the return on ad
    spend, not from a vanity cost per lead ("it's all about the roi... not some
    vanity metric, cost per lead"); if the budget cannot feed the algorithm at
    least ten leads a day, bid on clicks at an earlier funnel objective instead of
    starving learning; scale up when the observed cost per lead is at or below the
    target the desired return implies; and pause and revisit when it is above.

    The policy reads a same-tenant observed cost per lead -- never a placeholder
    figure or a metric of the wrong funnel step, unit or direction -- and returns a
    ``ScalingRecommendation`` that remains a recommendation a named owner approves
    before spend changes. It never mutates a campaign or authorizes spend.
    """

    def recommend(
        self,
        *,
        observed: MeasurementRecord,
        economics: FunnelEconomics,
        target_return_on_ad_spend: float,
        learning_phase: LearningPhase,
        minimum_leads_per_day: float = 10.0,
    ) -> ScalingRecommendation:
        if not isinstance(observed, MeasurementRecord):
            raise ScalingObservationError(
                "ad scaling must read a typed observed measurement, not a "
                "free-text figure"
            )
        if not observed.is_observed:
            raise ScalingObservationError(
                "ad scaling cannot act on a placeholder figure; the cost per lead "
                "must be observed"
            )
        self._require_cost_per_lead_metric(observed.metric)
        if not isinstance(economics, FunnelEconomics):
            raise InvalidScalingRecommendationError(
                "ad scaling requires typed funnel economics"
            )
        if observed.tenant_id != economics.tenant_id:
            raise ScalingTenantBoundaryError(
                f"the observed cost per lead belongs to tenant "
                f"{observed.tenant_id!r}, but the economics belongs to tenant "
                f"{economics.tenant_id!r}"
            )
        if not isinstance(learning_phase, LearningPhase):
            raise ScalingLearningPhaseError(
                "ad scaling requires a typed learning phase"
            )
        if (
            not isinstance(minimum_leads_per_day, (int, float))
            or isinstance(minimum_leads_per_day, bool)
            or minimum_leads_per_day < 0
        ):
            raise InvalidScalingRecommendationError(
                "the minimum leads per day must be a non-negative number"
            )
        if (
            not isinstance(target_return_on_ad_spend, (int, float))
            or isinstance(target_return_on_ad_spend, bool)
            or target_return_on_ad_spend <= 0
        ):
            raise InvalidScalingRecommendationError(
                "a scaling recommendation requires a positive target return on ad "
                "spend"
            )
        target_cost_per_lead = economics.target_cost_per_lead(
            target_return_on_ad_spend=target_return_on_ad_spend
        )
        if not learning_phase.is_complete(
            observed_on=observed.recorded_on, event_count=observed.sample_size
        ):
            action = ScalingAction.HOLD
            rationale = (
                "the campaign is still in its learning phase; do not change it "
                "until the learning period elapses"
            )
        else:
            days = (
                observed.window.end - observed.window.start
            ).days + 1
            leads_per_day = observed.sample_size / days
            if leads_per_day < minimum_leads_per_day:
                action = ScalingAction.BID_UP_FUNNEL
                rationale = (
                    f"the campaign gets {leads_per_day:.2f} leads a day, below the "
                    f"{minimum_leads_per_day} needed to feed the algorithm; bid on "
                    "clicks at an earlier funnel objective"
                )
            elif observed.value <= target_cost_per_lead:
                action = ScalingAction.SCALE_UP
                rationale = (
                    f"the observed cost per lead {observed.value} is at or below "
                    f"the target {target_cost_per_lead:.2f} for a "
                    f"{target_return_on_ad_spend}x return on ad spend; scale up"
                )
            else:
                action = ScalingAction.PAUSE_AND_REVIEW
                rationale = (
                    f"the observed cost per lead {observed.value} is above the "
                    f"target {target_cost_per_lead:.2f} for a "
                    f"{target_return_on_ad_spend}x return on ad spend; pause and "
                    "revisit with the owner"
                )
        return ScalingRecommendation(
            tenant_id=observed.tenant_id,
            action=action,
            observed=observed,
            economics=economics,
            target_return_on_ad_spend=float(target_return_on_ad_spend),
            rationale=rationale,
        )

    @staticmethod
    def _require_cost_per_lead_metric(metric: MetricDefinition) -> None:
        if (
            metric.funnel_step is not MetricFunnelStep.LEAD
            or metric.unit is not MetricUnit.CURRENCY
            or metric.direction is not MetricDirection.LOWER_IS_BETTER
        ):
            raise ScalingMetricError(
                f"ad scaling reads a cost per lead -- a lead-step currency metric "
                f"that is better when lower -- but metric {metric.metric_id!r} is "
                f"{metric.funnel_step.value!r}/{metric.unit.value!r}/"
                f"{metric.direction.value!r}"
            )
