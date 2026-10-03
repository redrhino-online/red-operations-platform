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
    ImprovementObservationError,
    ImprovementResultWindowOpenError,
    InvalidImprovementError,
    InvalidImprovementOutcomeError,
    InvalidMeasurementRecordError,
    InvalidMetricDefinitionError,
    InvalidMetricWindowError,
    MeasurementTenantBoundaryError,
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
