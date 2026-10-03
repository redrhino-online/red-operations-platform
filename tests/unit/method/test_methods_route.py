"""HTTP-boundary behavioral tests for the approved method route (SPEC.md §7).

SPEC.md section 7 lists ``/methods``; section 9 requires every query to carry the
client scope; section 3 pins an exact version and intended use at approval and
section 4 keeps the approved version identifiable. These tests drive the real
FastAPI app against a fresh in-memory approved-method store (substituted through
the overridable dependency), so a client's approved methods are readable for that
tenant, are unreadable for another, and cannot be written through the read
surface (a direct write would confer the approval governance owns).

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest
from datetime import date

from .test_method_version import method_version

TENANT = "client-3f"
OTHER_TENANT = "client-other"
ON = date(2026, 10, 2)


def approved_method():
    return method_version().approve(
        approved_by="client-approver-1",
        intended_use="3f pilot campaign",
        on=ON,
    )


class MethodsRouteTests(unittest.TestCase):
    """The method surface is a tenant-scoped read over the approved-method store."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import get_method_version_repository
            from redops.contexts.method.infrastructure.repositories import (
                InMemoryMethodVersionRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.method_dependency = staticmethod(get_method_version_repository)
        cls.repository_class = staticmethod(InMemoryMethodVersionRepository)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.methods = self.repository_class()
        self.app.dependency_overrides[self.method_dependency] = lambda: self.methods
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_an_approved_method_is_listed_for_its_tenant(self) -> None:
        self.methods.save(approved_method())

        listed = self.client.get("/red/methods", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        body = listed.json()
        self.assertEqual(1, body["total"])
        method = body["methods"][0]
        self.assertEqual("method-3f", method["method_id"])
        self.assertEqual("1.0.0", method["semantic_version"])
        self.assertTrue(method["is_approved"])
        self.assertEqual("client-approver-1", method["approved_by"])
        self.assertEqual("3f pilot campaign", method["intended_use"])
        self.assertEqual("qualified referrals", method["primary_currency"])
        self.assertIsNotNone(method["signature_solution_id"])

    def test_a_method_is_not_listed_for_another_client(self) -> None:
        self.methods.save(approved_method())

        listed = self.client.get(
            "/red/methods", params={"tenant_id": OTHER_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["methods"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get("/red/methods")

        self.assertEqual(422, response.status_code, response.text)

    def test_the_read_surface_refuses_a_write(self) -> None:
        response = self.client.post("/red/methods", json={"method_id": "method-3f"})

        self.assertEqual(405, response.status_code, response.text)

    def test_method_pagination_is_applied_after_tenant_scoping(self) -> None:
        self.methods.save(approved_method())
        second = method_version(method_id="a-method").approve(
            approved_by="client-approver-1",
            intended_use="3f pilot campaign",
            on=ON,
        )
        self.methods.save(second)

        page = self.client.get(
            "/red/methods",
            params={"tenant_id": TENANT, "limit": 1, "offset": 1},
        )

        self.assertEqual(200, page.status_code, page.text)
        self.assertEqual(2, page.json()["total"])
        self.assertEqual(1, len(page.json()["methods"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
