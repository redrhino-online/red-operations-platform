"""HTTP-boundary behavioral tests for the opportunity route (SPEC.md section 7).

SPEC.md section 7 lists ``/opportunities`` and requires list endpoints to enforce
client access and pagination; SPEC.md section 9 requires every tenant resource
query to carry ``tenant_id``; SPEC.md sections 1 and 5 keep a proposed expansion
from being represented as an authorized investment. These tests drive the real
FastAPI app against a fresh in-memory opportunity store, so a proposal is
tenant-scoped, traceable to an exact source asset version and never approved by
the platform.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest

TENANT = "client-3f"
OTHER_TENANT = "client-other"


def payload(**overrides):
    values = {
        "tenant_id": TENANT,
        "opportunity_id": "opp-1",
        "title": "a smaller entry point offer",
        "kind": "entry_point",
        "source": {"asset_id": "offer-3f", "kind": "offer-version", "version": 3},
        "investment_case": "the warmed audience already converts on the core offer",
        "expected_outcome": "a lower priced entry point that raises qualified leads",
        "owner": "portfolio-lead",
        "next_action": "size the offer and price it against the primary currency",
        "captured_on": "2026-10-03",
    }
    values.update(overrides)
    return values


class OpportunitiesRouteTests(unittest.TestCase):
    """The opportunity surface is a tenant-scoped register of proposals."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient

            from redops.api.app import create_app
            from redops.api.routes import get_opportunity_repository
            from redops.contexts.portfolio.infrastructure.repositories import (
                InMemoryOpportunityRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.repository_dependency = staticmethod(get_opportunity_repository)
        cls.repository_class = staticmethod(InMemoryOpportunityRepository)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.opportunities = self.repository_class()
        self.app.dependency_overrides[self.repository_dependency] = (
            lambda: self.opportunities
        )
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_a_recorded_opportunity_is_listed_as_a_proposal(self) -> None:
        created = self.client.post("/red/opportunities", json=payload())

        self.assertEqual(201, created.status_code, created.text)
        body = created.json()
        self.assertEqual("proposed", body["state"])
        self.assertEqual("offer-version", body["source_kind"])
        self.assertEqual(3, body["source_version"])

        listed = self.client.get(
            "/red/opportunities", params={"tenant_id": TENANT}
        )
        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(1, listed.json()["total"])
        self.assertEqual(
            "opp-1", listed.json()["opportunities"][0]["opportunity_id"]
        )

    def test_listing_is_scoped_to_the_tenant(self) -> None:
        self.client.post("/red/opportunities", json=payload())

        other = self.client.get(
            "/red/opportunities", params={"tenant_id": OTHER_TENANT}
        )

        self.assertEqual(200, other.status_code, other.text)
        self.assertEqual(0, other.json()["total"])

    def test_an_untyped_kind_is_a_named_422(self) -> None:
        response = self.client.post(
            "/red/opportunities", json=payload(kind="not-a-kind")
        )

        self.assertEqual(422, response.status_code, response.text)

    def test_a_blank_owner_is_a_named_422(self) -> None:
        response = self.client.post(
            "/red/opportunities", json=payload(owner="   ")
        )

        self.assertEqual(422, response.status_code, response.text)

    def test_an_exact_replay_is_idempotent(self) -> None:
        first = self.client.post("/red/opportunities", json=payload())
        second = self.client.post("/red/opportunities", json=payload())

        self.assertEqual(201, first.status_code, first.text)
        self.assertEqual(201, second.status_code, second.text)
        listed = self.client.get(
            "/red/opportunities", params={"tenant_id": TENANT}
        )
        self.assertEqual(1, listed.json()["total"])

    def test_a_same_id_different_body_is_a_named_409(self) -> None:
        self.client.post("/red/opportunities", json=payload())

        response = self.client.post(
            "/red/opportunities", json=payload(title="a different opportunity")
        )

        self.assertEqual(409, response.status_code, response.text)

    def test_a_blank_tenant_is_a_named_422(self) -> None:
        response = self.client.get(
            "/red/opportunities", params={"tenant_id": "   "}
        )

        self.assertEqual(422, response.status_code, response.text)

    def test_listing_is_paginated(self) -> None:
        for index in range(3):
            self.client.post(
                "/red/opportunities",
                json=payload(opportunity_id=f"opp-{index}"),
            )

        page = self.client.get(
            "/red/opportunities",
            params={"tenant_id": TENANT, "limit": 2, "offset": 1},
        )

        self.assertEqual(200, page.status_code, page.text)
        body = page.json()
        self.assertEqual(3, body["total"])
        self.assertEqual(2, body["limit"])
        self.assertEqual(1, body["offset"])
        self.assertEqual(2, len(body["opportunities"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
