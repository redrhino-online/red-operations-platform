"""HTTP-boundary behavioral tests for the measurement route (SPEC.md section 7).

SPEC.md section 7 lists ``/measurements``; section 9 requires every tenant
resource query to carry ``tenant_id`` and every list endpoint to enforce client
access and pagination; sections 3 and 4 key an observation by an exact versioned
metric and keep it append-only, distinct from a causal conclusion. These tests
drive the real FastAPI app against a fresh in-memory registry (substituted
through the overridable dependency), so an observation cannot be read under
another tenant, a record written before its window closed is refused, and a
same-key restatement is a conflict rather than a silent rewrite.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest

TENANT = "3fmindset"
OTHER_TENANT = "client-other"


class MeasurementsRouteTests(unittest.TestCase):
    """The measurement surface is served only through the registry seam."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import get_measurement_registry
            from redops.contexts.measurement.infrastructure.repositories import (
                InMemoryMeasurementRegistry,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.registry_dependency = staticmethod(get_measurement_registry)
        cls.registry_class = staticmethod(InMemoryMeasurementRegistry)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.registry = self.registry_class()
        self.app.dependency_overrides[self.registry_dependency] = (
            lambda: self.registry
        )
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def metric_body(**overrides):
        body = {
            "metric_id": "metric-cpl",
            "tenant_id": TENANT,
            "name": "cost per lead",
            "funnel_step": "lead",
            "unit": "currency",
            "direction": "lower_is_better",
            "version": 1,
        }
        body.update(overrides)
        return body

    @classmethod
    def record_body(cls, **overrides):
        body = {
            "record_id": "record-1",
            "tenant_id": TENANT,
            "metric": cls.metric_body(),
            "value": 12.5,
            "window": {"start": "2026-10-01", "end": "2026-10-10"},
            "basis": "observed",
            "source": "facebook ads manager export",
            "sample_size": 120,
            "recorded_on": "2026-10-20",
        }
        body.update(overrides)
        return body

    def test_a_recorded_observation_is_listed_for_its_tenant(self) -> None:
        created = self.client.post("/red/measurements", json=self.record_body())

        self.assertEqual(201, created.status_code, created.text)
        self.assertEqual("record-1", created.json()["record_id"])
        self.assertTrue(created.json()["is_observed"])
        self.assertEqual("metric-cpl", created.json()["metric"]["metric_id"])

        listed = self.client.get(
            "/red/measurements", params={"tenant_id": TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        body = listed.json()
        self.assertEqual(1, body["total"])
        self.assertEqual("record-1", body["records"][0]["record_id"])

    def test_a_record_is_not_listed_for_another_client(self) -> None:
        self.client.post("/red/measurements", json=self.record_body())

        listed = self.client.get(
            "/red/measurements", params={"tenant_id": OTHER_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["records"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get("/red/measurements")

        self.assertEqual(422, response.status_code, response.text)

    def test_a_placeholder_observation_is_recorded_but_not_observed(self) -> None:
        response = self.client.post(
            "/red/measurements", json=self.record_body(basis="placeholder")
        )

        self.assertEqual(201, response.status_code, response.text)
        self.assertFalse(response.json()["is_observed"])

    def test_a_record_before_its_window_closed_is_refused(self) -> None:
        response = self.client.post(
            "/red/measurements", json=self.record_body(recorded_on="2026-10-05")
        )

        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual(
            "MeasurementWindowOpenError", response.json()["detail"]["error"]
        )

    def test_a_record_citing_another_tenants_metric_is_refused(self) -> None:
        response = self.client.post(
            "/red/measurements",
            json=self.record_body(
                tenant_id=TENANT,
                metric=self.metric_body(tenant_id=OTHER_TENANT),
            ),
        )

        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual(
            "MeasurementTenantBoundaryError",
            response.json()["detail"]["error"],
        )

    def test_a_same_record_restatement_is_a_conflict(self) -> None:
        self.client.post("/red/measurements", json=self.record_body())

        response = self.client.post(
            "/red/measurements", json=self.record_body(value=99.0)
        )

        self.assertEqual(409, response.status_code, response.text)
        self.assertEqual(
            "MeasurementConflictError", response.json()["detail"]["error"]
        )

    def test_an_identical_record_replay_is_idempotent(self) -> None:
        first = self.client.post("/red/measurements", json=self.record_body())
        second = self.client.post("/red/measurements", json=self.record_body())

        self.assertEqual(201, first.status_code, first.text)
        self.assertEqual(201, second.status_code, second.text)

        listed = self.client.get(
            "/red/measurements", params={"tenant_id": TENANT}
        )
        self.assertEqual(1, listed.json()["total"])

    def test_measurement_pagination_is_applied_after_tenant_scoping(self) -> None:
        for index in range(3):
            self.client.post(
                "/red/measurements",
                json=self.record_body(
                    record_id=f"record-{index}",
                    metric=self.metric_body(metric_id=f"metric-{index}"),
                ),
            )

        page = self.client.get(
            "/red/measurements",
            params={"tenant_id": TENANT, "limit": 2, "offset": 1},
        )

        self.assertEqual(200, page.status_code, page.text)
        self.assertEqual(3, page.json()["total"])
        self.assertEqual(2, page.json()["limit"])
        self.assertEqual(1, page.json()["offset"])
        self.assertEqual(2, len(page.json()["records"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
