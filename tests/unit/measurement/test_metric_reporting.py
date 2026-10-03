"""Behavioral tests for the METRICS reporting projection (Measurement domain).

SPEC.md section 4 requires the production-manager view to "separate eight
reporting dimensions: assets, milestones, checkpoints, metrics, owner,
dependency, status and due date", and Phase 5 requires a metric registry and
observed results. The canon's Metrics Matrix and dashboard discipline (canon
files 22, 23 and 24) solve the funnel by typed metric, so the METRICS dimension
reports each registered metric with its latest observed figure and, where an
approved improvement has been measured, the observed movement between the before
and after windows.

The projection is pure and tenant scoped: a placeholder figure never appears as
a verified metric, an unobserved metric produces no row, and another client's
metric is never projected onto this client's production view.
"""

import unittest
from datetime import date

from redops.contexts.measurement.domain.errors import InvalidMetricReportingError
from redops.contexts.measurement.domain.value_objects import (
    metric_reporting_views,
)

from .fixtures import (
    TENANT,
    approved_improvement,
    measured_improvement,
    measurement_record,
    measurement_window,
    metric_definition,
    placeholder_record,
)


class MetricReportingProjectionTests(unittest.TestCase):
    def test_projects_an_observed_metric_with_its_latest_figure(self):
        rows = metric_reporting_views(
            tenant_id=TENANT,
            metrics=[metric_definition()],
            records=[measurement_record()],
        )

        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("metric-cost-per-lead", row.metric_id)
        self.assertEqual("cost per lead", row.name)
        self.assertEqual("lead", row.funnel_step)
        self.assertEqual("currency", row.unit)
        self.assertEqual("lower_is_better", row.direction)
        self.assertEqual(12.0, row.value)
        self.assertEqual(250, row.sample_size)
        self.assertIsNone(row.movement)

    def test_picks_the_latest_observed_record_by_recorded_on(self):
        older = measurement_record(
            record_id="measure-old",
            value=12.0,
            recorded_on=date(2026, 10, 1),
            window=measurement_window(
                start=date(2026, 9, 1), end=date(2026, 10, 1)
            ),
        )
        newer = measurement_record(
            record_id="measure-new",
            value=9.0,
            recorded_on=date(2026, 10, 3),
            window=measurement_window(
                start=date(2026, 10, 2), end=date(2026, 10, 3)
            ),
        )

        rows = metric_reporting_views(
            tenant_id=TENANT,
            metrics=[metric_definition()],
            records=[older, newer],
        )

        self.assertEqual(9.0, rows[0].value)

    def test_a_placeholder_only_metric_produces_no_verified_row(self):
        rows = metric_reporting_views(
            tenant_id=TENANT,
            metrics=[metric_definition()],
            records=[placeholder_record()],
        )

        self.assertEqual((), rows)

    def test_attaches_the_measured_movement_of_a_measured_improvement(self):
        rows = metric_reporting_views(
            tenant_id=TENANT,
            metrics=[metric_definition()],
            records=[measurement_record()],
            improvements=[measured_improvement()],
        )

        movement = rows[0].movement
        self.assertIsNotNone(movement)
        self.assertEqual("improve-3f", movement.improvement_id)
        self.assertEqual(12.0, movement.before)
        self.assertEqual(8.0, movement.after)

    def test_an_approved_but_unmeasured_improvement_adds_no_movement(self):
        rows = metric_reporting_views(
            tenant_id=TENANT,
            metrics=[metric_definition()],
            records=[measurement_record()],
            improvements=[approved_improvement()],
        )

        self.assertIsNone(rows[0].movement)

    def test_does_not_project_another_tenants_metric(self):
        rows = metric_reporting_views(
            tenant_id=TENANT,
            metrics=[metric_definition(tenant_id="other-client")],
            records=[
                measurement_record(
                    metric=metric_definition(tenant_id="other-client"),
                    tenant_id="other-client",
                )
            ],
        )

        self.assertEqual((), rows)

    def test_requires_a_tenant(self):
        with self.assertRaises(InvalidMetricReportingError):
            metric_reporting_views(tenant_id="  ", metrics=[], records=[])


if __name__ == "__main__":
    unittest.main()
