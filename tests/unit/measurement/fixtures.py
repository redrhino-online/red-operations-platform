"""Shared pure-domain fixtures for Measurement tests.

These build a stage 10 improvement proposal grounded on an established
same-tenant ``PerformanceBaseline``, the named-owner approval that moves it out
of proposal, and a before/after ``ImprovementOutcome``, so tests that exercise
the improvement loop do not restate the same content in every file. They are
test data only and carry no behavior.
"""

from __future__ import annotations

from datetime import date

from redops.contexts.measurement.domain.entities import ImprovementProposal
from redops.contexts.measurement.domain.value_objects import (
    FunnelEconomics,
    FunnelFigure,
    FunnelForecast,
    FunnelMetricRole,
    ImprovementApproval,
    ImprovementOutcome,
    MeasurementBasis,
    MeasurementRecord,
    MeasurementWindow,
    MetricDefinition,
    MetricDirection,
    MetricFunnelStep,
    MetricUnit,
)
from ..execution.fixtures import (
    TODAY,
    established_baseline,
)

TENANT = "client-3f"


def improvement_proposal(baseline=None, **overrides) -> ImprovementProposal:
    values = {
        "proposal_id": "improve-3f",
        "tenant_id": TENANT,
        "baseline": established_baseline() if baseline is None else baseline,
        "metric": metric_definition(),
        "proposed_by": "optimizer-agent",
        "owner": "performance-owner",
        "subject": "cost per lead",
        "lever": "landing page headline",
        "evidence": "evidence://baseline/cost-per-lead-analysis",
        "measurement_plan": "compare cost per lead two weeks before and after",
    }
    values.update(overrides)
    return ImprovementProposal(**values)


def improvement_approval(**overrides) -> ImprovementApproval:
    values = {
        "approved_by": "performance-owner",
        "intended_use": "apply the lever to the live campaign",
        "approved_on": TODAY,
    }
    values.update(overrides)
    return ImprovementApproval(**values)


def approved_improvement(**overrides) -> ImprovementProposal:
    return improvement_proposal(**overrides).approve(
        approval=improvement_approval()
    )


def improvement_outcome(
    metric=None, before=None, after=None, tenant_id=TENANT, **overrides
) -> ImprovementOutcome:
    metric = (
        metric_definition(tenant_id=tenant_id) if metric is None else metric
    )
    values = {
        "outcome_id": "outcome-3f",
        "tenant_id": tenant_id,
        "metric": metric,
        "before": (
            measurement_record(
                metric=metric,
                tenant_id=tenant_id,
                record_id="measure-before-3f",
                value=12.0,
                window=MeasurementWindow(
                    start=date(2026, 9, 18), end=date(2026, 10, 1)
                ),
            )
            if before is None
            else before
        ),
        "after": (
            measurement_record(
                metric=metric,
                tenant_id=tenant_id,
                record_id="measure-after-3f",
                value=8.0,
                window=MeasurementWindow(
                    start=date(2026, 10, 2), end=date(2026, 10, 2)
                ),
            )
            if after is None
            else after
        ),
        "measured_on": TODAY,
        "summary": "cost per lead fell after the headline change",
    }
    values.update(overrides)
    return ImprovementOutcome(**values)


def measured_improvement(**overrides) -> ImprovementProposal:
    return approved_improvement(**overrides).record_outcome(
        outcome=improvement_outcome()
    )


def metric_definition(**overrides) -> MetricDefinition:
    values = {
        "metric_id": "metric-cost-per-lead",
        "tenant_id": TENANT,
        "name": "cost per lead",
        "funnel_step": MetricFunnelStep.LEAD,
        "unit": MetricUnit.CURRENCY,
        "direction": MetricDirection.LOWER_IS_BETTER,
        "version": 1,
    }
    values.update(overrides)
    return MetricDefinition(**values)


def measurement_window(**overrides) -> MeasurementWindow:
    values = {"start": TODAY, "end": TODAY}
    values.update(overrides)
    return MeasurementWindow(**values)


def measurement_record(metric=None, **overrides) -> MeasurementRecord:
    values = {
        "record_id": "measure-3f",
        "tenant_id": TENANT,
        "metric": metric_definition() if metric is None else metric,
        "value": 12.0,
        "window": measurement_window(),
        "basis": MeasurementBasis.OBSERVED,
        "source": "analytics://campaign-report",
        "sample_size": 250,
        "recorded_on": TODAY,
    }
    values.update(overrides)
    return MeasurementRecord(**values)


def placeholder_record(**overrides) -> MeasurementRecord:
    values = {"basis": MeasurementBasis.PLACEHOLDER, "sample_size": 0}
    values.update(overrides)
    return measurement_record(**values)


_FUNNEL_ROLE_SHAPES = {
    FunnelMetricRole.ANNUAL_CUSTOMER_VALUE: (
        "metric-annual-customer-value",
        "annual customer value",
        MetricFunnelStep.CUSTOMER,
        MetricUnit.CURRENCY,
        MetricDirection.HIGHER_IS_BETTER,
    ),
    FunnelMetricRole.LEAD_BOOKING_RATE: (
        "metric-lead-booking-rate",
        "lead booking rate",
        MetricFunnelStep.LEAD,
        MetricUnit.PERCENT,
        MetricDirection.HIGHER_IS_BETTER,
    ),
    FunnelMetricRole.SESSION_SHOW_RATE: (
        "metric-session-show-rate",
        "session show rate",
        MetricFunnelStep.APPOINTMENT,
        MetricUnit.PERCENT,
        MetricDirection.HIGHER_IS_BETTER,
    ),
    FunnelMetricRole.SESSION_CLOSE_RATE: (
        "metric-session-close-rate",
        "session close rate",
        MetricFunnelStep.APPOINTMENT,
        MetricUnit.PERCENT,
        MetricDirection.HIGHER_IS_BETTER,
    ),
}


def funnel_metric(role, **overrides) -> MetricDefinition:
    metric_id, name, step, unit, direction = _FUNNEL_ROLE_SHAPES[role]
    values = {
        "metric_id": metric_id,
        "tenant_id": TENANT,
        "name": name,
        "funnel_step": step,
        "unit": unit,
        "direction": direction,
        "version": 1,
    }
    values.update(overrides)
    return MetricDefinition(**values)


def funnel_figure(role, metric=None, **overrides) -> FunnelFigure:
    defaults = {
        FunnelMetricRole.ANNUAL_CUSTOMER_VALUE: (10000.0, MeasurementBasis.OBSERVED),
        FunnelMetricRole.LEAD_BOOKING_RATE: (5.0, MeasurementBasis.OBSERVED),
        FunnelMetricRole.SESSION_SHOW_RATE: (100.0, MeasurementBasis.OBSERVED),
        FunnelMetricRole.SESSION_CLOSE_RATE: (25.0, MeasurementBasis.OBSERVED),
    }
    value, basis = defaults[role]
    values = {
        "role": role,
        "metric": funnel_metric(role) if metric is None else metric,
        "value": value,
        "basis": basis,
        "source": "plan://funnel-metrics",
    }
    values.update(overrides)
    return FunnelFigure(**values)


def funnel_economics(**overrides) -> FunnelEconomics:
    values = {
        "tenant_id": TENANT,
        "annual_customer_value": funnel_figure(
            FunnelMetricRole.ANNUAL_CUSTOMER_VALUE
        ),
        "lead_booking_rate": funnel_figure(FunnelMetricRole.LEAD_BOOKING_RATE),
        "session_show_rate": funnel_figure(FunnelMetricRole.SESSION_SHOW_RATE),
        "session_close_rate": funnel_figure(
            FunnelMetricRole.SESSION_CLOSE_RATE
        ),
    }
    values.update(overrides)
    return FunnelEconomics(**values)


def funnel_forecast(**overrides) -> FunnelForecast:
    values = {
        "tenant_id": TENANT,
        "economics": funnel_economics(),
        "ad_spend": 5000.0,
        "cost_per_lead": 5.0,
    }
    values.update(overrides)
    return FunnelForecast(**values)
