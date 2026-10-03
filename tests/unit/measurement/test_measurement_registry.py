"""Behavioral tests for the measurement registry store (Measurement application).

Rules under test come from SPEC.md sections 3, 4 and 9:
- A Measurement aggregate is "metric definition, window, baseline, observation,
  source" and keys an observation by an exact versioned metric; a metric
  definition version and a recorded observation are therefore append-only, and a
  same-key re-statement with different content is refused (sections 3 and 4).
- A measurement is a client resource: every read and write carries ``tenant_id``,
  and one client's registry cannot be read for another (sections 3 and 9).
- Source attribution survives a reload, so a stored metric keeps its typed funnel
  step, unit and direction and a stored observation keeps its window, basis and
  sample (section 11).

The durable PostgreSQL case skips cleanly when no psycopg, alembic or
``DATABASE_URL`` is present:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/measurement/test_measurement_registry.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from datetime import date
from pathlib import Path

from redops.contexts.measurement.domain.errors import (
    InvalidMeasurementRecordError,
    InvalidMetricDefinitionError,
    MeasurementConflictError,
    MeasurementTenantBoundaryError,
    MeasurementWindowOpenError,
    UnscopedMeasurementError,
)
from redops.contexts.measurement.domain.value_objects import (
    MeasurementBasis,
    MeasurementRecord,
    MeasurementWindow,
    MetricDefinition,
    MetricDirection,
    MetricFunnelStep,
    MetricUnit,
)
from redops.contexts.measurement.infrastructure.mappers import (
    metric_from_payload,
    metric_to_payload,
    record_from_payload,
    record_to_payload,
)
from redops.contexts.measurement.infrastructure.repositories import (
    InMemoryMeasurementRegistry,
)

TENANT = "3fmindset"
OTHER_TENANT = "client-other"

DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL adapter test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)


def metric(
    metric_id: str = "metric-cpl",
    tenant_id: str = TENANT,
    name: str = "cost per lead",
    version: int = 1,
) -> MetricDefinition:
    return MetricDefinition(
        metric_id=metric_id,
        tenant_id=tenant_id,
        name=name,
        funnel_step=MetricFunnelStep.LEAD,
        unit=MetricUnit.CURRENCY,
        direction=MetricDirection.LOWER_IS_BETTER,
        version=version,
    )


def record(
    record_id: str = "record-1",
    tenant_id: str = TENANT,
    definition: MetricDefinition | None = None,
    basis: MeasurementBasis = MeasurementBasis.OBSERVED,
    window: MeasurementWindow | None = None,
    recorded_on: date = date(2026, 10, 20),
) -> MeasurementRecord:
    return MeasurementRecord(
        record_id=record_id,
        tenant_id=tenant_id,
        metric=definition if definition is not None else metric(),
        value=12.5,
        window=window
        if window is not None
        else MeasurementWindow(start=date(2026, 10, 1), end=date(2026, 10, 10)),
        basis=basis,
        source="facebook ads manager export",
        sample_size=120,
        recorded_on=recorded_on,
    )


class InMemoryMeasurementRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = InMemoryMeasurementRegistry()

    def test_a_saved_metric_is_resolved_by_tenant_and_version(self) -> None:
        self.registry.save_metric(metric(version=1))
        self.registry.save_metric(metric(version=2))

        self.assertEqual(2, len(self.registry.list_metrics(TENANT)))
        self.assertIsNotNone(self.registry.get_metric(TENANT, "metric-cpl", 2))
        self.assertIsNone(self.registry.get_metric(TENANT, "metric-cpl", 3))

    def test_a_metric_is_not_visible_to_another_tenant(self) -> None:
        self.registry.save_metric(metric())

        self.assertEqual((), self.registry.list_metrics(OTHER_TENANT))
        self.assertIsNone(self.registry.get_metric(OTHER_TENANT, "metric-cpl", 1))

    def test_a_blank_tenant_is_refused_on_read(self) -> None:
        with self.assertRaises(UnscopedMeasurementError):
            self.registry.list_metrics("  ")
        with self.assertRaises(UnscopedMeasurementError):
            self.registry.get_metric("", "metric-cpl", 1)

    def test_a_blank_tenant_metric_cannot_be_constructed(self) -> None:
        with self.assertRaises(InvalidMetricDefinitionError):
            metric(tenant_id="")

    def test_the_same_metric_version_cannot_be_redefined(self) -> None:
        self.registry.save_metric(metric(name="cost per lead"))

        with self.assertRaises(MeasurementConflictError):
            self.registry.save_metric(metric(name="cost per acquisition"))

    def test_an_identical_metric_replay_is_idempotent(self) -> None:
        self.registry.save_metric(metric())
        self.registry.save_metric(metric())

        self.assertEqual(1, len(self.registry.list_metrics(TENANT)))

    def test_a_saved_record_is_resolved_by_tenant(self) -> None:
        self.registry.save_record(record())

        stored = self.registry.get_record(TENANT, "record-1")

        self.assertIsNotNone(stored)
        self.assertEqual(12.5, stored.value)
        self.assertTrue(stored.is_observed)

    def test_a_record_is_not_visible_to_another_tenant(self) -> None:
        self.registry.save_record(record())

        self.assertEqual((), self.registry.list_records(OTHER_TENANT))
        self.assertIsNone(self.registry.get_record(OTHER_TENANT, "record-1"))

    def test_a_blank_tenant_is_refused_for_records(self) -> None:
        with self.assertRaises(UnscopedMeasurementError):
            self.registry.list_records("")
        with self.assertRaises(InvalidMeasurementRecordError):
            record(tenant_id="")

    def test_the_same_record_id_cannot_be_restated(self) -> None:
        self.registry.save_record(record())
        changed = MeasurementRecord(
            record_id="record-1",
            tenant_id=TENANT,
            metric=metric(),
            value=99.0,
            window=MeasurementWindow(
                start=date(2026, 10, 1), end=date(2026, 10, 10)
            ),
            basis=MeasurementBasis.OBSERVED,
            source="facebook ads manager export",
            sample_size=120,
            recorded_on=date(2026, 10, 20),
        )

        with self.assertRaises(MeasurementConflictError):
            self.registry.save_record(changed)

    def test_an_identical_record_replay_is_idempotent(self) -> None:
        self.registry.save_record(record())
        self.registry.save_record(record())

        self.assertEqual(1, len(self.registry.list_records(TENANT)))

    def test_a_record_cannot_attach_to_another_tenants_metric(self) -> None:
        with self.assertRaises(MeasurementTenantBoundaryError):
            record(definition=metric(tenant_id=OTHER_TENANT))

    def test_a_record_cannot_be_written_before_its_window_closed(self) -> None:
        with self.assertRaises(MeasurementWindowOpenError):
            record(recorded_on=date(2026, 10, 5))

    def test_the_payloads_round_trip_through_the_mappers(self) -> None:
        definition = metric(version=3)
        observation = record(definition=definition, basis=MeasurementBasis.PLACEHOLDER)

        self.assertEqual(
            definition, metric_from_payload(metric_to_payload(definition))
        )
        self.assertEqual(
            observation,
            record_from_payload(record_to_payload(observation)),
        )
        self.assertFalse(
            record_from_payload(record_to_payload(observation)).is_observed
        )


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresMeasurementRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        from redops.contexts.measurement.infrastructure.repositories import (
            PostgresMeasurementRegistry,
        )

        self.psycopg = importlib.import_module("psycopg")
        self.run_migrations = importlib.import_module(
            "redops.shared.persistence.migrate"
        ).run_migrations
        self.run_migrations(DATABASE_URL)
        self.registry = PostgresMeasurementRegistry(
            self.psycopg.connect(DATABASE_URL)
        )

    def tearDown(self) -> None:
        with self.psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM measurement_records WHERE tenant_id IN (%s, %s)",
                    (TENANT, OTHER_TENANT),
                )
                cursor.execute(
                    "DELETE FROM metric_definitions WHERE tenant_id IN (%s, %s)",
                    (TENANT, OTHER_TENANT),
                )
        self.registry.close()

    def test_a_metric_and_observation_survive_a_reload(self) -> None:
        definition = metric(version=4)
        self.registry.save_metric(definition)
        self.registry.save_record(record(definition=definition))

        self.assertEqual(
            definition, self.registry.get_metric(TENANT, "metric-cpl", 4)
        )
        stored = self.registry.get_record(TENANT, "record-1")
        self.assertIsNotNone(stored)
        self.assertEqual(definition, stored.metric)

    def test_a_metric_is_not_visible_to_another_tenant(self) -> None:
        self.registry.save_metric(metric())

        self.assertIsNone(
            self.registry.get_metric(OTHER_TENANT, "metric-cpl", 1)
        )
        self.assertEqual((), self.registry.list_records(OTHER_TENANT))

    def test_a_metric_version_redefinition_is_refused(self) -> None:
        self.registry.save_metric(metric(name="cost per lead"))

        with self.assertRaises(MeasurementConflictError):
            self.registry.save_metric(metric(name="renamed"))

    def test_a_record_restatement_is_refused(self) -> None:
        self.registry.save_record(record())

        with self.assertRaises(MeasurementConflictError):
            self.registry.save_record(
                MeasurementRecord(
                    record_id="record-1",
                    tenant_id=TENANT,
                    metric=metric(),
                    value=1.0,
                    window=MeasurementWindow(
                        start=date(2026, 10, 1), end=date(2026, 10, 10)
                    ),
                    basis=MeasurementBasis.OBSERVED,
                    source="other",
                    sample_size=1,
                    recorded_on=date(2026, 10, 20),
                )
            )

    def test_a_blank_tenant_is_refused(self) -> None:
        with self.assertRaises(UnscopedMeasurementError):
            self.registry.list_metrics("")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
