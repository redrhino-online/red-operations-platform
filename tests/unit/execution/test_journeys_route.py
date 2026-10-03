"""HTTP-boundary behavioral tests for the journey release route (SPEC.md section 7).

SPEC.md section 7 lists ``/journeys``; section 9 requires every tenant resource
query to carry ``tenant_id`` and every list endpoint to enforce client access and
pagination; section 3 names the ``JourneyRelease`` core aggregate (assets,
routing, configuration digest, rollback ref) whose invariant is "launch needs
signed readiness and authorized release". These tests drive the real FastAPI app
against a fresh in-memory release store and a launch QA store seeded with an
authorized stage 9 QA, substituted through the overridable dependencies, so a
release is created and read only under its own tenant, grounded on the durable
QA, and refused when the QA is missing or the release is not one exact version
per kind.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest

from .fixtures import TENANT, ready_for_traffic

OTHER_TENANT = "client-other"


class JourneysRouteTests(unittest.TestCase):
    """The journey surface is a tenant-scoped read and an authorized release write."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient

            from redops.api.app import create_app
            from redops.api.routes import (
                get_journey_release_repository,
                get_launch_qa_repository,
            )
            from redops.contexts.execution.infrastructure.repositories import (
                InMemoryJourneyReleaseRepository,
                InMemoryLaunchQARepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.release_dependency = staticmethod(get_journey_release_repository)
        cls.qa_dependency = staticmethod(get_launch_qa_repository)
        cls.release_store_class = staticmethod(InMemoryJourneyReleaseRepository)
        cls.qa_store_class = staticmethod(InMemoryLaunchQARepository)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.releases = self.release_store_class()
        self.qas = self.qa_store_class()
        self.qas.save(ready_for_traffic())
        self.app.dependency_overrides[self.release_dependency] = (
            lambda: self.releases
        )
        self.app.dependency_overrides[self.qa_dependency] = lambda: self.qas
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def release_body(**overrides):
        body = {
            "release_id": "release-1",
            "tenant_id": TENANT,
            "qa_id": "qa-3f",
            "assets": [
                {"asset_id": "asset-pages", "kind": "pages", "version": 1},
                {"asset_id": "asset-forms", "kind": "forms", "version": 1},
            ],
            "routing": "route://3f/main",
            "configuration_digest": "sha256:config",
            "rollback_ref": "release://3f/previous",
        }
        body.update(overrides)
        return body

    def test_a_created_release_is_listed_for_its_tenant(self) -> None:
        created = self.client.post("/red/journeys", json=self.release_body())

        self.assertEqual(201, created.status_code, created.text)
        self.assertEqual("release-1", created.json()["release_id"])
        self.assertEqual("qa-3f", created.json()["qa_id"])
        self.assertTrue(created.json()["is_authorized"])
        self.assertEqual(
            ["forms", "pages"], created.json()["released_kinds"]
        )

        listed = self.client.get("/red/journeys", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(1, listed.json()["total"])
        self.assertEqual(
            "release-1", listed.json()["releases"][0]["release_id"]
        )

    def test_a_release_is_not_listed_for_another_client(self) -> None:
        self.client.post("/red/journeys", json=self.release_body())

        listed = self.client.get(
            "/red/journeys", params={"tenant_id": OTHER_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get("/red/journeys")

        self.assertEqual(422, response.status_code, response.text)

    def test_a_missing_launch_qa_is_a_named_404(self) -> None:
        response = self.client.post(
            "/red/journeys",
            json=self.release_body(qa_id="qa-absent"),
        )

        self.assertEqual(404, response.status_code, response.text)
        self.assertEqual(
            "LaunchQANotFoundError", response.json()["detail"]["error"]
        )
        self.assertIsNone(self.releases.get(TENANT, "release-1"))

    def test_two_versions_for_one_kind_are_refused(self) -> None:
        response = self.client.post(
            "/red/journeys",
            json=self.release_body(
                assets=[
                    {"asset_id": "asset-pages", "kind": "pages", "version": 1},
                    {"asset_id": "asset-pages-2", "kind": "pages", "version": 2},
                ]
            ),
        )

        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual(
            "InvalidJourneyReleaseError",
            response.json()["detail"]["error"],
        )
        self.assertIsNone(self.releases.get(TENANT, "release-1"))

    def test_a_repeated_release_id_with_a_different_body_is_a_409(self) -> None:
        self.client.post("/red/journeys", json=self.release_body())

        conflict = self.client.post(
            "/red/journeys",
            json=self.release_body(routing="route://3f/changed"),
        )

        self.assertEqual(409, conflict.status_code, conflict.text)
        self.assertEqual(
            "JourneyReleaseVersionConflictError",
            conflict.json()["detail"]["error"],
        )

    def test_journey_pagination_is_applied_after_tenant_scoping(self) -> None:
        for index in range(3):
            self.client.post(
                "/red/journeys",
                json=self.release_body(release_id=f"release-{index}"),
            )

        page = self.client.get(
            "/red/journeys",
            params={"tenant_id": TENANT, "limit": 2, "offset": 1},
        )

        self.assertEqual(200, page.status_code, page.text)
        self.assertEqual(3, page.json()["total"])
        self.assertEqual(2, page.json()["limit"])
        self.assertEqual(1, page.json()["offset"])
        self.assertEqual(2, len(page.json()["releases"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
