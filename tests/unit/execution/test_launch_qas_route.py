"""HTTP-boundary behavioral tests for the launch readiness read (SPEC.md section 7).

SPEC.md section 8 lists the launch readiness screen; section 4 stage 9 requires
the QA state, its required checks (each with an outcome, evidence and owner) and
the designated human's traffic authorization; section 9 requires every tenant
resource query to carry ``tenant_id`` and section 7 requires list endpoints to
enforce client access and pagination. These tests drive the real FastAPI app
against a fresh in-memory launch QA store substituted through the overridable
dependency, so the readiness read is tenant scoped and the projected checks keep
their exact outcome, owner and critical-path flag, and a QA never authorizes
traffic by being listed.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest

from redops.contexts.execution.domain.value_objects import (
    QACheckKind,
    QACheckOutcome,
)

from .fixtures import TENANT, ready_for_traffic

OTHER_TENANT = "client-other"


class LaunchQAsRouteTests(unittest.TestCase):
    """The launch readiness surface is a tenant-scoped read."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient

            from redops.api.app import create_app
            from redops.api.routes import get_launch_qa_repository
            from redops.contexts.execution.infrastructure.repositories import (
                InMemoryLaunchQARepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.qa_dependency = staticmethod(get_launch_qa_repository)
        cls.qa_store_class = staticmethod(InMemoryLaunchQARepository)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.qas = self.qa_store_class()
        self.app.dependency_overrides[self.qa_dependency] = lambda: self.qas
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_a_seeded_qa_is_listed_with_its_checks_and_authorization(self) -> None:
        self.qas.save(ready_for_traffic())

        listed = self.client.get(
            "/red/launch-qas", params={"tenant_id": TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        payload = listed.json()
        self.assertEqual(1, payload["total"])
        qa = payload["launch_qas"][0]
        self.assertEqual("qa-3f", qa["qa_id"])
        self.assertEqual("ready_for_traffic", qa["state"])
        self.assertTrue(qa["is_ready_for_traffic"])
        self.assertEqual("client-authority", qa["designated_authority"])
        self.assertEqual(
            "client-authority", qa["authorization"]["authorized_by"]
        )
        self.assertEqual(18, len(qa["checks"]))
        self.assertEqual("recorded_message", qa["checks"][0]["kind"])
        self.assertTrue(all(check["outcome"] == "passed" for check in qa["checks"]))
        self.assertTrue(qa["checks"][0]["is_critical_path"])

    def test_a_non_critical_exception_is_marked_off_the_critical_path(self) -> None:
        from .fixtures import launch_checks

        self.qas.save(
            ready_for_traffic(
                checks=launch_checks(
                    {QACheckKind.PAYMENT: QACheckOutcome.EXCEPTED}
                )
            )
        )

        listed = self.client.get(
            "/red/launch-qas", params={"tenant_id": TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        checks = {
            check["kind"]: check for check in listed.json()["launch_qas"][0]["checks"]
        }
        self.assertEqual("excepted", checks["payment"]["outcome"])
        self.assertEqual("risk-owner", checks["payment"]["owner"])
        self.assertFalse(checks["payment"]["is_critical_path"])

    def test_a_qa_is_not_listed_for_another_client(self) -> None:
        self.qas.save(ready_for_traffic())

        listed = self.client.get(
            "/red/launch-qas", params={"tenant_id": OTHER_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get("/red/launch-qas")

        self.assertEqual(422, response.status_code, response.text)

    def test_pagination_is_applied_after_tenant_scoping(self) -> None:
        for qa_id in ("qa-a", "qa-b", "qa-c"):
            self.qas.save(ready_for_traffic(qa_id=qa_id))

        page = self.client.get(
            "/red/launch-qas",
            params={"tenant_id": TENANT, "limit": 1, "offset": 1},
        )

        self.assertEqual(200, page.status_code, page.text)
        self.assertEqual(3, page.json()["total"])
        self.assertEqual(1, page.json()["limit"])
        self.assertEqual(1, page.json()["offset"])
        self.assertEqual(1, len(page.json()["launch_qas"]))
        self.assertEqual("qa-b", page.json()["launch_qas"][0]["qa_id"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
