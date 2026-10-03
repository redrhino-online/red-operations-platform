"""HTTP-boundary behavioral tests for the offer route (SPEC.md section 7).

SPEC.md section 7 lists ``/offers``; section 9 requires every tenant resource
query to carry ``tenant_id`` and every list endpoint to enforce client access and
pagination; section 3 makes production require approved dependencies. These tests
drive the real FastAPI app against a fresh in-memory offer store substituted
through the overridable dependency, so a production ready offer is read only under
its own tenant and never written through the surface.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest

from .fixtures import TENANT, production_ready_offer

OTHER_TENANT = "client-other"


class OffersRouteTests(unittest.TestCase):
    """The offer surface is a tenant-scoped read of the offer store."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient

            from redops.api.app import create_app
            from redops.api.routes import get_offer_version_repository
            from redops.contexts.commercial.infrastructure.repositories import (
                InMemoryOfferVersionRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.offer_dependency = staticmethod(get_offer_version_repository)
        cls.offer_store_class = staticmethod(InMemoryOfferVersionRepository)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.offers = self.offer_store_class()
        self.app.dependency_overrides[self.offer_dependency] = lambda: self.offers
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_a_stored_offer_is_listed_for_its_tenant(self) -> None:
        self.offers.save(production_ready_offer(offer_id="offer-1"))

        listed = self.client.get("/red/offers", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        body = listed.json()
        self.assertEqual(1, body["total"])
        self.assertEqual("offer-1", body["offers"][0]["offer_id"])
        self.assertTrue(body["offers"][0]["is_production_ready"])
        self.assertEqual(1, len(body["offers"][0]["method_refs"]))

    def test_an_offer_is_not_listed_for_another_client(self) -> None:
        self.offers.save(production_ready_offer(offer_id="offer-1"))

        listed = self.client.get("/red/offers", params={"tenant_id": OTHER_TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["offers"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get("/red/offers")

        self.assertEqual(422, response.status_code, response.text)

    def test_the_offer_surface_exposes_no_write_path(self) -> None:
        response = self.client.post(
            "/red/offers", json={"tenant_id": TENANT}
        )

        self.assertEqual(405, response.status_code, response.text)

    def test_offer_pagination_is_applied_after_tenant_scoping(self) -> None:
        for index in range(3):
            self.offers.save(production_ready_offer(offer_id=f"offer-{index}"))

        page = self.client.get(
            "/red/offers", params={"tenant_id": TENANT, "limit": 2, "offset": 1}
        )

        self.assertEqual(200, page.status_code, page.text)
        self.assertEqual(3, page.json()["total"])
        self.assertEqual(2, page.json()["limit"])
        self.assertEqual(1, page.json()["offset"])
        self.assertEqual(2, len(page.json()["offers"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
