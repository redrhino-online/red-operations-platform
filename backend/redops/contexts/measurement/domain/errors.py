"""Named domain errors for the Measurement bounded context (pure domain)."""

from __future__ import annotations


class MeasurementError(Exception):
    """Base class for measurement domain rule violations."""


class InvalidImprovementError(MeasurementError, ValueError):
    """An ImprovementProposal, ImprovementApproval or their fields are invalid.

    SPEC.md section 4: a performance recommendation carries evidence, a named
    accountable owner and the single lever to change. A proposal that leaves any
    of its identification fields (proposal, proposer, owner, subject, lever,
    evidence, measurement plan) unspecified cannot be a reviewable improvement.
    """


class InvalidImprovementOutcomeError(MeasurementError, ValueError):
    """An ImprovementOutcome violates an invariant.

    SPEC.md section 3, Measurement invariant: observations are distinct from
    causal conclusions. The recorded before-and-after is an observed movement,
    so its before and after must be observations of the same subject for the same
    tenant; a causal conclusion is a separate claim that an established baseline
    and an adequate sample must support.
    """


class ImprovementObservationError(MeasurementError, ValueError):
    """An improvement outcome is not grounded on typed observed measurements.

    SPEC.md section 3, Measurement aggregate is "metric definition, window,
    baseline, observation, source" and its invariant keeps observations distinct
    from causal conclusions. The canon's optimization discipline (canon files 23
    and 24) warns that placeholder figures are not real metrics until measured
    over enough instances and waits before reading how a change performed, so the
    before-and-after of a measured improvement must be observed
    ``MeasurementRecord`` values attached to the improvement's metric over an
    explicit window, not free-text statements or placeholder figures, and the
    before window must end before the after window starts.
    """


class ImprovementApprovalPrecedenceError(MeasurementError):
    """An improvement is approved before its baseline was established.

    SPEC.md section 4, stage 10 grounds an improvement on an established
    ``PerformanceBaseline`` and requires owner approval before a material change.
    The canon's optimization discipline (canon files 23 and 24: "you need a
    baseline of metrics" before optimizing; "I wait 10 days to see how it does"
    after authorizing a change) requires the baseline to exist before a change is
    authorized, so an approval whose ``approved_on`` date falls before the
    ``established_on`` date of the baseline it optimizes is refused: the change
    would be authorized before the very baseline it is measured against existed.
    """


class ImprovementObservationWindowError(MeasurementError):
    """An outcome reads its after window before the owner approved the change.

    SPEC.md section 4: a performance recommendation requires owner approval
    before a material change, and only then is the change applied and its result
    read. The canon's optimization discipline (canon files 23 and 24: "I wait 10
    days to see how it does"; "don't touch anything for 10 days") starts the
    result window after the authorized change, so an after observation window
    cannot begin before the improvement's approval date. The before window, which
    is the baseline period, may precede the approval.
    """


class ImprovementBeforeWindowError(MeasurementError):
    """An outcome reads its before window past the owner's approval of the change.

    SPEC.md section 4: "performance recommendations require evidence and owner
    approval before material changes", so the before measurement is a pre-change
    state and must not be observed over a period that extends beyond the
    authorization of the change. The canon's optimization discipline (canon files
    23 and 24: "you need a baseline of metrics" before optimizing; "I wait 10 days
    to see how it does" after authorizing a change) treats the before window as
    the established baseline period, so it must close on or before the improvement
    approval date. A before window that closes after the approval would record a
    period already affected by the authorized change as the pre-change measurement.
    """


class ImprovementResultWindowOpenError(MeasurementError):
    """An outcome is measured before its own result window has closed.

    SPEC.md section 3 keys a MeasurementRecord by its window and keeps
    observations distinct from causal conclusions, and SPEC.md section 4, stage
    10 with Phase 5 reads the observed result only after the optimization has
    run. The canon's optimization discipline (canon files 23 and 24: "I wait 10
    days to see how it does"; "don't touch anything for 10 days") does not read
    a result until the window it is measured over has elapsed, so an outcome
    whose ``measured_on`` date falls before its after observation window has
    closed is refused: the result period is still open, so the movement has not
    yet been observed over a complete window.
    """


class ImprovementDependencyError(MeasurementError):
    """An improvement is not grounded on an established same-tenant baseline.

    SPEC.md section 4, stage 10: optimization continues after "Performance
    Baseline Established", so a proposal or outcome cannot be grounded on a
    draft, review-required or another client's baseline.
    """


class ImprovementMetricError(MeasurementError, ValueError):
    """An improvement is not grounded on a registered, versioned metric.

    SPEC.md section 3 keys a Measurement aggregate by its metric definition and
    Phase 5 requires a metric registry, so an optimization cannot be proposed or
    measured against a free-text metric. A proposal or outcome whose metric is
    missing, untyped or whose subject disagrees with the registered metric name
    cannot be a typed stage 10 improvement.
    """


class ImprovementMetricBoundaryError(MeasurementError):
    """An improvement cites another tenant's registered metric.

    SPEC.md section 3: every tenant resource carries a tenant id and a query is
    tenant scoped, so an improvement cannot be grounded on a metric owned by a
    different client.
    """


class ImprovementMetricMismatchError(MeasurementError):
    """An outcome measures against a metric other than the approved one.

    SPEC.md section 4: a passing gate pins the exact evidence and intended use,
    so a measured improvement must use the exact metric identity and version its
    proposal was approved against, not a redefined or different metric.
    """


class ImprovementAuthorityError(MeasurementError):
    """An improvement was not approved by its named human owner.

    SPEC.md section 4: performance recommendations require owner approval before
    material changes, and an agent cannot confer human approval upon itself, so
    the proposer cannot also be the approving owner.
    """


class ImprovementStateError(MeasurementError):
    """A lifecycle transition was attempted from an illegal improvement state.

    SPEC.md section 4: reject illegal transitions rather than silently coercing
    state. A rejected proposal cannot be approved, and an approved proposal
    cannot be approved twice.
    """


class ImprovementNotApprovedError(MeasurementError):
    """An improvement was measured before its owner approved it.

    SPEC.md section 4: an unapproved recommendation cannot be used to authorize
    production or traffic, so only an approved improvement can be measured.
    """


class ImprovementOutcomeSupportError(MeasurementError):
    """A recorded outcome is not grounded on the proposal's own baseline.

    SPEC.md sections 3 and 4: a passing stage pins the exact evidence and
    intended use, so the before-and-after outcome must belong to the same tenant
    and cite the same performance baseline the improvement was approved against.
    """


class InvalidMetricDefinitionError(MeasurementError, ValueError):
    """A MetricDefinition violates an invariant.

    SPEC.md section 3: a MeasurementRecord is keyed by a "metric definition,
    window, baseline, observation, source". A registry metric that leaves its
    identity, tenant or name unspecified, or carries no unit, direction or
    positive version, cannot be the typed reference an observation attaches to.
    """


class InvalidMetricWindowError(MeasurementError, ValueError):
    """A MeasurementWindow violates an invariant.

    SPEC.md section 3: every observation is scoped to a window. A window whose
    end precedes its start, or that is not a pair of dates, cannot bound a
    measurement.
    """


class InvalidMeasurementRecordError(MeasurementError, ValueError):
    """A MeasurementRecord violates an invariant.

    SPEC.md section 3, Measurement invariant: observations are distinct from
    causal conclusions. A record names the metric, the value, the window, the
    basis and the source, so a record missing any of these, or attaching a value
    or sample that is not a real number, cannot be a grounded observation.
    """


class MeasurementWindowOpenError(MeasurementError):
    """A MeasurementRecord is written before the window it covers has closed.

    SPEC.md section 3 keys a MeasurementRecord by its window and keeps
    observations distinct from causal conclusions, so a record describes a
    period that has been observed. The canon's optimization discipline (canon
    files 23 and 24: "I wait 10 days to see how it does"; "don't touch anything
    for 10 days") does not read a result until the period it is measured over has
    elapsed, so a record whose ``recorded_on`` date falls before its window end
    is refused: the window is still open, so its figure cannot yet be a real
    observation and cannot ground a baseline or a movement.
    """


class MeasurementTenantBoundaryError(MeasurementError):
    """A measurement record cites another tenant's metric definition.

    SPEC.md section 3: every tenant resource carries a tenant id and a query is
    tenant scoped. An observation cannot attach to a metric owned by a different
    client.
    """


class MetricBaselineNotObservedError(MeasurementError):
    """A metric has no observed measurement to serve as a baseline.

    SPEC.md section 4, stage 10 and the canon's optimization discipline (canon
    files 23 and 24): optimization starts only once a baseline of metrics exists,
    and placeholder figures are not real metrics until measured over enough
    instances. A placeholder-only series cannot establish a baseline.
    """


class MetricSampleTooSmallError(MeasurementError):
    """An observed metric has too small a sample to serve as a baseline.

    The canon (canon files 23 and 24) warns that a percentage from too few leads
    is irrelevant and that placeholder inputs should not change until real
    metrics accumulate over many instances, so a baseline requires an observed
    sample at or above the caller-supplied minimum.
    """
