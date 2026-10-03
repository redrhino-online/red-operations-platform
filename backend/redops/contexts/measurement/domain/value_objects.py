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
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Iterable

from redops.contexts.commercial.domain.value_objects import (
    AvatarProfile,
    DailyPromotionBudget,
)
from redops.contexts.execution.domain.value_objects import (
    ClaimKind,
    PerformanceClaim,
)
from redops.contexts.governance.domain.value_objects import (
    MetricMovement,
    MetricReportingBasis,
    MetricReportingView,
)
from redops.contexts.measurement.domain.errors import (
    AudienceBuildObservationBasisError,
    AudienceBuildObservationDependencyError,
    AudienceBuildObservationTenantBoundaryError,
    AudienceBuildObservationWindowOpenError,
    BannerAdCanonSpecError,
    BannerAdObservationError,
    FunnelForecastObservationError,
    FunnelMetricRoleError,
    FunnelTenantBoundaryError,
    ImprovementObservationError,
    ImprovementResultWindowOpenError,
    InvalidAudienceBuildObservationError,
    InvalidBannerAdError,
    InvalidFunnelFigureError,
    InvalidFunnelForecastError,
    InvalidImprovementError,
    InvalidImprovementOutcomeError,
    InvalidInvisibleOptInError,
    InvalidMeasurementRecordError,
    InvalidMetricDefinitionError,
    InvalidMetricReportingError,
    InvalidMetricWindowError,
    InvalidRetargetingError,
    InvalidScalingRecommendationError,
    InvalidSplitTestError,
    InvalidVideoViewAudienceError,
    InvisibleOptInContactGateError,
    InvisibleOptInDependencyError,
    InvisibleOptInObservationError,
    InvisibleOptInStepError,
    InvisibleOptInTenantBoundaryError,
    MeasurementTenantBoundaryError,
    MeasurementWindowOpenError,
    RetargetingDependencyError,
    RetargetingObservationError,
    RetargetingStepError,
    RetargetingTenantBoundaryError,
    ScalingLearningPhaseError,
    ScalingObservationError,
    ScalingRecommendationObservationError,
    ScalingTenantBoundaryError,
    SplitTestChangeError,
    SplitTestDependencyError,
    SplitTestLeverError,
    SplitTestObservationError,
    SplitTestTenantBoundaryError,
    SplitTestVariableError,
    SplitTestWindowOpenError,
    VideoViewAudienceBudgetError,
    VideoViewAudienceDependencyError,
    VideoViewAudienceObjectiveError,
    VideoViewAudienceObservationError,
    VideoViewAudienceTargetCostError,
    VideoViewAudienceTenantBoundaryError,
    VideoViewAudienceWindowError,
)

if TYPE_CHECKING:
    from redops.contexts.measurement.domain.entities import ImprovementProposal


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
    The before and after are both typed ``MeasurementRecord`` observations of the
    same registered metric for the same tenant, each over its own window with a
    basis, sample and source, so the outcome reports a reproducible movement
    rather than two free-text assertions. A causal conclusion is a separate
    PerformanceClaim that an established baseline and an adequate sample must
    support (SPEC.md section 3, Measurement invariant; Phase 5 TDD example "low
    sample size keeps causal claim as interpretation").

    Shaped by the canon's optimization discipline (canon files 23 and 24): a
    baseline of real metrics must exist before optimizing, one variable changes at
    a time, and placeholder figures are not real metrics until measured over
    enough instances. A placeholder record therefore cannot serve as a measured
    before or after, and the two observations must be distinct. The canon also
    waits before reading how a change performed (canon file 24: "I wait 10 days to
    see how it does"), so the before window must end before the after window
    starts; an after-state observed before or during its own before-state is not a
    movement. The same discipline means the after window must have closed by the
    date the outcome is read: until the result period has elapsed there is no
    complete observed movement to report.
    """

    outcome_id: str
    tenant_id: str
    metric: MetricDefinition
    before: MeasurementRecord
    after: MeasurementRecord
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
        if not isinstance(self.metric, MetricDefinition):
            raise InvalidImprovementOutcomeError(
                "an improvement outcome must name a registered, versioned metric "
                "definition rather than a free-text metric"
            )
        if self.metric.tenant_id != self.tenant_id:
            raise InvalidImprovementOutcomeError(
                f"the improvement outcome metric {self.metric.metric_id!r} "
                f"belongs to tenant {self.metric.tenant_id!r}, not outcome tenant "
                f"{self.tenant_id!r}"
            )
        if not isinstance(self.measured_on, date):
            raise InvalidImprovementOutcomeError(
                "improvement outcome measured date is required"
            )
        for label, record in (("before", self.before), ("after", self.after)):
            if not isinstance(record, MeasurementRecord):
                raise ImprovementObservationError(
                    f"the improvement outcome {label} must be a typed measurement "
                    "record over a window, not a free-text observation"
                )
            if record.tenant_id != self.tenant_id:
                raise InvalidImprovementOutcomeError(
                    f"the improvement outcome {label} observation belongs to "
                    f"tenant {record.tenant_id!r}, not outcome tenant "
                    f"{self.tenant_id!r}"
                )
            if record.metric != self.metric:
                raise ImprovementObservationError(
                    f"the improvement outcome {label} measurement attaches to "
                    f"metric {record.metric.metric_id!r} version "
                    f"{record.metric.version}, not its outcome metric "
                    f"{self.metric.metric_id!r} version {self.metric.version}"
                )
            if not record.is_observed:
                raise ImprovementObservationError(
                    f"the improvement outcome {label} must be an observed "
                    "measurement; a placeholder figure cannot be a measured "
                    "before or after"
                )
        if self.before == self.after:
            raise ImprovementObservationError(
                "an improvement outcome measures the movement between two "
                "distinct observations"
            )
        if self.before.window.end >= self.after.window.start:
            raise ImprovementObservationError(
                "an improvement outcome must read the after window only once the "
                "before window has ended: the before window "
                f"({self.before.window.start} to {self.before.window.end}) must "
                f"end before the after window starts "
                f"({self.after.window.start})"
            )
        if self.measured_on < self.after.window.end:
            raise ImprovementResultWindowOpenError(
                "an improvement outcome cannot be measured before its after "
                f"window has closed: it was measured on {self.measured_on} but "
                f"the after window ends {self.after.window.end}"
            )

    def observations(
        self, *, baseline_id: str
    ) -> tuple[PerformanceClaim, PerformanceClaim]:
        """Project the before-and-after records onto observation claims.

        SPEC.md section 3 keeps observations distinct from causal conclusions and
        keys the Measurement aggregate by its source. Each typed record is
        projected through ``MeasurementRecord.as_observation`` so the recorded
        movement cites the approved baseline, the metric name, the value with its
        unit, the sample and the source, rather than a free-text before-and-after.
        A missing baseline reference is refused so the outcome cannot be read
        without a baseline to compare against.
        """
        if not baseline_id or not baseline_id.strip():
            raise ImprovementObservationError(
                "an improvement outcome requires the approved baseline it was "
                "measured against"
            )
        return (
            self.before.as_observation(
                claim_id=f"{self.outcome_id}:before", baseline_id=baseline_id
            ),
            self.after.as_observation(
                claim_id=f"{self.outcome_id}:after", baseline_id=baseline_id
            ),
        )


class MetricUnit(Enum):
    """The unit a metric is expressed in (SPEC.md section 3).

    The canon's Metrics Matrix (canon files 23 and 24) mixes counts of funnel
    events (views, clicks, leads, calls), money (cost per lead, annual customer
    value), rates (click-through, conversion, show and close rates), ratios
    (return on ad spend) and platform scores (Facebook relevance), so the registry
    types the unit rather than storing an untyped number.
    """

    COUNT = "count"
    CURRENCY = "currency"
    PERCENT = "percent"
    RATIO = "ratio"
    SCORE = "score"


class MetricDirection(Enum):
    """Which way a metric is meant to move (canon files 23 and 24).

    The canon reads costs (cost per click, cost per lead, customer acquisition
    cost) as better when lower and results (leads, conversion rate, return on ad
    spend) as better when higher, so a recorded movement can be interpreted
    without guessing the desired direction.
    """

    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


class MetricFunnelStep(Enum):
    """The funnel step a metric belongs to (canon files 23 and 24).

    The Metrics Matrix solves down the funnel: audience, leads, strategy sessions
    and customers, with the economics that connect them (cost and value per step,
    return on ad spend). The canon warns that only the step of the funnel for
    which metrics exist can be analyzed, so the registry orders a metric by its
    step.
    """

    AUDIENCE = "audience"
    LEAD = "lead"
    APPOINTMENT = "appointment"
    CUSTOMER = "customer"
    ECONOMICS = "economics"


@dataclass(frozen=True)
class MetricDefinition:
    """A typed, versioned metric in the stage 10 registry (SPEC.md section 3).

    SPEC.md section 3 names Measurement as the context for "metric definition,
    window, baseline, observation, source", and Phase 5 requires a "metric
    registry". The canon's Metrics Matrix (canon files 23 and 24) defines each
    metric by the funnel step it measures, its unit and the direction that counts
    as good movement. The definition is frozen and versioned, so an observation
    pins the exact metric it measures and a later redefinition is a new version
    rather than a silent change to historical observations.
    """

    metric_id: str
    tenant_id: str
    name: str
    funnel_step: MetricFunnelStep
    unit: MetricUnit
    direction: MetricDirection
    version: int

    def __post_init__(self) -> None:
        for label, value in (
            ("metric definition id", self.metric_id),
            ("metric definition tenant id", self.tenant_id),
            ("metric definition name", self.name),
        ):
            if not value or not value.strip():
                raise InvalidMetricDefinitionError(f"{label} is required")
        if not isinstance(self.funnel_step, MetricFunnelStep):
            raise InvalidMetricDefinitionError(
                "a metric definition requires a funnel step"
            )
        if not isinstance(self.unit, MetricUnit):
            raise InvalidMetricDefinitionError(
                "a metric definition requires a unit"
            )
        if not isinstance(self.direction, MetricDirection):
            raise InvalidMetricDefinitionError(
                "a metric definition requires a direction"
            )
        if not isinstance(self.version, int) or isinstance(self.version, bool):
            raise InvalidMetricDefinitionError(
                "a metric definition version must be an integer"
            )
        if self.version < 1:
            raise InvalidMetricDefinitionError(
                "a metric definition version must be a positive integer so an "
                "observation pins an exact version"
            )


class MeasurementBasis(Enum):
    """Whether a measurement is a placeholder figure or a real observation.

    The canon's dashboard discipline (canon files 23 and 24) is explicit: start
    from placeholder numbers, do not change them until real metrics accumulate
    over thousands of instances, and do not read a rate from too small a sample.
    The basis keeps a planned figure distinct from an observed one so a
    placeholder can never masquerade as a measured baseline.
    """

    PLACEHOLDER = "placeholder"
    OBSERVED = "observed"


@dataclass(frozen=True)
class MeasurementWindow:
    """The date range an observation covers (SPEC.md section 3).

    SPEC.md section 3 keys a MeasurementRecord by its window, so every
    observation is scoped to an explicit start and end rather than an ambiguous
    point in time. The window is closed, so its start must not fall after its end.
    """

    start: date
    end: date

    def __post_init__(self) -> None:
        if not isinstance(self.start, date) or not isinstance(self.end, date):
            raise InvalidMetricWindowError(
                "a measurement window requires a start and end date"
            )
        if self.end < self.start:
            raise InvalidMetricWindowError(
                "a measurement window cannot end before it starts"
            )


@dataclass(frozen=True)
class MeasurementRecord:
    """An observation of a registered metric over a window (SPEC.md section 3).

    SPEC.md section 3, Measurement aggregate: "metric definition, window,
    baseline, observation, source", and its invariant that "observations are
    distinct from causal conclusions". The record attaches a numeric value and a
    sample size to a same-tenant ``MetricDefinition`` over an explicit window,
    names the basis (placeholder or observed) and the source, and can be projected
    to a ``PerformanceClaim`` of kind OBSERVATION so the improvement loop reads a
    typed observed movement rather than a causal conclusion.

    The canon's optimization discipline (canon files 23 and 24: "I wait 10 days
    to see how it does"; "don't touch anything for 10 days") reads a result only
    after the period it is measured over has elapsed, so a record is written only
    once its window has closed: ``recorded_on`` cannot fall before ``window.end``.
    A still-open window has no complete observation to report and cannot enter the
    registry or ground a baseline.
    """

    record_id: str
    tenant_id: str
    metric: MetricDefinition
    value: float
    window: MeasurementWindow
    basis: MeasurementBasis
    source: str
    sample_size: int
    recorded_on: date

    def __post_init__(self) -> None:
        for label, value in (
            ("measurement record id", self.record_id),
            ("measurement record tenant id", self.tenant_id),
            ("measurement record source", self.source),
        ):
            if not value or not value.strip():
                raise InvalidMeasurementRecordError(f"{label} is required")
        if self.metric.tenant_id != self.tenant_id:
            raise MeasurementTenantBoundaryError(
                f"measurement record {self.record_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its metric "
                f"{self.metric.metric_id!r} belongs to tenant "
                f"{self.metric.tenant_id!r}"
            )
        if not isinstance(self.value, (int, float)) or isinstance(
            self.value, bool
        ):
            raise InvalidMeasurementRecordError(
                "a measurement value must be a real number"
            )
        if not isinstance(self.window, MeasurementWindow):
            raise InvalidMeasurementRecordError(
                "a measurement record requires a measurement window"
            )
        if not isinstance(self.basis, MeasurementBasis):
            raise InvalidMeasurementRecordError(
                "a measurement record requires a placeholder or observed basis"
            )
        if not isinstance(self.sample_size, int) or isinstance(
            self.sample_size, bool
        ):
            raise InvalidMeasurementRecordError(
                "a measurement sample size must be an integer"
            )
        if self.sample_size < 0:
            raise InvalidMeasurementRecordError(
                "a measurement sample size cannot be negative"
            )
        if not isinstance(self.recorded_on, date):
            raise InvalidMeasurementRecordError(
                "a measurement record requires the date it was recorded"
            )
        if self.recorded_on < self.window.end:
            raise MeasurementWindowOpenError(
                "a measurement record cannot be written before the window it "
                f"covers has closed: it was recorded on {self.recorded_on} but "
                f"the window ends {self.window.end}"
            )

    @property
    def is_observed(self) -> bool:
        return self.basis is MeasurementBasis.OBSERVED

    @property
    def is_placeholder(self) -> bool:
        return self.basis is MeasurementBasis.PLACEHOLDER

    def as_observation(
        self,
        *,
        claim_id: str,
        baseline_id: str | None = None,
        subject: str | None = None,
    ) -> PerformanceClaim:
        """Project this record onto an observation claim (SPEC.md section 3).

        SPEC.md section 3 keeps observations distinct from causal conclusions.
        The projection always yields kind OBSERVATION, carrying the metric name as
        the subject, the value with its unit as the statement, the record's
        sample, source and tenant, and an optional baseline reference, so the
        improvement loop grounds its before-and-after on a typed observed
        measurement rather than a free-text assertion.
        """
        statement = f"{self.metric.name} was {self.value} {self.metric.unit.value}"
        return PerformanceClaim(
            claim_id=claim_id,
            tenant_id=self.tenant_id,
            subject=subject or self.metric.name,
            statement=statement,
            kind=ClaimKind.OBSERVATION,
            sample_size=self.sample_size,
            source=self.source,
            baseline_id=baseline_id,
        )


def _latest_metric_definitions(
    metrics: Iterable[MetricDefinition], *, tenant_id: str
) -> dict[str, MetricDefinition]:
    """Return the newest version of each same-tenant registered metric."""
    latest: dict[str, MetricDefinition] = {}
    for metric in metrics:
        if metric.tenant_id != tenant_id:
            continue
        current = latest.get(metric.metric_id)
        if current is None or metric.version > current.version:
            latest[metric.metric_id] = metric
    return latest


def _measured_movement(
    metric: MetricDefinition,
    improvements: Iterable["ImprovementProposal"],
    *,
    tenant_id: str,
) -> MetricMovement | None:
    """Return the measured movement of the newest measured same-tenant improvement."""
    measured = [
        proposal
        for proposal in improvements
        if proposal.tenant_id == tenant_id
        and proposal.state is ImprovementState.MEASURED
        and proposal.metric == metric
        and proposal.outcome is not None
    ]
    if not measured:
        return None
    newest = max(
        measured, key=lambda proposal: proposal.outcome.measured_on
    )
    outcome = newest.outcome
    return MetricMovement(
        improvement_id=newest.proposal_id,
        before=float(outcome.before.value),
        after=float(outcome.after.value),
        measured_on=outcome.measured_on,
    )


def metric_reporting_views(
    *,
    tenant_id: str,
    metrics: Iterable[MetricDefinition],
    records: Iterable[MeasurementRecord],
    improvements: Iterable["ImprovementProposal"] = (),
) -> tuple[MetricReportingView, ...]:
    """Project the metric registry and improvement loop onto METRICS rows.

    SPEC.md section 4 separates metrics as one of the production view's eight
    reporting dimensions, and Phase 5 requires a metric registry and observed
    results. This pure projection is the Measurement context's contribution to
    that dimension: for each registered metric that has at least one observed
    same-tenant record it reports the newest observed figure over its closed
    window, and, where an approved improvement of the same metric has been
    measured, the observed before-and-after movement. The canon's dashboard
    discipline (canon files 22, 23 and 24) treats a placeholder number as not a
    real metric until observed, so a placeholder-only metric produces no row and
    another tenant's metric is never projected onto this client's view.

    The projection reads only the registry and the improvement loop; it never
    invents a metric, window, sample, source or causal conclusion, and it counts
    no activity (SPEC.md sections 3, 4 and 12.4).
    """
    if not tenant_id or not tenant_id.strip():
        raise InvalidMetricReportingError(
            "metric reporting requires the owning tenant so the projection stays "
            "tenant scoped"
        )
    latest_definitions = _latest_metric_definitions(metrics, tenant_id=tenant_id)
    tenant_records = [
        record
        for record in records
        if record.tenant_id == tenant_id and record.metric.tenant_id == tenant_id
    ]
    rows: list[MetricReportingView] = []
    for metric_id in sorted(latest_definitions):
        metric = latest_definitions[metric_id]
        observed = [
            record
            for record in tenant_records
            if record.metric == metric and record.is_observed
        ]
        if not observed:
            continue
        newest = max(
            observed, key=lambda record: (record.recorded_on, record.record_id)
        )
        rows.append(
            MetricReportingView(
                metric_id=metric.metric_id,
                tenant_id=metric.tenant_id,
                name=metric.name,
                funnel_step=metric.funnel_step.value,
                unit=metric.unit.value,
                direction=metric.direction.value,
                value=float(newest.value),
                window_start=newest.window.start,
                window_end=newest.window.end,
                sample_size=newest.sample_size,
                source=newest.source,
                recorded_on=newest.recorded_on,
                basis=MetricReportingBasis.OBSERVED,
                movement=_measured_movement(
                    metric, improvements, tenant_id=tenant_id
                ),
            )
        )
    return tuple(rows)


class FunnelMetricRole(Enum):
    """A named input slot in the canon's stage 10 forecast equation.

    The canon's Metrics Matrix (canon files 22 and 23) reverse engineers the funnel
    from four ratios: the annual customer value, the percentage of leads that book
    a strategy session, the percentage that show up, and the percentage that
    close. Naming the role lets a forecast refuse a metric that measures the wrong
    funnel step or unit, so the equation cannot silently multiply an unrelated
    figure into the projection.
    """

    ANNUAL_CUSTOMER_VALUE = "annual_customer_value"
    LEAD_BOOKING_RATE = "lead_booking_rate"
    SESSION_SHOW_RATE = "session_show_rate"
    SESSION_CLOSE_RATE = "session_close_rate"


_FUNNEL_ROLE_SHAPES = {
    FunnelMetricRole.ANNUAL_CUSTOMER_VALUE: (
        MetricFunnelStep.CUSTOMER,
        MetricUnit.CURRENCY,
        MetricDirection.HIGHER_IS_BETTER,
    ),
    FunnelMetricRole.LEAD_BOOKING_RATE: (
        MetricFunnelStep.LEAD,
        MetricUnit.PERCENT,
        MetricDirection.HIGHER_IS_BETTER,
    ),
    FunnelMetricRole.SESSION_SHOW_RATE: (
        MetricFunnelStep.APPOINTMENT,
        MetricUnit.PERCENT,
        MetricDirection.HIGHER_IS_BETTER,
    ),
    FunnelMetricRole.SESSION_CLOSE_RATE: (
        MetricFunnelStep.APPOINTMENT,
        MetricUnit.PERCENT,
        MetricDirection.HIGHER_IS_BETTER,
    ),
}


@dataclass(frozen=True)
class FunnelFigure:
    """A typed input to the stage 10 forecast (SPEC.md section 3; canon 22, 23).

    The canon's forecast plugs real inputs into the Metrics Matrix (canon files 22
    and 23), so each figure names the registered, versioned metric it is drawn
    from and carries its own basis. A percentage figure is stored in the metric's
    percent unit (25.0 is 25%) and exposed as a fraction for the equation, while a
    currency figure is a non-negative amount. Because the basis travels with the
    figure, a placeholder figure is explicitly planned-not-observed and can never
    be mistaken for a measured metric.
    """

    role: FunnelMetricRole
    metric: MetricDefinition
    value: float
    basis: MeasurementBasis
    source: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, FunnelMetricRole):
            raise InvalidFunnelFigureError(
                "a funnel figure requires a named forecast role"
            )
        if not isinstance(self.metric, MetricDefinition):
            raise InvalidFunnelFigureError(
                "a funnel figure must draw on a registered, versioned metric "
                "definition rather than a free-text number"
            )
        if not isinstance(self.value, (int, float)) or isinstance(
            self.value, bool
        ):
            raise InvalidFunnelFigureError(
                "a funnel figure value must be a real number"
            )
        if not isinstance(self.basis, MeasurementBasis):
            raise InvalidFunnelFigureError(
                "a funnel figure requires a placeholder or observed basis"
            )
        if not self.source or not self.source.strip():
            raise InvalidFunnelFigureError("a funnel figure requires a source")
        expected = _FUNNEL_ROLE_SHAPES[self.role]
        actual = (
            self.metric.funnel_step,
            self.metric.unit,
            self.metric.direction,
        )
        if actual != expected:
            raise FunnelMetricRoleError(
                f"funnel role {self.role.value!r} requires metric "
                f"{expected[0].value!r}/{expected[1].value!r}/"
                f"{expected[2].value!r}, but metric {self.metric.metric_id!r} is "
                f"{actual[0].value!r}/{actual[1].value!r}/{actual[2].value!r}"
            )
        if self.value < 0:
            raise InvalidFunnelFigureError(
                "a funnel figure cannot be negative"
            )
        if self.metric.unit is MetricUnit.PERCENT and self.value > 100:
            raise InvalidFunnelFigureError(
                "a percentage funnel figure must be between 0 and 100"
            )

    @property
    def tenant_id(self) -> str:
        return self.metric.tenant_id

    @property
    def fraction(self) -> float:
        """Return a percentage figure as a 0-to-1 fraction for the equation."""
        if self.metric.unit is MetricUnit.PERCENT:
            return float(self.value) / 100.0
        return float(self.value)


@dataclass(frozen=True)
class FunnelEconomics:
    """The canon's stage 10 funnel unit economics (SPEC.md section 4; canon 22, 23).

    The canon's advertising forecast (canon files 22 and 23) solves the funnel
    economics before real data exists: a strategy session is worth the annual
    customer value times the close rate, and a lead is worth that session value
    times the show rate and the lead-to-booking rate ("a lead is worth $125"). The
    economics pins the four same-tenant figures so a scenario can compute the
    target cost per lead for a desired return on ad spend ("to get a 10x return on
    ad spend I would need to spend $12.50 per lead") without inventing a metric.
    """

    tenant_id: str
    annual_customer_value: FunnelFigure
    lead_booking_rate: FunnelFigure
    session_show_rate: FunnelFigure
    session_close_rate: FunnelFigure

    _SLOTS = (
        ("annual_customer_value", FunnelMetricRole.ANNUAL_CUSTOMER_VALUE),
        ("lead_booking_rate", FunnelMetricRole.LEAD_BOOKING_RATE),
        ("session_show_rate", FunnelMetricRole.SESSION_SHOW_RATE),
        ("session_close_rate", FunnelMetricRole.SESSION_CLOSE_RATE),
    )

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.tenant_id.strip():
            raise InvalidFunnelFigureError(
                "funnel economics requires the owning tenant so the equation "
                "stays tenant scoped"
            )
        for field, role in self._SLOTS:
            figure = getattr(self, field)
            if not isinstance(figure, FunnelFigure):
                raise InvalidFunnelFigureError(
                    f"funnel economics {field} must be a typed funnel figure"
                )
            if figure.role is not role:
                raise FunnelMetricRoleError(
                    f"funnel economics {field} must be the {role.value!r} role, "
                    f"not {figure.role.value!r}"
                )
            if figure.tenant_id != self.tenant_id:
                raise FunnelTenantBoundaryError(
                    f"funnel economics belongs to tenant {self.tenant_id!r}, but "
                    f"its {field} figure cites tenant {figure.tenant_id!r}"
                )

    @property
    def strategy_session_value(self) -> float:
        """The canon's value of a strategy session: customer value x close rate."""
        return (
            float(self.annual_customer_value.value)
            * self.session_close_rate.fraction
        )

    @property
    def lead_value(self) -> float:
        """The canon's value of a lead: session value x show rate x booking rate."""
        return (
            self.strategy_session_value
            * self.session_show_rate.fraction
            * self.lead_booking_rate.fraction
        )

    @property
    def input_basis(self) -> MeasurementBasis:
        """The least certain basis across the four inputs."""
        figures = tuple(getattr(self, field) for field, _ in self._SLOTS)
        if any(
            figure.basis is MeasurementBasis.PLACEHOLDER for figure in figures
        ):
            return MeasurementBasis.PLACEHOLDER
        return MeasurementBasis.OBSERVED

    def target_cost_per_lead(self, *, target_return_on_ad_spend: float) -> float:
        """The cost per lead that would yield the target return on ad spend.

        Canon file 22 turns the lead value into a bidding target ("$12.50 for a
        lead" for a 10x return), so the target cost per lead is the lead value
        divided by the desired return. A non-positive target return is refused
        rather than producing an undefined bid.
        """
        if (
            not isinstance(target_return_on_ad_spend, (int, float))
            or isinstance(target_return_on_ad_spend, bool)
            or target_return_on_ad_spend <= 0
        ):
            raise InvalidFunnelForecastError(
                "a target return on ad spend must be a positive number"
            )
        return self.lead_value / target_return_on_ad_spend


@dataclass(frozen=True)
class FunnelForecast:
    """A stage 10 funnel scenario projection (SPEC.md section 4; canon 22, 23).

    SPEC.md section 4, stage 10 reads qualified traffic, leads, appointments and
    sales, and the canon's Metrics Matrix (canon files 22 and 23) projects what a
    spend and a target cost per lead should produce: leads, strategy sessions,
    shown sessions, customers and a return on ad spend. The projection is computed
    from the typed economics and a scenario spend, so it stays distinct from an
    observed result; it can never be projected to an OBSERVATION claim, and its
    ``input_basis`` is PLACEHOLDER whenever any input is still a planned figure.
    """

    tenant_id: str
    economics: FunnelEconomics
    ad_spend: float
    cost_per_lead: float

    def __post_init__(self) -> None:
        if not isinstance(self.economics, FunnelEconomics):
            raise InvalidFunnelForecastError(
                "a funnel forecast requires typed funnel economics"
            )
        if not self.tenant_id or not self.tenant_id.strip():
            raise InvalidFunnelForecastError(
                "a funnel forecast requires the owning tenant"
            )
        if self.economics.tenant_id != self.tenant_id:
            raise FunnelTenantBoundaryError(
                f"funnel forecast belongs to tenant {self.tenant_id!r}, but its "
                f"economics belongs to tenant {self.economics.tenant_id!r}"
            )
        for label, value in (
            ("ad spend", self.ad_spend),
            ("cost per lead", self.cost_per_lead),
        ):
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or value <= 0
            ):
                raise InvalidFunnelForecastError(
                    f"a funnel forecast {label} must be a positive number"
                )

    @property
    def leads(self) -> float:
        return self.ad_spend / self.cost_per_lead

    @property
    def booked_sessions(self) -> float:
        return self.leads * self.economics.lead_booking_rate.fraction

    @property
    def shown_sessions(self) -> float:
        return self.booked_sessions * self.economics.session_show_rate.fraction

    @property
    def customers(self) -> float:
        return self.shown_sessions * self.economics.session_close_rate.fraction

    @property
    def revenue(self) -> float:
        return self.customers * float(
            self.economics.annual_customer_value.value
        )

    @property
    def return_on_ad_spend(self) -> float:
        return self.revenue / self.ad_spend

    @property
    def input_basis(self) -> MeasurementBasis:
        return self.economics.input_basis

    @property
    def is_forecast(self) -> bool:
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a forecast as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions, and the
        canon's dashboard discipline (canon files 22 and 23) treats the metrics
        matrix as a forecast solved before real data exists. A projection is not a
        ``MeasurementRecord`` and cannot be projected to an OBSERVATION claim.
        """
        raise FunnelForecastObservationError(
            f"forecast {claim_id!r} is a projection over planned or observed "
            "inputs, not an observed measurement, and cannot be recorded as an "
            "observation"
        )


def funnel_figure(
    *,
    role: FunnelMetricRole,
    metric: MetricDefinition,
    records: Iterable[MeasurementRecord],
    placeholder_value: float,
    placeholder_source: str,
) -> FunnelFigure:
    """Ground a forecast input on the registry or an explicit placeholder.

    The canon's forecast discipline (canon files 22 and 23) starts from placeholder
    numbers, then replaces them only as real metrics accumulate. This helper picks
    the newest observed same-tenant record for the registered metric when one
    exists, and otherwise falls back to the caller's placeholder value and source,
    so the resulting figure is always explicitly observed or explicitly planned.
    """
    if not isinstance(metric, MetricDefinition):
        raise InvalidFunnelFigureError(
            "a funnel figure must be grounded on a registered, versioned metric "
            "definition"
        )
    observed = [
        record
        for record in records
        if record.metric == metric
        and record.tenant_id == metric.tenant_id
        and record.is_observed
    ]
    if observed:
        newest = max(
            observed, key=lambda record: (record.recorded_on, record.record_id)
        )
        return FunnelFigure(
            role=role,
            metric=metric,
            value=float(newest.value),
            basis=MeasurementBasis.OBSERVED,
            source=newest.source,
        )
    return FunnelFigure(
        role=role,
        metric=metric,
        value=placeholder_value,
        basis=MeasurementBasis.PLACEHOLDER,
        source=placeholder_source,
    )


@dataclass(frozen=True)
class LearningPhase:
    """The waiting period before a campaign can be scaled (canon files 22, 24).

    The canon is explicit that a new ad set must be left alone while Facebook
    learns: "for the first 10 days or 100 plus conversions, they're simply
    learning", and "after seven to 10 days, Facebook is going to transition from
    the learning phase to the optimization phase". Touching a campaign during
    learning restarts the phase, so the phase is a typed period with a start date,
    a minimum day count and a minimum event count, and it is complete once either
    threshold is met.
    """

    started_on: date
    minimum_days: int = 7
    minimum_events: int = 100

    def __post_init__(self) -> None:
        if not isinstance(self.started_on, date):
            raise ScalingLearningPhaseError(
                "a learning phase requires the date the campaign started"
            )
        for label, value in (
            ("minimum days", self.minimum_days),
            ("minimum events", self.minimum_events),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ScalingLearningPhaseError(
                    f"a learning phase {label} must be an integer"
                )
        if self.minimum_days < 1:
            raise ScalingLearningPhaseError(
                "a learning phase minimum days must be positive"
            )
        if self.minimum_events < 0:
            raise ScalingLearningPhaseError(
                "a learning phase minimum events cannot be negative"
            )

    def days_elapsed(self, *, observed_on: date) -> int:
        return (observed_on - self.started_on).days

    def is_complete(self, *, observed_on: date, event_count: int) -> bool:
        """Whether the learning phase has ended by time or by conversion volume."""
        return (
            self.days_elapsed(observed_on=observed_on) >= self.minimum_days
            or event_count >= self.minimum_events
        )


class ScalingAction(Enum):
    """A named stage 10 advertising scaling action (canon files 22, 23, 24).

    The canon's scaling discipline yields a small set of moves: leave a campaign
    alone while it is learning (HOLD), increase budget on a campaign whose return
    on ad spend is at or above target (SCALE_UP), bid on an earlier funnel
    objective when the budget cannot feed the algorithm enough leads (BID_UP_FUNNEL,
    canon file 24: "if you can't afford to get 10 leads a day... bid on clicks"),
    and pause and revisit a campaign whose observed cost per lead is above the
    target that its desired return implies (PAUSE_AND_REVIEW).
    """

    HOLD = "hold"
    SCALE_UP = "scale_up"
    BID_UP_FUNNEL = "bid_up_funnel"
    PAUSE_AND_REVIEW = "pause_and_review"


@dataclass(frozen=True)
class ScalingRecommendation:
    """A stage 10 recommendation to change ad spend (SPEC.md section 4; canon 22-24).

    SPEC.md section 4, stage 10: "performance recommendations require evidence and
    owner approval before material changes". The canon's scaling rule (canon files
    22, 23 and 24) is that the decision is about the return on ad spend derived
    from the observed cost per lead, never a vanity cost per lead, and it is read
    only after the learning phase. The recommendation pins the observed
    same-tenant cost per lead, the economics and target return it was judged
    against, and a rationale, so the action is a traceable proposal rather than an
    authorization. It can never be projected to an OBSERVATION claim and always
    requires a named owner's approval before spend changes.
    """

    tenant_id: str
    action: ScalingAction
    observed: MeasurementRecord
    economics: FunnelEconomics
    target_return_on_ad_spend: float
    rationale: str

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.tenant_id.strip():
            raise InvalidScalingRecommendationError(
                "a scaling recommendation requires the owning tenant so it stays "
                "tenant scoped"
            )
        if not isinstance(self.action, ScalingAction):
            raise InvalidScalingRecommendationError(
                "a scaling recommendation requires a named scale action"
            )
        if not isinstance(self.observed, MeasurementRecord):
            raise ScalingObservationError(
                "a scaling recommendation must read a typed observed measurement, "
                "not a free-text figure"
            )
        if not self.observed.is_observed:
            raise ScalingObservationError(
                "a scaling recommendation cannot be driven by a placeholder "
                "figure; the cost per lead must be observed"
            )
        if not isinstance(self.economics, FunnelEconomics):
            raise InvalidScalingRecommendationError(
                "a scaling recommendation requires typed funnel economics"
            )
        if (
            self.observed.tenant_id != self.tenant_id
            or self.economics.tenant_id != self.tenant_id
            or self.observed.metric.tenant_id != self.tenant_id
        ):
            raise ScalingTenantBoundaryError(
                f"scaling recommendation belongs to tenant {self.tenant_id!r}, "
                "but its observation or economics cites another tenant"
            )
        if (
            not isinstance(self.target_return_on_ad_spend, (int, float))
            or isinstance(self.target_return_on_ad_spend, bool)
            or self.target_return_on_ad_spend <= 0
        ):
            raise InvalidScalingRecommendationError(
                "a scaling recommendation requires a positive target return on ad "
                "spend"
            )
        if not self.rationale or not self.rationale.strip():
            raise InvalidScalingRecommendationError(
                "a scaling recommendation requires a rationale"
            )

    @property
    def target_cost_per_lead(self) -> float:
        """The cost per lead that the target return on ad spend implies."""
        return self.economics.target_cost_per_lead(
            target_return_on_ad_spend=self.target_return_on_ad_spend
        )

    @property
    def leads_per_day(self) -> float:
        """The observed lead volume per day over the observation window."""
        days = (self.observed.window.end - self.observed.window.start).days + 1
        return self.observed.sample_size / days

    @property
    def requires_owner_approval(self) -> bool:
        return True

    @property
    def is_recommendation(self) -> bool:
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a scaling recommendation as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions, and
        SPEC.md section 4 requires owner approval before a material change. A
        recommendation to change spend is an unapproved proposal and can never be
        recorded as an observed measurement.
        """
        raise ScalingRecommendationObservationError(
            f"scaling recommendation {claim_id!r} is an unapproved proposal to "
            "change spend, not an observed measurement, and cannot be recorded as "
            "an observation"
        )


class SplitTestMode(Enum):
    """The canon's two ways to run a stage 10 split test (canon file 24).

    Canon file 24 gives a limited-budget operator exactly two options: "I pause
    the first ad, clone it and make the changes I want to make and run a new one
    ... Or if I have the budget, I just run them both together. That's only two
    ways you could possibly do it." Naming the mode keeps the change log honest
    about whether the original was paused or both ran together.
    """

    PAUSE_AND_CLONE = "pause_and_clone"
    RUN_CONCURRENT = "run_concurrent"


@dataclass(frozen=True)
class SplitTestChange:
    """The single variable a stage 10 split test changes (canon files 22, 24).

    Canon file 24: "I'm not going to change this headline and the image and the
    button text. Why? Because how do I know what the hell worked?" The change
    names exactly one variable and its before and after values, and the two values
    must differ so the log records a real version change rather than a no-op.
    """

    variable: str
    from_value: str
    to_value: str

    def __post_init__(self) -> None:
        for label, value in (
            ("split test variable", self.variable),
            ("split test before value", self.from_value),
            ("split test after value", self.to_value),
        ):
            if not value or not value.strip():
                raise InvalidSplitTestError(f"{label} is required")
        if self.from_value == self.to_value:
            raise SplitTestChangeError(
                f"split test variable {self.variable!r} has identical before and "
                "after values, so it records no change"
            )


@dataclass(frozen=True)
class SplitTest:
    """A logged stage 10 one-variable split test (SPEC.md section 4; canon 22-24).

    SPEC.md section 4, stage 10 keeps the observed movement distinct from a
    causal conclusion and requires owner approval before material changes. The
    canon's split-test discipline (canon files 22, 23 and 24) logs what changed
    before reading the result: start only once a baseline of metrics exists, change
    one variable at a time, pause-and-clone or run both, and wait for the result
    window to close ("I wait 10 days to see how it does"). The log is bound to the
    staged optimization -- the same tenant's owner-approved ``ImprovementProposal``
    -- and its single changed variable must be that optimization's exact lever, so
    the change stays traceable to the authorized optimization and its established
    baseline rather than becoming an untethered experiment.

    The log records the change, not the measured movement; it can never be
    projected to an OBSERVATION claim. The separate ``ImprovementOutcome`` remains
    the measured before-and-after, so the two are never conflated (SPEC.md section
    3, Measurement invariant).
    """

    test_id: str
    tenant_id: str
    optimization: "ImprovementProposal"
    changes: tuple[SplitTestChange, ...]
    mode: SplitTestMode
    window: MeasurementWindow
    read_on: date
    rationale: str

    def __post_init__(self) -> None:
        from redops.contexts.measurement.domain.entities import (
            ImprovementProposal,
        )

        for label, value in (
            ("split test id", self.test_id),
            ("split test tenant id", self.tenant_id),
            ("split test rationale", self.rationale),
        ):
            if not value or not value.strip():
                raise InvalidSplitTestError(f"{label} is required")
        if not isinstance(self.optimization, ImprovementProposal):
            raise InvalidSplitTestError(
                "a split test must bind to the staged optimization it logs, not "
                "a free-standing experiment"
            )
        if self.optimization.tenant_id != self.tenant_id:
            raise SplitTestTenantBoundaryError(
                f"split test {self.test_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its optimization "
                f"{self.optimization.proposal_id!r} belongs to tenant "
                f"{self.optimization.tenant_id!r}"
            )
        if not (
            self.optimization.is_approved or self.optimization.is_measured
        ):
            raise SplitTestDependencyError(
                f"split test {self.test_id!r} cannot log a change for "
                f"optimization {self.optimization.proposal_id!r} in state "
                f"{self.optimization.state.value!r}; only an owner-approved "
                "optimization can authorize a material change"
            )
        if not self.optimization.baseline.is_established:
            raise SplitTestDependencyError(
                f"split test {self.test_id!r} cannot log a change for "
                f"optimization {self.optimization.proposal_id!r}: its "
                "performance baseline is no longer established"
            )
        if not isinstance(self.changes, tuple) or len(self.changes) != 1:
            raise SplitTestVariableError(
                f"split test {self.test_id!r} must change exactly one variable "
                "at a time; changing none or more than one makes the result "
                "unattributable"
            )
        change = self.changes[0]
        if not isinstance(change, SplitTestChange):
            raise InvalidSplitTestError(
                "a split test change must be a typed variable change with before "
                "and after values"
            )
        if change.variable != self.optimization.lever:
            raise SplitTestLeverError(
                f"split test {self.test_id!r} changes {change.variable!r}, but "
                f"its approved optimization authorizes the lever "
                f"{self.optimization.lever!r}"
            )
        if not isinstance(self.mode, SplitTestMode):
            raise InvalidSplitTestError(
                "a split test requires the canon's pause-and-clone or "
                "run-concurrent mode"
            )
        if not isinstance(self.window, MeasurementWindow):
            raise InvalidSplitTestError(
                "a split test requires the window it is read over"
            )
        if not isinstance(self.read_on, date):
            raise InvalidSplitTestError(
                "a split test requires the date its result is read"
            )
        if self.read_on < self.window.end:
            raise SplitTestWindowOpenError(
                "a split test cannot read its result before its test window has "
                f"closed: it was read on {self.read_on} but the window ends "
                f"{self.window.end}"
            )

    @property
    def variable(self) -> str:
        """The single variable this split test changes."""
        return self.changes[0].variable

    @property
    def is_split_test(self) -> bool:
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a split-test change log as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions; the log
        records what changed, while the measured movement is the separate
        improvement outcome. A change log is therefore never an observation.
        """
        raise SplitTestObservationError(
            f"split test {claim_id!r} logs the variable that changed, not an "
            "observed movement or causal conclusion, and cannot be recorded as "
            "an observation"
        )


class RetargetingChannel(Enum):
    """A named ad medium a retargeting campaign runs on (canon files 33, 34).

    The canon's retargeting setup (canon files 33 and 34) separates campaigns by
    medium: Facebook newsfeed and right rail ads, the Google Display Network, and
    Twitter retargeting, each with its own traffic requirement and ad spec. Naming
    the channel keeps a focused campaign tied to the medium it was built for
    rather than an untyped label.
    """

    FACEBOOK_NEWSFEED = "facebook_newsfeed"
    FACEBOOK_RIGHT_RAIL = "facebook_right_rail"
    GOOGLE_DISPLAY = "google_display"
    TWITTER = "twitter"


@dataclass(frozen=True)
class TrackingCode:
    """The canon's retargeting pixel on the funnel pages (canon files 33, 34).

    The canon's retargeting roadmap starts with step one, the tracking code: place
    JavaScript on every page you want to retarget, through the ad network's
    account, so visitors can later be segmented (canon file 34: "You place some
    JavaScript on every page of your site that you want to retarget"; canon file
    33: "put a pixel on every page in your funnel"). The code names its provider
    and the exact pages it is installed on, so a later list or goal is grounded on
    a real installation rather than an assumed one. It cannot verify that every
    page carries it (that is an integration concern), so it records the declared
    pages explicitly.
    """

    code_id: str
    tenant_id: str
    provider: str
    pages: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("tracking code id", self.code_id),
            ("tracking code tenant id", self.tenant_id),
            ("tracking code provider", self.provider),
        ):
            if not value or not value.strip():
                raise InvalidRetargetingError(f"{label} is required")
        if not isinstance(self.pages, tuple) or not self.pages:
            raise InvalidRetargetingError(
                "a tracking code must be installed on at least one page; a pixel "
                "on no page cannot retarget anyone"
            )
        for page in self.pages:
            if not page or not page.strip():
                raise InvalidRetargetingError(
                    "a tracking code page cannot be blank"
                )


@dataclass(frozen=True)
class ConversionGoal:
    """The canon's conversion goal at a completed funnel URL (canon files 33, 34).

    The canon's retargeting roadmap sets up a conversion goal for every URL that
    signifies a completed outcome -- an opt in, a webinar registration, a
    requested consultation or a purchase -- and tells the operator to put a dollar
    value on each one, even a guessed one, so return can be computed (canon file
    34: "Every conversion goal that you set up... put a dollar amount, even if you
    have to guess"). The goal is grounded on a same-tenant tracking code, and its
    value carries a ``MeasurementBasis`` so an estimated value stays explicitly
    planned while a real one is observed. The canon's example values are
    reverse-engineered per lead or consultation, so a non-negative amount is
    required.
    """

    goal_id: str
    tenant_id: str
    name: str
    url: str
    value: float
    basis: MeasurementBasis
    tracking_code: TrackingCode

    def __post_init__(self) -> None:
        for label, value in (
            ("conversion goal id", self.goal_id),
            ("conversion goal tenant id", self.tenant_id),
            ("conversion goal name", self.name),
            ("conversion goal url", self.url),
        ):
            if not value or not value.strip():
                raise InvalidRetargetingError(f"{label} is required")
        if not isinstance(self.tracking_code, TrackingCode):
            raise RetargetingDependencyError(
                "a conversion goal must be set up on an installed tracking code, "
                "not a free-text pixel"
            )
        if self.tracking_code.tenant_id != self.tenant_id:
            raise RetargetingTenantBoundaryError(
                f"conversion goal {self.goal_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its tracking code "
                f"{self.tracking_code.code_id!r} belongs to tenant "
                f"{self.tracking_code.tenant_id!r}"
            )
        if not isinstance(self.value, (int, float)) or isinstance(
            self.value, bool
        ):
            raise InvalidRetargetingError(
                "a conversion goal value must be a real number"
            )
        if self.value < 0:
            raise InvalidRetargetingError(
                "a conversion goal value cannot be negative"
            )
        if not isinstance(self.basis, MeasurementBasis):
            raise InvalidRetargetingError(
                "a conversion goal requires a placeholder or observed basis"
            )

    @property
    def is_placeholder(self) -> bool:
        return self.basis is MeasurementBasis.PLACEHOLDER

    @property
    def is_observed(self) -> bool:
        return self.basis is MeasurementBasis.OBSERVED


@dataclass(frozen=True)
class RetargetingAudience:
    """The canon's retargeting list, a funnel-step segmentation (canon 33, 34).

    The canon creates a retargeting list for each funnel step: "lists of segments
    for user groups with a defined state within a defined stage of your funnel",
    for example people who opted in but did not book (canon file 34). The list
    names its funnel step, the achieved conversion goal that puts a prospect in it
    and the lookback window it retains them for, and is grounded on the same
    tenant's tracking code. It cannot exist without the tracking code and the goal
    it segments from, so the roadmap's order is enforced at construction rather
    than assumed.
    """

    audience_id: str
    tenant_id: str
    name: str
    funnel_step: str
    achieved_goal: ConversionGoal
    lookback_days: int
    tracking_code: TrackingCode

    def __post_init__(self) -> None:
        for label, value in (
            ("retargeting audience id", self.audience_id),
            ("retargeting audience tenant id", self.tenant_id),
            ("retargeting audience name", self.name),
            ("retargeting audience funnel step", self.funnel_step),
        ):
            if not value or not value.strip():
                raise InvalidRetargetingError(f"{label} is required")
        if not isinstance(self.achieved_goal, ConversionGoal):
            raise RetargetingDependencyError(
                "a retargeting list must segment on a typed conversion goal, not "
                "a free-text state"
            )
        if not isinstance(self.tracking_code, TrackingCode):
            raise RetargetingDependencyError(
                "a retargeting list must be built on an installed tracking code, "
                "not a free-text pixel"
            )
        if (
            self.achieved_goal.tenant_id != self.tenant_id
            or self.tracking_code.tenant_id != self.tenant_id
        ):
            raise RetargetingTenantBoundaryError(
                f"retargeting audience {self.audience_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its goal or tracking code cites another "
                "tenant"
            )
        if self.achieved_goal.tracking_code != self.tracking_code:
            raise RetargetingDependencyError(
                f"retargeting audience {self.audience_id!r} segments a goal "
                f"recorded on tracking code "
                f"{self.achieved_goal.tracking_code.code_id!r}, not its own "
                f"tracking code {self.tracking_code.code_id!r}"
            )
        if not isinstance(self.lookback_days, int) or isinstance(
            self.lookback_days, bool
        ):
            raise InvalidRetargetingError(
                "a retargeting list lookback window must be an integer number of "
                "days"
            )
        if self.lookback_days < 1:
            raise InvalidRetargetingError(
                "a retargeting list lookback window must be at least one day so "
                "the segment is bounded"
            )


@dataclass(frozen=True)
class RetargetingCampaign:
    """The canon's focused retargeting campaign (canon files 33, 34).

    The canon creates "super focused campaigns that should accomplish one goal at a
    time" to move a named audience from one funnel step to the next, on a specific
    medium (canon file 34). The campaign is grounded on a same-tenant retargeting
    list and a target conversion goal that shares that list's tracking code, and it
    must name the next funnel step; a campaign whose target step is the step its
    audience already occupies presents no next action and is refused. It is a plan,
    not an authorization to spend: the launching platform's owner approval gates
    still apply (SPEC.md sections 4 and 9).
    """

    campaign_id: str
    tenant_id: str
    name: str
    audience: RetargetingAudience
    from_step: str
    to_step: str
    target_goal: ConversionGoal
    channel: RetargetingChannel

    def __post_init__(self) -> None:
        for label, value in (
            ("retargeting campaign id", self.campaign_id),
            ("retargeting campaign tenant id", self.tenant_id),
            ("retargeting campaign name", self.name),
            ("retargeting campaign from step", self.from_step),
            ("retargeting campaign to step", self.to_step),
        ):
            if not value or not value.strip():
                raise InvalidRetargetingError(f"{label} is required")
        if not isinstance(self.audience, RetargetingAudience):
            raise RetargetingDependencyError(
                "a focused retargeting campaign must target a typed retargeting "
                "list, not a free-text audience"
            )
        if not isinstance(self.target_goal, ConversionGoal):
            raise RetargetingDependencyError(
                "a focused retargeting campaign must target a typed conversion "
                "goal, not a free-text outcome"
            )
        if not isinstance(self.channel, RetargetingChannel):
            raise InvalidRetargetingError(
                "a focused retargeting campaign requires a named ad channel"
            )
        if (
            self.audience.tenant_id != self.tenant_id
            or self.target_goal.tenant_id != self.tenant_id
        ):
            raise RetargetingTenantBoundaryError(
                f"retargeting campaign {self.campaign_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its list or target goal cites another "
                "tenant"
            )
        if self.target_goal.tracking_code != self.audience.tracking_code:
            raise RetargetingDependencyError(
                f"retargeting campaign {self.campaign_id!r} targets a goal on "
                f"tracking code {self.target_goal.tracking_code.code_id!r}, not "
                f"the tracking code {self.audience.tracking_code.code_id!r} its "
                "list was built on"
            )
        if self.from_step == self.to_step:
            raise RetargetingStepError(
                f"retargeting campaign {self.campaign_id!r} targets step "
                f"{self.to_step!r}, which is the step its audience is already on; "
                "a focused campaign must move a prospect to a new step"
            )


class RetargetingStep(Enum):
    """The buildable sections of the canon's retargeting roadmap (canon 33, 34).

    The canon's roadmap has six steps: tracking code, conversion goals, retargeting
    lists, focused campaigns, effective ads and metrics. This context owns the
    planning of the first four as typed value objects; the canon's effective ads
    step is logged one variable at a time by the stage 10 ``SplitTest``, and its
    metrics step is grounded by the ``MetricDefinition`` registry, so the plan does
    not duplicate them.
    """

    TRACKING_CODE = "tracking_code"
    CONVERSION_GOALS = "conversion_goals"
    RETARGETING_LISTS = "retargeting_lists"
    FOCUSED_CAMPAIGNS = "focused_campaigns"


REQUIRED_RETARGETING_STEPS: tuple[RetargetingStep, ...] = (
    RetargetingStep.TRACKING_CODE,
    RetargetingStep.CONVERSION_GOALS,
    RetargetingStep.RETARGETING_LISTS,
    RetargetingStep.FOCUSED_CAMPAIGNS,
)


@dataclass(frozen=True)
class RetargetingPlan:
    """The canon's retargeting roadmap for a client (SPEC.md section 4; canon 33, 34).

    SPEC.md section 4, stage 8 requires tracking and analytics among the funnel
    assets before "Funnel Complete", and section 12.3 maps the retargeting roadmap
    to stage 8 and stage 10. The canon's roadmap (canon files 33 and 34) is a
    plan of a tracking code, conversion goals, retargeting lists and focused
    campaigns, ordered so the earlier step exists before the later one. The plan
    binds those typed sections to a named owner and one tenant, requires every list
    and campaign to be grounded in the plan's own tracking code and declared goals,
    and reports the sections it is still missing.

    The plan is never an observed result: it is the roadmap the campaign runs
    against, while the measured movement it later produces is a separate
    ``MeasurementRecord`` or ``ImprovementOutcome`` (SPEC.md section 3, Measurement
    invariant). It does not authorize spend or traffic; that remains a named human
    approval (SPEC.md sections 4 and 9).
    """

    plan_id: str
    tenant_id: str
    owner: str
    tracking_code: TrackingCode
    goals: tuple[ConversionGoal, ...]
    audiences: tuple[RetargetingAudience, ...]
    campaigns: tuple[RetargetingCampaign, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("retargeting plan id", self.plan_id),
            ("retargeting plan tenant id", self.tenant_id),
            ("retargeting plan owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidRetargetingError(f"{label} is required")
        if not isinstance(self.tracking_code, TrackingCode):
            raise RetargetingDependencyError(
                "a retargeting plan must be grounded on a typed tracking code"
            )
        if self.tracking_code.tenant_id != self.tenant_id:
            raise RetargetingTenantBoundaryError(
                f"retargeting plan {self.plan_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its tracking code belongs to tenant "
                f"{self.tracking_code.tenant_id!r}"
            )
        for goal in self.goals:
            if not isinstance(goal, ConversionGoal):
                raise RetargetingDependencyError(
                    "a retargeting plan goal must be a typed conversion goal"
                )
            if goal.tenant_id != self.tenant_id:
                raise RetargetingTenantBoundaryError(
                    f"retargeting plan {self.plan_id!r} cites goal "
                    f"{goal.goal_id!r} from another tenant"
                )
            if goal.tracking_code != self.tracking_code:
                raise RetargetingDependencyError(
                    f"retargeting plan {self.plan_id!r} cites goal "
                    f"{goal.goal_id!r} recorded on tracking code "
                    f"{goal.tracking_code.code_id!r}, not the plan's own tracking "
                    f"code {self.tracking_code.code_id!r}; the roadmap's conversion "
                    "goals must be set up on the same pixel as the tracking code "
                    "(canon file 34)"
                )
        for audience in self.audiences:
            if not isinstance(audience, RetargetingAudience):
                raise RetargetingDependencyError(
                    "a retargeting plan list must be a typed retargeting audience"
                )
            if audience.tenant_id != self.tenant_id:
                raise RetargetingTenantBoundaryError(
                    f"retargeting plan {self.plan_id!r} cites list "
                    f"{audience.audience_id!r} from another tenant"
                )
            if audience.tracking_code != self.tracking_code:
                raise RetargetingDependencyError(
                    f"retargeting plan {self.plan_id!r} list "
                    f"{audience.audience_id!r} is built on a tracking code the "
                    "plan does not declare"
                )
            if audience.achieved_goal not in self.goals:
                raise RetargetingDependencyError(
                    f"retargeting plan {self.plan_id!r} list "
                    f"{audience.audience_id!r} segments an undeclared goal "
                    f"{audience.achieved_goal.goal_id!r}"
                )
        for campaign in self.campaigns:
            if not isinstance(campaign, RetargetingCampaign):
                raise RetargetingDependencyError(
                    "a retargeting plan campaign must be a typed retargeting "
                    "campaign"
                )
            if campaign.tenant_id != self.tenant_id:
                raise RetargetingTenantBoundaryError(
                    f"retargeting plan {self.plan_id!r} cites campaign "
                    f"{campaign.campaign_id!r} from another tenant"
                )
            if campaign.audience not in self.audiences:
                raise RetargetingDependencyError(
                    f"retargeting plan {self.plan_id!r} campaign "
                    f"{campaign.campaign_id!r} targets an undeclared list "
                    f"{campaign.audience.audience_id!r}"
                )
            if campaign.target_goal not in self.goals:
                raise RetargetingDependencyError(
                    f"retargeting plan {self.plan_id!r} campaign "
                    f"{campaign.campaign_id!r} targets an undeclared goal "
                    f"{campaign.target_goal.goal_id!r}"
                )

    @property
    def sections(self) -> tuple[RetargetingStep, ...]:
        """The roadmap sections present, in the canon's order."""
        present: list[RetargetingStep] = [RetargetingStep.TRACKING_CODE]
        if self.goals:
            present.append(RetargetingStep.CONVERSION_GOALS)
        if self.audiences:
            present.append(RetargetingStep.RETARGETING_LISTS)
        if self.campaigns:
            present.append(RetargetingStep.FOCUSED_CAMPAIGNS)
        return tuple(present)

    def missing_sections(self) -> tuple[RetargetingStep, ...]:
        present = set(self.sections)
        return tuple(
            step for step in REQUIRED_RETARGETING_STEPS if step not in present
        )

    @property
    def is_complete(self) -> bool:
        return not self.missing_sections()

    @property
    def is_plan(self) -> bool:
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a retargeting plan as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The plan
        describes the pixels, goals, lists and campaigns that will run, while any
        measured movement is a separate observation, so a plan is never an
        observation.
        """
        raise RetargetingObservationError(
            f"retargeting plan {claim_id!r} is a roadmap of pixels, goals, lists "
            "and campaigns, not an observed result, and cannot be recorded as an "
            "observation"
        )


MIN_VIDEO_VIEW_SECONDS: int = 10
"""The canon's minimum meaningful ten-second view (canon file 30).

Canon file 30: "I'm trying to pay 5 to 20 cents for people to watch 10 seconds
of the video" and "10 seconds to start with"; a three-second view "is too small
of a commitment to really gauge interest or engagement".
"""

MAX_VIDEO_VIEW_RETENTION_DAYS: int = 30
"""The canon's longest retargeting lookback for a video-view audience.

Canon file 30: retarget "people who have watched 10 seconds of the video in the
last 30 days" and "I don't want to go out more than 30 days".
"""


class AudienceBuildingObjective(Enum):
    """The objective a stage 10 audience campaign optimizes for (canon file 30).

    The canon separates the objectives an audience campaign could chase -- page
    post engagement, leads and conversions -- from the one it should use. Canon
    file 30: "the goal of the campaign is not to generate leads, not to get
    customers, not to get appointments... I'm gonna bid on video views", because
    page post engagement "was too weak of engagement". Typing the objective lets a
    campaign refuse any objective other than video views rather than an untyped
    label that cannot be checked.
    """

    VIDEO_VIEWS = "video_views"
    PAGE_POST_ENGAGEMENT = "page_post_engagement"
    LEAD_GENERATION = "lead_generation"
    CONVERSIONS = "conversions"


@dataclass(frozen=True)
class VideoViewWindow:
    """The canon's ten-second view and thirty-day retention (canon file 30).

    Canon file 30 defines the audience by a view threshold and a lookback window:
    "10 second video views, 30 days is a good catch all", with the threshold a
    minimum commitment ("10 seconds to start with"; three seconds is "too small of
    a commitment") and thirty days the longest lookback ("I don't want to go out
    more than 30 days"). It is frozen and reject-only, so a weaker or unbounded
    window cannot be represented as the audience definition, while a stricter
    window (a longer view or a shorter lookback) is allowed.
    """

    view_seconds: int
    retention_days: int

    def __post_init__(self) -> None:
        for label, value in (
            ("video view seconds", self.view_seconds),
            ("video view retention days", self.retention_days),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise VideoViewAudienceWindowError(
                    f"the {label} must be an integer"
                )
        if self.view_seconds < MIN_VIDEO_VIEW_SECONDS:
            raise VideoViewAudienceWindowError(
                f"a video view window requires at least a "
                f"{MIN_VIDEO_VIEW_SECONDS} second view, because a shorter view is "
                "too small a commitment to gauge interest (canon file 30)"
            )
        if self.retention_days < 1:
            raise VideoViewAudienceWindowError(
                "a video view retention window must be at least one day so the "
                "audience is bounded"
            )
        if self.retention_days > MAX_VIDEO_VIEW_RETENTION_DAYS:
            raise VideoViewAudienceWindowError(
                f"a video view retention window cannot exceed "
                f"{MAX_VIDEO_VIEW_RETENTION_DAYS} days (canon file 30: do not go "
                "out more than 30 days)"
            )

    @classmethod
    def canon(cls) -> "VideoViewWindow":
        """The canon's catch-all ten-second view over thirty days."""
        return cls(
            view_seconds=MIN_VIDEO_VIEW_SECONDS,
            retention_days=MAX_VIDEO_VIEW_RETENTION_DAYS,
        )

    @property
    def uses_canon_catch_all(self) -> bool:
        """Whether this is exactly the canon's ten-second / thirty-day window."""
        return (
            self.view_seconds == MIN_VIDEO_VIEW_SECONDS
            and self.retention_days == MAX_VIDEO_VIEW_RETENTION_DAYS
        )


@dataclass(frozen=True)
class InterestTargeting:
    """The canon's interest-stacked avatar targeting (canon file 30).

    Canon file 30 builds the audience from the avatar's "interests, hobbies,
    experts, software tools": "I'm going to have my avatar framework in front of
    me" and target by "interests, likes, affinities, associations, publications",
    combining several so the reach is qualified ("It's called interest stacking.
    It's way more powerful"). The targeting is grounded on a same-tenant
    ``AvatarProfile`` and stacks at least two distinct named interests, so it
    cannot be an untyped guess or a single over-broad interest.
    """

    targeting_id: str
    tenant_id: str
    avatar: AvatarProfile
    interests: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("interest targeting id", self.targeting_id),
            ("interest targeting tenant id", self.tenant_id),
        ):
            if not value or not value.strip():
                raise InvalidVideoViewAudienceError(f"{label} is required")
        if not isinstance(self.avatar, AvatarProfile):
            raise VideoViewAudienceDependencyError(
                "an audience campaign must target a typed avatar, not a "
                "free-text persona"
            )
        if self.avatar.tenant_id != self.tenant_id:
            raise VideoViewAudienceTenantBoundaryError(
                f"interest targeting {self.targeting_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its avatar {self.avatar.avatar_id!r} "
                f"belongs to tenant {self.avatar.tenant_id!r}"
            )
        if not isinstance(self.interests, tuple) or len(self.interests) < 2:
            raise InvalidVideoViewAudienceError(
                "interest stacking requires at least two named interests, because "
                "one interest alone is too broad to qualify the audience (canon "
                "file 30)"
            )
        seen: set[str] = set()
        for interest in self.interests:
            if not interest or not interest.strip():
                raise InvalidVideoViewAudienceError(
                    "a targeting interest must not be blank"
                )
            normalized = interest.strip().lower()
            if normalized in seen:
                raise InvalidVideoViewAudienceError(
                    f"a targeting interest {interest!r} is repeated; interest "
                    "stacking combines distinct interests"
                )
            seen.add(normalized)


@dataclass(frozen=True)
class VideoViewAudienceCampaign:
    """The canon's ten-second-view audience building campaign (SPEC.md 12.5).

    SPEC.md section 12.5 records the canon's ten-second-view audience campaign
    (canon file 30) as the remaining planning asset of the audience-building and
    content flywheel gap, and section 4 keeps external spend behind human
    authorization. The campaign binds a named owner to a same-tenant avatar's
    interest-stacked targeting, the canon's video-view window, a positive low
    daily budget, a caller-supplied target cost per ten-second view, a same-tenant
    tracking code and at least one existing retargeting list it builds for. It
    refuses any objective other than video views, a blank identity, an untyped or
    cross-tenant dependency and a non-positive target cost.

    The campaign is a stage 10 plan, not a gate kind and not an authorization to
    spend: launching it and any payment remain named human decisions (SPEC.md
    sections 4 and 9). It is never an observed result; the audience size it later
    reaches is a separate observation (SPEC.md section 3, Measurement invariant).
    """

    campaign_id: str
    tenant_id: str
    owner: str
    name: str
    objective: AudienceBuildingObjective
    targeting: InterestTargeting
    view_window: VideoViewWindow
    daily_budget: DailyPromotionBudget
    target_cost_per_view: Decimal
    tracking_code: TrackingCode
    retargeting_lists: tuple[RetargetingAudience, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("video view audience campaign id", self.campaign_id),
            ("video view audience campaign tenant id", self.tenant_id),
            ("video view audience campaign owner", self.owner),
            ("video view audience campaign name", self.name),
        ):
            if not value or not value.strip():
                raise InvalidVideoViewAudienceError(f"{label} is required")
        if not isinstance(self.objective, AudienceBuildingObjective):
            raise VideoViewAudienceObjectiveError(
                "an audience campaign requires a named objective"
            )
        if self.objective is not AudienceBuildingObjective.VIDEO_VIEWS:
            raise VideoViewAudienceObjectiveError(
                f"an audience campaign objective {self.objective.value!r} cannot "
                "build the warm video-view audience; the objective must be video "
                "views, not leads, conversions or page post engagement (canon "
                "file 30)"
            )
        if not isinstance(self.targeting, InterestTargeting):
            raise VideoViewAudienceDependencyError(
                "an audience campaign must be grounded on typed interest "
                "targeting, not a free-text audience"
            )
        if self.targeting.tenant_id != self.tenant_id:
            raise VideoViewAudienceTenantBoundaryError(
                f"video view audience campaign {self.campaign_id!r} belongs to "
                f"tenant {self.tenant_id!r}, but its targeting cites tenant "
                f"{self.targeting.tenant_id!r}"
            )
        if not isinstance(self.view_window, VideoViewWindow):
            raise VideoViewAudienceDependencyError(
                "an audience campaign requires a typed video view window"
            )
        if not isinstance(self.daily_budget, DailyPromotionBudget):
            raise VideoViewAudienceDependencyError(
                "an audience campaign requires a typed daily promotion budget"
            )
        if not isinstance(self.target_cost_per_view, Decimal):
            raise InvalidVideoViewAudienceError(
                "a target cost per ten-second view must be a Decimal"
            )
        if self.target_cost_per_view <= 0:
            raise InvalidVideoViewAudienceError(
                "a target cost per ten-second view must be positive"
            )
        if not isinstance(self.tracking_code, TrackingCode):
            raise VideoViewAudienceDependencyError(
                "an audience campaign must be built on a typed tracking code, not "
                "a free-text pixel"
            )
        if self.tracking_code.tenant_id != self.tenant_id:
            raise VideoViewAudienceTenantBoundaryError(
                f"video view audience campaign {self.campaign_id!r} belongs to "
                f"tenant {self.tenant_id!r}, but its tracking code "
                f"{self.tracking_code.code_id!r} belongs to tenant "
                f"{self.tracking_code.tenant_id!r}"
            )
        if (
            not isinstance(self.retargeting_lists, tuple)
            or not self.retargeting_lists
        ):
            raise VideoViewAudienceDependencyError(
                "an audience campaign must build for at least one existing "
                "retargeting list, or the warm audience has no consumer"
            )
        for audience in self.retargeting_lists:
            if not isinstance(audience, RetargetingAudience):
                raise VideoViewAudienceDependencyError(
                    "an audience campaign must build for typed retargeting lists, "
                    "not a free-text audience"
                )
            if audience.tenant_id != self.tenant_id:
                raise VideoViewAudienceTenantBoundaryError(
                    f"video view audience campaign {self.campaign_id!r} cites "
                    f"retargeting list {audience.audience_id!r} from another "
                    "tenant"
                )
            if audience.tracking_code != self.tracking_code:
                raise VideoViewAudienceDependencyError(
                    f"video view audience campaign {self.campaign_id!r} cites "
                    f"retargeting list {audience.audience_id!r} built on tracking "
                    f"code {audience.tracking_code.code_id!r}, not the campaign's "
                    f"tracking code {self.tracking_code.code_id!r}"
                )

    @property
    def is_campaign(self) -> bool:
        return True

    @property
    def retargeting_steps(self) -> tuple[str, ...]:
        """The funnel steps of the existing retargeting lists this campaign warms."""
        return tuple(audience.funnel_step for audience in self.retargeting_lists)

    def builds_for(self, audience: RetargetingAudience) -> bool:
        """Whether this campaign builds the warm audience for a retargeting list."""
        return audience in self.retargeting_lists

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent an audience campaign as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The
        campaign describes the targeting, budget and view window that will run,
        while the audience size it later reaches is a separate observation, so a
        campaign is never an observation.
        """
        raise VideoViewAudienceObservationError(
            f"video view audience campaign {claim_id!r} is a plan of targeting, "
            "budget and view window, not an observed result, and cannot be "
            "recorded as an observation"
        )


class VideoViewAudiencePolicy:
    """Refuses a stage 10 audience campaign outside the canon's spend bounds.

    Canon file 30 starts the audience campaign at a low daily spend ("$5 a day...
    I'll spend ten. Ten bucks a day") and calls "under 20 cents" per ten-second
    view a rough viability metric, warning that a much higher cost means a problem
    with the topic. The policy keeps a starting campaign low and its target cost
    affordable; it never authorizes spend, which remains a named human decision
    (SPEC.md sections 4 and 9).
    """

    @staticmethod
    def require_low_daily_budget(
        campaign: VideoViewAudienceCampaign, *, ceiling: Decimal
    ) -> None:
        if not isinstance(campaign, VideoViewAudienceCampaign):
            raise VideoViewAudienceDependencyError(
                "the low daily budget check requires a typed audience campaign"
            )
        if not isinstance(ceiling, Decimal) or ceiling <= 0:
            raise InvalidVideoViewAudienceError(
                "the low daily budget ceiling must be a positive Decimal"
            )
        if campaign.daily_budget.amount > ceiling:
            raise VideoViewAudienceBudgetError(
                f"video view audience campaign {campaign.campaign_id!r} starts at "
                f"{campaign.daily_budget.amount} {campaign.daily_budget.currency} "
                f"a day, above the low starting ceiling {ceiling}; the audience "
                "campaign is for building a warm audience cheaply, not for "
                "scaling spend (canon file 30)"
            )

    @staticmethod
    def require_target_cost_below(
        campaign: VideoViewAudienceCampaign, *, ceiling: Decimal
    ) -> None:
        if not isinstance(campaign, VideoViewAudienceCampaign):
            raise VideoViewAudienceDependencyError(
                "the target cost check requires a typed audience campaign"
            )
        if not isinstance(ceiling, Decimal) or ceiling <= 0:
            raise InvalidVideoViewAudienceError(
                "the target cost ceiling must be a positive Decimal"
            )
        if campaign.target_cost_per_view > ceiling:
            raise VideoViewAudienceTargetCostError(
                f"video view audience campaign {campaign.campaign_id!r} targets "
                f"{campaign.target_cost_per_view} per ten-second view, above the "
                f"viable ceiling {ceiling}; a higher cost signals a problem with "
                "the topic (canon file 30)"
            )


@dataclass(frozen=True)
class LeadMagnetAsset:
    """The canon's lead magnet delivered without an opt in (canon file 34).

    Canon file 34's invisible opt-in gives a non-converted visitor "the cheat
    sheet without requiring an opt in", so the delivered asset is named by its
    locator rather than by a contact record. The asset records whether its normal
    delivery would require contact information; the invisible opt-in itself
    refuses a gated asset, so a magnet that is contact-gated elsewhere can still be
    represented here rather than silently redefined.
    """

    asset_id: str
    tenant_id: str
    name: str
    delivery_locator: str
    requires_contact_information: bool

    def __post_init__(self) -> None:
        for label, value in (
            ("lead magnet asset id", self.asset_id),
            ("lead magnet tenant id", self.tenant_id),
            ("lead magnet name", self.name),
            ("lead magnet delivery locator", self.delivery_locator),
        ):
            if not value or not value.strip():
                raise InvalidInvisibleOptInError(f"{label} is required")
        if not isinstance(self.requires_contact_information, bool):
            raise InvalidInvisibleOptInError(
                "a lead magnet requires_contact_information flag must be a boolean"
            )


@dataclass(frozen=True)
class NonConvertedSegment:
    """The canon's non-converted visitor segment (canon file 34).

    Canon file 34's invisible opt-in recovers the prospect who "hit that landing
    page and don't opt in", so the segment names the funnel step and page the
    prospect stalled on and the conversion goal they did not achieve. It is
    grounded on a same-tenant tracking code and the unachieved goal on that code,
    so a segment cannot be invented apart from the pixel and goal that define it.
    """

    segment_id: str
    tenant_id: str
    name: str
    landing_step: str
    landing_page: str
    unachieved_goal: ConversionGoal
    tracking_code: TrackingCode

    def __post_init__(self) -> None:
        for label, value in (
            ("non-converted segment id", self.segment_id),
            ("non-converted segment tenant id", self.tenant_id),
            ("non-converted segment name", self.name),
            ("non-converted segment landing step", self.landing_step),
            ("non-converted segment landing page", self.landing_page),
        ):
            if not value or not value.strip():
                raise InvalidInvisibleOptInError(f"{label} is required")
        if not isinstance(self.unachieved_goal, ConversionGoal):
            raise InvisibleOptInDependencyError(
                "a non-converted segment must name the typed conversion goal the "
                "prospect did not achieve, not a free-text state"
            )
        if not isinstance(self.tracking_code, TrackingCode):
            raise InvisibleOptInDependencyError(
                "a non-converted segment must be built on an installed tracking "
                "code, not a free-text pixel"
            )
        if (
            self.unachieved_goal.tenant_id != self.tenant_id
            or self.tracking_code.tenant_id != self.tenant_id
        ):
            raise InvisibleOptInTenantBoundaryError(
                f"non-converted segment {self.segment_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its goal or tracking code cites another "
                "tenant"
            )
        if self.unachieved_goal.tracking_code != self.tracking_code:
            raise InvisibleOptInDependencyError(
                f"non-converted segment {self.segment_id!r} names a goal recorded "
                f"on tracking code {self.unachieved_goal.tracking_code.code_id!r}, "
                f"not its own tracking code {self.tracking_code.code_id!r}"
            )


@dataclass(frozen=True)
class InvisibleOptInOffer:
    """The canon's invisible opt-in offer (SPEC.md section 12.5; canon file 34).

    SPEC.md section 12.5 records the canon's invisible opt-in offer as the
    remaining retargeting-system candidate, an explicit stage 8/10 planning asset
    that avoids a named-owner pipeline change. Canon file 34 retargets a prospect
    who reached the lead-magnet page but did not opt in and gives them the lead
    magnet "without requiring an opt in", pushing them "all the way down the funnel
    without ever needing an email address". The offer therefore binds a named owner
    to the non-converted segment it recovers, the contact-free lead magnet it
    delivers, the typed channel it runs on and the same-tenant retargeting audience
    it advances. It refuses a blank identity, an untyped or cross-tenant
    dependency, a contact-gated lead magnet and an audience that does not move the
    prospect past the stalled step.

    The offer is a plan, not a gate kind and not an authorization to spend or send:
    putting ads in front of prospects remains a named human decision (SPEC.md
    sections 4 and 9). It is never an observed result; the opt-ins or engagement it
    later produces are separate observations (SPEC.md section 3).
    """

    offer_id: str
    tenant_id: str
    owner: str
    name: str
    segment: NonConvertedSegment
    lead_magnet: LeadMagnetAsset
    channel: RetargetingChannel
    advances: RetargetingAudience

    def __post_init__(self) -> None:
        for label, value in (
            ("invisible opt-in offer id", self.offer_id),
            ("invisible opt-in offer tenant id", self.tenant_id),
            ("invisible opt-in offer owner", self.owner),
            ("invisible opt-in offer name", self.name),
        ):
            if not value or not value.strip():
                raise InvalidInvisibleOptInError(f"{label} is required")
        if not isinstance(self.segment, NonConvertedSegment):
            raise InvisibleOptInDependencyError(
                "an invisible opt-in offer must recover a typed non-converted "
                "segment, not a free-text audience"
            )
        if self.segment.tenant_id != self.tenant_id:
            raise InvisibleOptInTenantBoundaryError(
                f"invisible opt-in offer {self.offer_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its segment "
                f"{self.segment.segment_id!r} belongs to tenant "
                f"{self.segment.tenant_id!r}"
            )
        if not isinstance(self.lead_magnet, LeadMagnetAsset):
            raise InvisibleOptInDependencyError(
                "an invisible opt-in offer must deliver a typed lead magnet, not "
                "a free-text asset"
            )
        if self.lead_magnet.tenant_id != self.tenant_id:
            raise InvisibleOptInTenantBoundaryError(
                f"invisible opt-in offer {self.offer_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its lead magnet "
                f"{self.lead_magnet.asset_id!r} belongs to tenant "
                f"{self.lead_magnet.tenant_id!r}"
            )
        if self.lead_magnet.requires_contact_information:
            raise InvisibleOptInContactGateError(
                f"invisible opt-in offer {self.offer_id!r} delivers lead magnet "
                f"{self.lead_magnet.asset_id!r} behind a contact gate; the "
                "invisible opt-in gives the asset without requiring an opt in "
                "(canon file 34)"
            )
        if not isinstance(self.channel, RetargetingChannel):
            raise InvalidInvisibleOptInError(
                "an invisible opt-in offer requires a named ad channel"
            )
        if not isinstance(self.advances, RetargetingAudience):
            raise InvisibleOptInDependencyError(
                "an invisible opt-in offer must advance a typed retargeting "
                "audience, not a free-text list"
            )
        if self.advances.tenant_id != self.tenant_id:
            raise InvisibleOptInTenantBoundaryError(
                f"invisible opt-in offer {self.offer_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its advanced audience "
                f"{self.advances.audience_id!r} belongs to tenant "
                f"{self.advances.tenant_id!r}"
            )
        if self.advances.tracking_code != self.segment.tracking_code:
            raise InvisibleOptInDependencyError(
                f"invisible opt-in offer {self.offer_id!r} advances an audience "
                f"built on tracking code {self.advances.tracking_code.code_id!r}, "
                f"not the segment's tracking code "
                f"{self.segment.tracking_code.code_id!r}"
            )
        if self.advances.funnel_step == self.segment.landing_step:
            raise InvisibleOptInStepError(
                f"invisible opt-in offer {self.offer_id!r} advances to the "
                f"{self.advances.funnel_step!r} step, which is the step the "
                "prospect stalled on; the offer must push the prospect down the "
                "funnel to a new step (canon file 34)"
            )

    @property
    def delivers_without_contact(self) -> bool:
        """Whether the delivered lead magnet needs no contact information."""
        return not self.lead_magnet.requires_contact_information

    @property
    def is_offer(self) -> bool:
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent an invisible opt-in offer as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The offer
        describes the segment, lead magnet, channel and advanced audience that will
        run, while the opt-ins or engagement it later produces are separate
        observations, so an offer is never an observation.
        """
        raise InvisibleOptInObservationError(
            f"invisible opt-in offer {claim_id!r} is a plan of a segment, a lead "
            "magnet, a channel and an audience it advances, not an observed "
            "result, and cannot be recorded as an observation"
        )


@dataclass(frozen=True)
class BannerDimension:
    """A banner ad's pixel size (canon files 33, 34).

    The canon's banner ad specs name each ad by its pixel dimensions, and the
    operator uploads one ad per size because the ad network "serves whichever size
    fits" (canon file 34: "each ad has to have its own size" and "you upload any one
    of these sizes"). A dimension is a positive integer width and height, so a
    reference cannot carry an unbounded or non-numeric size.
    """

    width: int
    height: int

    def __post_init__(self) -> None:
        for label, value in (
            ("banner width", self.width),
            ("banner height", self.height),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise InvalidBannerAdError(f"a {label} must be an integer")
            if value < 1:
                raise InvalidBannerAdError(
                    f"a {label} must be positive pixels"
                )

    @property
    def label(self) -> str:
        """The conventional ``WIDTHxHEIGHT`` ad size label."""
        return f"{self.width}x{self.height}"


CANON_DISPLAY_BANNER_DIMENSIONS: tuple[BannerDimension, ...] = (
    BannerDimension(300, 250),
    BannerDimension(728, 90),
)
"""The display banner sizes the canon names as its baseline (canon file 34).

Canon file 34: "I only use the two most common sizes, which is the 3 by 250 and
the 728. You know, this long banner and then square one." The medium rectangle
and leaderboard are the canon's declared starting set; larger sizes are an
acknowledged improvement ("if you're for the same price, you can get like such
huge presence by going with the bigger sizes").
"""

CANON_FACEBOOK_AD_DIMENSION: BannerDimension = BannerDimension(600, 315)
"""The Facebook/Perfect Audience ad image size the canon uses (canon file 34).

Canon file 34 creates the Facebook retargeting ad with the image "600 by 315".
The same 600x315 image is what the canon reuses across its Facebook newsfeed and
right-rail placements, so both Facebook channels require it.
"""

CANON_BANNER_DIMENSIONS: dict[RetargetingChannel, tuple[BannerDimension, ...]] = {
    RetargetingChannel.FACEBOOK_NEWSFEED: (CANON_FACEBOOK_AD_DIMENSION,),
    RetargetingChannel.FACEBOOK_RIGHT_RAIL: (CANON_FACEBOOK_AD_DIMENSION,),
    RetargetingChannel.GOOGLE_DISPLAY: CANON_DISPLAY_BANNER_DIMENSIONS,
}
"""The canon-named dimensions per channel (canon files 33, 34).

Google Display and both Facebook placements are sized by the canon. Twitter is a
retargeting channel the canon names (canon file 33) but does not size in the
supplied material, so it is deliberately absent and recorded as a gap rather than
invented; a reference for it is left to the caller.
"""


@dataclass(frozen=True)
class BannerAdReference:
    """A channel's banner spec and swipe-copy note (SPEC.md 12.5; canon 33, 34).

    Canon file 33 supplies a "banner ad specs and guidelines" reference and
    banner/sidebar swipe files of ads collected from competitors "to give you some
    inspiration", and canon file 34 warns against copying them verbatim ("just
    reverse engineered... to start with, you'd probably crush it" is advice to
    learn, not to clone). The reference records the channel, the dimensions the
    creative must be produced at, and a swipe note describing the observed ads that
    inform the next creative. It generates no creative itself and names no spend.
    """

    reference_id: str
    channel: RetargetingChannel
    dimensions: tuple[BannerDimension, ...]
    swipe_note: str

    def __post_init__(self) -> None:
        if not self.reference_id or not self.reference_id.strip():
            raise InvalidBannerAdError("a banner reference id is required")
        if not isinstance(self.channel, RetargetingChannel):
            raise InvalidBannerAdError(
                "a banner reference requires a named retargeting channel"
            )
        if not isinstance(self.dimensions, tuple) or not self.dimensions:
            raise InvalidBannerAdError(
                "a banner reference must declare at least one pixel dimension; a "
                "banner at no size cannot be produced"
            )
        seen: set[tuple[int, int]] = set()
        for size in self.dimensions:
            if not isinstance(size, BannerDimension):
                raise InvalidBannerAdError(
                    "a banner reference dimension must be a typed BannerDimension, "
                    "not a free-text size label"
                )
            key = (size.width, size.height)
            if key in seen:
                raise InvalidBannerAdError(
                    f"a banner reference repeats the {size.label} size; each "
                    "declared size must be distinct"
                )
            seen.add(key)
        if not self.swipe_note or not self.swipe_note.strip():
            raise InvalidBannerAdError(
                "a banner reference requires a swipe-copy note describing the "
                "observed ads that inform the creative (canon file 33)"
            )

    @property
    def labels(self) -> tuple[str, ...]:
        """The declared sizes as ``WIDTHxHEIGHT`` labels, in declared order."""
        return tuple(size.label for size in self.dimensions)


class BannerAdReferencePolicy:
    """Enforces the canon-named dimensions for a banner reference (canon 34).

    A reference for a channel the canon sizes must declare those sizes, so a
    creative brief cannot target Google Display or a Facebook placement without the
    canon's baseline dimensions. A channel the canon does not size is left to the
    caller and recorded as a gap rather than invented (SPEC.md section 12.4). The
    policy never generates creative or authorizes spend; that remains a named human
    decision (SPEC.md sections 4 and 9).
    """

    @staticmethod
    def require_canon_sizes(reference: BannerAdReference) -> None:
        if not isinstance(reference, BannerAdReference):
            raise InvalidBannerAdError(
                "the canon-size check requires a typed banner reference"
            )
        expected = CANON_BANNER_DIMENSIONS.get(reference.channel)
        if expected is None:
            return
        declared = set(reference.dimensions)
        missing = tuple(size for size in expected if size not in declared)
        if missing:
            labels = ", ".join(size.label for size in missing)
            raise BannerAdCanonSpecError(
                f"banner reference {reference.reference_id!r} for channel "
                f"{reference.channel.value!r} omits the canon size(s) {labels}; the "
                "canon names the sizes this medium must be produced at (canon file "
                "34)"
            )


@dataclass(frozen=True)
class BannerAdReferenceLibrary:
    """The canon's banner-ad spec and swipe library (SPEC.md 12.5; canon 33, 34).

    SPEC.md section 12.5 records the canon's banner-ad specs and swipe file as the
    remaining retargeting-system candidate, and section 4 keeps external spend and
    publishing behind a named human authorization. The library is a tenant-scoped,
    owner-bound static reference of per-channel dimensions and swipe notes that a
    stage 8 funnel integration or stage 10 campaign can consult before producing
    creative. It reports the canon channels it does not yet cover so the gap stays
    visible.

    The library is a reference, not a gate kind and not an authorization to spend:
    producing or publishing the creative and any payment remain named human
    decisions (SPEC.md sections 4 and 9). It is never an observed result; the ad
    performance it later informs is a separate observation (SPEC.md section 3).
    """

    library_id: str
    tenant_id: str
    owner: str
    references: tuple[BannerAdReference, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("banner reference library id", self.library_id),
            ("banner reference library tenant id", self.tenant_id),
            ("banner reference library owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidBannerAdError(f"{label} is required")
        if not isinstance(self.references, tuple) or not self.references:
            raise InvalidBannerAdError(
                "a banner reference library must declare at least one typed "
                "reference; an empty library documents no medium"
            )
        seen: set[RetargetingChannel] = set()
        for reference in self.references:
            if not isinstance(reference, BannerAdReference):
                raise InvalidBannerAdError(
                    "a banner reference library entry must be a typed banner "
                    "reference, not a free-text spec"
                )
            if reference.channel in seen:
                raise InvalidBannerAdError(
                    f"a banner reference library repeats channel "
                    f"{reference.channel.value!r}; each channel is documented once"
                )
            seen.add(reference.channel)

    @property
    def channels(self) -> tuple[RetargetingChannel, ...]:
        """The channels the library documents, in declared order."""
        return tuple(reference.channel for reference in self.references)

    def covers(self, channel: RetargetingChannel) -> bool:
        """Whether the library documents a channel."""
        return any(reference.channel is channel for reference in self.references)

    def specification_for(
        self, channel: RetargetingChannel
    ) -> BannerAdReference | None:
        """The reference for a channel, or ``None`` if it is not documented."""
        for reference in self.references:
            if reference.channel is channel:
                return reference
        return None

    def missing_canon_channels(self) -> tuple[RetargetingChannel, ...]:
        """The canon-sized channels this library does not yet document."""
        return tuple(
            channel
            for channel in CANON_BANNER_DIMENSIONS
            if not self.covers(channel)
        )

    @property
    def is_canon_complete(self) -> bool:
        """Whether every canon-sized channel is documented."""
        return not self.missing_canon_channels()

    @property
    def is_reference(self) -> bool:
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a banner reference library as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The library
        is a static reference of required dimensions and swipe notes, not the ad
        performance it later informs, so it is never an observation.
        """
        raise BannerAdObservationError(
            f"banner reference library {claim_id!r} is a reference of dimensions "
            "and swipe notes, not an observed result, and cannot be recorded as an "
            "observation"
        )


@dataclass(frozen=True)
class AudienceBuildObservation:
    """The canon's content measurement loop for a top-of-funnel audience (SPEC.md
    12.5).

    SPEC.md section 12.5 records the audience-building and content flywheel (canon
    files 25-31) and section 3 names Measurement as the home of "metric definition,
    window, baseline, observation, source", with observations kept distinct from
    causal conclusions. Canon file 30 measures the ten-second-view audience
    campaign by the audience it builds ("22,000 people to advertise to") and by
    the cost per ten-second view ("$0.03 for a 10 second video view"; "under 20
    cents is a really rough metric"), and canon file 23's dashboard tracks the
    "top of funnel audience" of "25,000 people" at "20 cents each".

    The observation binds a named owner to the same-tenant
    ``VideoViewAudienceCampaign`` whose target cost it measures, an explicit closed
    ``MeasurementWindow``, an observed audience size and an observed cost per
    ten-second view. It refuses a blank identity, a non-positive or non-integer
    audience size, a non-positive or non-Decimal cost per view, an untyped or
    cross-tenant campaign, an untyped window or basis, a placeholder basis and a
    result read before its window closed. It exposes ``meets_target_cost`` and its
    inverse ``indicates_topic_problem`` -- canon file 30: if the cost per view "is
    super high. Then you have a problem with the topic. So you can stop it" -- and
    projects to an OBSERVATION ``PerformanceClaim`` rather than a causal
    conclusion.

    It is a stage 10 measurement asset, not a required gate kind (a
    methodology-owner decision), and it never authorizes spend: the campaign and
    any payment remain named human decisions (SPEC.md sections 4 and 9).
    """

    observation_id: str
    tenant_id: str
    owner: str
    campaign: VideoViewAudienceCampaign
    window: MeasurementWindow
    basis: MeasurementBasis
    audience_size: int
    cost_per_view: Decimal
    source: str
    recorded_on: date

    def __post_init__(self) -> None:
        for label, value in (
            ("audience build observation id", self.observation_id),
            ("audience build observation tenant id", self.tenant_id),
            ("audience build observation owner", self.owner),
            ("audience build observation source", self.source),
        ):
            if not value or not value.strip():
                raise InvalidAudienceBuildObservationError(f"{label} is required")
        if not isinstance(self.campaign, VideoViewAudienceCampaign):
            raise AudienceBuildObservationDependencyError(
                "the content measurement loop must observe a typed video view "
                "audience campaign, not a free-text campaign"
            )
        if self.campaign.tenant_id != self.tenant_id:
            raise AudienceBuildObservationTenantBoundaryError(
                f"audience build observation {self.observation_id!r} belongs to "
                f"tenant {self.tenant_id!r}, but its campaign "
                f"{self.campaign.campaign_id!r} belongs to tenant "
                f"{self.campaign.tenant_id!r}"
            )
        if not isinstance(self.window, MeasurementWindow):
            raise AudienceBuildObservationDependencyError(
                "the content measurement loop requires a typed measurement window"
            )
        if not isinstance(self.basis, MeasurementBasis):
            raise AudienceBuildObservationDependencyError(
                "the content measurement loop requires a placeholder or observed "
                "basis"
            )
        if self.basis is not MeasurementBasis.OBSERVED:
            raise AudienceBuildObservationBasisError(
                "the content measurement loop records what actually happened; a "
                "placeholder figure is not a measured audience build (canon files "
                "23 and 24)"
            )
        if not isinstance(self.audience_size, int) or isinstance(
            self.audience_size, bool
        ):
            raise InvalidAudienceBuildObservationError(
                "a built audience size must be an integer"
            )
        if self.audience_size <= 0:
            raise InvalidAudienceBuildObservationError(
                "a built audience size must be positive: an empty audience is not "
                "a built warm audience (canon file 30)"
            )
        if not isinstance(self.cost_per_view, Decimal):
            raise InvalidAudienceBuildObservationError(
                "an observed cost per ten-second view must be a Decimal"
            )
        if self.cost_per_view <= 0:
            raise InvalidAudienceBuildObservationError(
                "an observed cost per ten-second view must be positive"
            )
        if not isinstance(self.recorded_on, date):
            raise InvalidAudienceBuildObservationError(
                "an audience build observation requires the date it was recorded"
            )
        if self.recorded_on < self.window.end:
            raise AudienceBuildObservationWindowOpenError(
                "an audience build observation cannot be read before the window "
                f"it covers has closed: it was recorded on {self.recorded_on} but "
                f"the window ends {self.window.end}"
            )

    @property
    def meets_target_cost(self) -> bool:
        """Whether the observed cost per view is at or below the campaign target."""
        return self.cost_per_view <= self.campaign.target_cost_per_view

    @property
    def indicates_topic_problem(self) -> bool:
        """Whether the observed cost signals a problem with the topic (canon 30)."""
        return not self.meets_target_cost

    def performance_claim(
        self, *, claim_id: str, subject: str | None = None
    ) -> PerformanceClaim:
        """Project the loop onto an OBSERVATION claim (SPEC.md section 3).

        SPEC.md section 3 keeps observations distinct from causal conclusions. The
        projection always yields kind OBSERVATION, carrying the campaign name as
        the subject, the built audience and cost per view as the statement, the
        audience size as the sample, the observation's source and tenant, so a
        stage 10 review reads a typed observed result rather than a conclusion.
        """
        return PerformanceClaim(
            claim_id=claim_id,
            tenant_id=self.tenant_id,
            subject=subject or self.campaign.name,
            statement=(
                f"the audience building campaign built {self.audience_size} "
                f"people at {self.cost_per_view} per ten-second view"
            ),
            kind=ClaimKind.OBSERVATION,
            sample_size=self.audience_size,
            source=self.source,
        )

