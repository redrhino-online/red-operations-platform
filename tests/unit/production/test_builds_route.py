"""HTTP-boundary behavioral tests for the build route (SPEC.md section 7).

SPEC.md section 7 lists ``/builds``; section 9 requires every tenant resource
query to carry ``tenant_id`` and every list endpoint to enforce client access and
pagination; section 3 makes an active build always carry an owner and a next
action. These tests drive the real FastAPI app against a fresh in-memory build
store substituted through the overridable dependency, so a build is created and
read only under its own tenant and a blank owner or next action is refused.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest

TENANT = "3fmindset"
OTHER_TENANT = "client-other"


class BuildsRouteTests(unittest.TestCase):
    """The build surface is a tenant-scoped read and a proposal write."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient

            from redops.api.app import create_app
            from redops.api.routes import get_build_object_repository
            from redops.contexts.production.infrastructure.repositories import (
                InMemoryBuildObjectRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.build_dependency = staticmethod(get_build_object_repository)
        cls.build_store_class = staticmethod(InMemoryBuildObjectRepository)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.builds = self.build_store_class()
        self.app.dependency_overrides[self.build_dependency] = lambda: self.builds
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def build_body(**overrides):
        body = {
            "build_id": "build-1",
            "tenant_id": TENANT,
            "build_type": "authority-amplifier-video",
            "purpose": "stage 7 creative",
            "audience": "3f prospects",
            "owner": "production-manager",
            "next_action": "record the video",
            "refs": ["authority-amplifier-script@1"],
        }
        body.update(overrides)
        return body

    def test_a_created_build_is_listed_for_its_tenant(self) -> None:
        created = self.client.post("/red/builds", json=self.build_body())

        self.assertEqual(201, created.status_code, created.text)
        self.assertEqual("build-1", created.json()["build_id"])
        self.assertEqual("identified", created.json()["state"])
        self.assertTrue(created.json()["is_active"])

        listed = self.client.get("/red/builds", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(1, listed.json()["total"])
        self.assertEqual("build-1", listed.json()["builds"][0]["build_id"])

    def test_a_build_is_not_listed_for_another_client(self) -> None:
        self.client.post("/red/builds", json=self.build_body())

        listed = self.client.get("/red/builds", params={"tenant_id": OTHER_TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["builds"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get("/red/builds")

        self.assertEqual(422, response.status_code, response.text)

    def test_a_build_without_an_owner_is_refused(self) -> None:
        response = self.client.post(
            "/red/builds", json=self.build_body(owner="")
        )

        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual("InvalidBuildError", response.json()["detail"]["error"])
        self.assertIsNone(self.builds.get(TENANT, "build-1"))

    def test_a_build_without_a_tenant_is_refused(self) -> None:
        response = self.client.post(
            "/red/builds", json=self.build_body(tenant_id="  ")
        )

        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual("InvalidBuildError", response.json()["detail"]["error"])

    def test_build_pagination_is_applied_after_tenant_scoping(self) -> None:
        for index in range(3):
            self.client.post(
                "/red/builds", json=self.build_body(build_id=f"build-{index}")
            )

        page = self.client.get(
            "/red/builds", params={"tenant_id": TENANT, "limit": 2, "offset": 1}
        )

        self.assertEqual(200, page.status_code, page.text)
        self.assertEqual(3, page.json()["total"])
        self.assertEqual(2, page.json()["limit"])
        self.assertEqual(1, page.json()["offset"])
        self.assertEqual(2, len(page.json()["builds"]))

    @staticmethod
    def transition_body(**overrides):
        body = {
            "tenant_id": TENANT,
            "expected_version": 1,
            "target_state": "ready",
            "actor": "specialist-1",
            "reason": "footage arrived",
            "correlation_id": "corr-build-transition-1",
            "on": "2026-10-06",
        }
        body.update(overrides)
        return body

    def test_a_transition_with_the_current_version_advances_the_build(self) -> None:
        self.client.post("/red/builds", json=self.build_body())

        response = self.client.post(
            "/red/builds/build-1/transition", json=self.transition_body()
        )

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual("ready", response.json()["state"])
        self.assertEqual(2, response.json()["version"])

    def test_a_stale_transition_is_refused_without_changing_state(self) -> None:
        self.client.post("/red/builds", json=self.build_body())
        first = self.client.post(
            "/red/builds/build-1/transition", json=self.transition_body()
        )
        self.assertEqual(200, first.status_code, first.text)

        stale = self.client.post(
            "/red/builds/build-1/transition", json=self.transition_body()
        )

        self.assertEqual(409, stale.status_code, stale.text)
        self.assertEqual(
            "BuildObjectVersionConflictError", stale.json()["detail"]["error"]
        )
        stored = self.builds.get(TENANT, "build-1")
        self.assertEqual(2, stored.version)
        self.assertEqual("ready", stored.state.value)

    def test_a_transition_for_an_unknown_build_is_a_404(self) -> None:
        response = self.client.post(
            "/red/builds/missing/transition", json=self.transition_body()
        )

        self.assertEqual(404, response.status_code, response.text)
        self.assertEqual(
            "BuildObjectNotFoundError", response.json()["detail"]["error"]
        )

    def test_a_transition_for_another_client_is_a_404(self) -> None:
        self.client.post("/red/builds", json=self.build_body())

        response = self.client.post(
            "/red/builds/build-1/transition",
            json=self.transition_body(tenant_id=OTHER_TENANT),
        )

        self.assertEqual(404, response.status_code, response.text)

    def test_an_illegal_transition_is_a_422(self) -> None:
        self.client.post("/red/builds", json=self.build_body())

        response = self.client.post(
            "/red/builds/build-1/transition",
            json=self.transition_body(target_state="approved"),
        )

        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual(
            "IllegalBuildTransitionError", response.json()["detail"]["error"]
        )
        self.assertEqual(1, self.builds.get(TENANT, "build-1").version)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
