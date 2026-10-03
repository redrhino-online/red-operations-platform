"""Behavioral tests for the stage 10 metric registry (Measurement domain).

Rules under test come from SPEC.md section 3 (Measurement aggregate: "metric
definition, window, baseline, observation, source"; the Measurement invariant
that "observations are distinct from causal conclusions") and Phase 5 ("metric
registry, event instrumentation, observations and experiment records"), shaped by
the canon's Metrics Matrix and dashboard discipline (canon files 23 and 24):

- A metric is typed by its funnel step, unit, direction and version, so an
  observation pins an exact metric.
- An observation carries an explicit window, basis, source, value and sample.
- A metric is tenant scoped, and an observation cannot cite another tenant's
  metric.
- A placeholder figure is not an observation, and a placeholder-only series
  cannot serve as a baseline; a sample below the caller's minimum is too small.
- A record is written only once the window it covers has closed, so a
  still-open result window cannot enter the registry or ground any baseline
  (canon file 24: "I wait 10 days to see how it does"; "don't touch anything for
  10 days").
- A measurement can be projected to an OBSERVATION claim, never a causal
  conclusion.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.measurement.domain.errors import (
    InvalidMeasurementRecordError,
    InvalidMetricDefinitionError,
    InvalidMetricWindowError,
    MeasurementTenantBoundaryError,
    MeasurementWindowOpenError,
    MetricBaselineNotObservedError,
    MetricSampleTooSmallError,
)
from redops.contexts.measurement.domain.policies import MetricBaselinePolicy
from redops.contexts.measurement.domain.value_objects import (
    MeasurementWindow,
    MetricDirection,
    MetricFunnelStep,
    MetricUnit,
)
from redops.contexts.execution.domain.value_objects import ClaimKind
from redops.contexts.execution.domain.errors import InvalidPerformanceClaimError

from ..execution.fixtures import TODAY
from .fixtures import (
    measurement_record,
    measurement_window,
    metric_definition,
    placeholder_record,
)


class MetricDefinitionTests(unittest.TestCase):
    def test_a_valid_definition_keeps_its_type_and_version(self):
        metric = metric_definition()

        self.assertEqual("cost per lead", metric.name)
        self.assertIs(MetricFunnelStep.LEAD, metric.funnel_step)
        self.assertIs(MetricUnit.CURRENCY, metric.unit)
        self.assertIs(MetricDirection.LOWER_IS_BETTER, metric.direction)
        self.assertEqual(1, metric.version)

    def test_a_definition_requires_identity_tenant_and_name(self):
        for field in ("metric_id", "tenant_id", "name"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidMetricDefinitionError):
                    metric_definition(**{field: "  "})

    def test_a_definition_version_must_be_a_positive_integer(self):
        for version in (0, -1, "1", True):
            with self.subTest(version=version):
                with self.assertRaises(InvalidMetricDefinitionError):
                    metric_definition(version=version)

    def test_a_definition_requires_a_funnel_step_unit_and_direction(self):
        with self.assertRaises(InvalidMetricDefinitionError):
            metric_definition(funnel_step="lead")
        with self.assertRaises(InvalidMetricDefinitionError):
            metric_definition(unit="dollars")
        with self.assertRaises(InvalidMetricDefinitionError):
            metric_definition(direction="up")

    def test_a_definition_is_immutable(self):
        metric = metric_definition()

        with self.assertRaises(FrozenInstanceError):
            metric.name = "tampered"


class MeasurementWindowTests(unittest.TestCase):
    def test_a_window_requires_dates_in_order(self):
        with self.assertRaises(InvalidMetricWindowError):
            measurement_window(start=TODAY, end=date(2020, 1, 1))

    def test_a_window_requires_date_objects(self):
        with self.assertRaises(InvalidMetricWindowError):
            measurement_window(start="2026-10-03", end=TODAY)


class MeasurementRecordTests(unittest.TestCase):
    def test_an_observed_record_reports_its_value_window_and_source(self):
        record = measurement_record()

        self.assertTrue(record.is_observed)
        self.assertFalse(record.is_placeholder)
        self.assertEqual(12.0, record.value)
        self.assertEqual(250, record.sample_size)
        self.assertEqual("analytics://campaign-report", record.source)

    def test_a_placeholder_record_is_not_an_observation(self):
        record = placeholder_record()

        self.assertTrue(record.is_placeholder)
        self.assertFalse(record.is_observed)

    def test_a_record_requires_identity_tenant_and_source(self):
        for field in ("record_id", "tenant_id", "source"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidMeasurementRecordError):
                    measurement_record(**{field: "  "})

    def test_a_record_value_must_be_a_real_number(self):
        for value in ("12", None, True):
            with self.subTest(value=value):
                with self.assertRaises(InvalidMeasurementRecordError):
                    measurement_record(value=value)

    def test_a_record_sample_size_cannot_be_negative(self):
        with self.assertRaises(InvalidMeasurementRecordError):
            measurement_record(sample_size=-1)

    def test_a_record_cannot_cite_another_tenants_metric(self):
        foreign = metric_definition(metric_id="metric-foreign", tenant_id="other")

        with self.assertRaises(MeasurementTenantBoundaryError):
            measurement_record(metric=foreign)

    def test_a_record_requires_a_measurement_window(self):
        with self.assertRaises(InvalidMeasurementRecordError):
            measurement_record(window="last week")

    def test_a_record_cannot_be_recorded_before_its_window_closes(self):
        with self.assertRaises(MeasurementWindowOpenError):
            measurement_record(
                window=MeasurementWindow(
                    start=date(2026, 10, 2), end=date(2026, 10, 9)
                ),
                recorded_on=date(2026, 10, 2),
            )

    def test_a_record_may_be_recorded_on_the_day_its_window_closes(self):
        record = measurement_record(
            window=MeasurementWindow(
                start=date(2026, 10, 2), end=date(2026, 10, 5)
            ),
            recorded_on=date(2026, 10, 5),
        )

        self.assertEqual(date(2026, 10, 5), record.window.end)
        self.assertEqual(date(2026, 10, 5), record.recorded_on)

    def test_the_default_record_is_written_after_its_window_closes(self):
        record = measurement_record()

        self.assertGreaterEqual(record.recorded_on, record.window.end)

    def test_a_record_is_immutable(self):
        record = measurement_record()

        with self.assertRaises(FrozenInstanceError):
            record.value = 0.0

    def test_a_record_projects_to_an_observation_claim(self):
        record = measurement_record()

        claim = record.as_observation(
            claim_id="claim-cost-per-lead", baseline_id="baseline-3f"
        )

        self.assertIs(ClaimKind.OBSERVATION, claim.kind)
        self.assertEqual(record.metric.name, claim.subject)
        self.assertEqual(record.sample_size, claim.sample_size)
        self.assertEqual(record.source, claim.source)
        self.assertEqual(record.tenant_id, claim.tenant_id)
        self.assertEqual("baseline-3f", claim.baseline_id)

    def test_the_projected_observation_keeps_its_typed_value(self):
        claim = measurement_record().as_observation(claim_id="claim-1")

        self.assertIn("cost per lead", claim.statement)
        self.assertIn("12.0", claim.statement)
        self.assertIn("currency", claim.statement)

    def test_a_projected_observation_requires_a_claim_identity(self):
        with self.assertRaises(InvalidPerformanceClaimError):
            measurement_record().as_observation(claim_id="  ")


class MetricBaselinePolicyTests(unittest.TestCase):
    def setUp(self):
        self.metric = metric_definition()
        self.policy = MetricBaselinePolicy()

    def test_a_placeholder_only_series_cannot_establish_a_baseline(self):
        records = [placeholder_record(record_id="plan-1")]

        with self.assertRaises(MetricBaselineNotObservedError):
            self.policy.require(self.metric, records)

    def test_an_observed_record_establishes_the_baseline(self):
        baseline = measurement_record()

        selected = self.policy.require(self.metric, [baseline])

        self.assertIs(baseline, selected)

    def test_another_metrics_observations_are_ignored(self):
        other = metric_definition(metric_id="metric-lead-volume")
        records = [measurement_record(metric=other)]

        with self.assertRaises(MetricBaselineNotObservedError):
            self.policy.require(self.metric, records)

    def test_an_observed_sample_below_the_minimum_is_refused(self):
        records = [measurement_record(sample_size=4)]

        with self.assertRaises(MetricSampleTooSmallError):
            self.policy.require(self.metric, records, minimum_sample=100)

    def test_the_newest_adequate_observed_record_is_selected(self):
        older = measurement_record(record_id="measure-old", recorded_on=TODAY)
        newer = measurement_record(
            record_id="measure-new", value=8.0, recorded_on=date(2026, 10, 10)
        )
        placeholder = placeholder_record(record_id="plan-1")

        selected = self.policy.require(
            self.metric, [older, placeholder, newer], minimum_sample=100
        )

        self.assertIs(newer, selected)

    def test_a_metric_with_no_records_has_no_baseline(self):
        with self.assertRaises(MetricBaselineNotObservedError):
            self.policy.require(self.metric, [])


if __name__ == "__main__":
    unittest.main()
