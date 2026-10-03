"""HTTP-boundary behavioral tests for the claim route (SPEC.md section 7).

SPEC.md section 7 lists ``/claims``; section 9 requires every tenant resource
query to carry ``tenant_id`` and every list endpoint to enforce client access and
pagination; sections 3 and 11 require a claim's source attribution to survive
ingestion and a Known claim to cite a real direct source. These tests drive the
real FastAPI app against fresh in-memory stores (substituted through the
overridable dependencies), so a claim cannot be read under another tenant and a
Known claim cannot be recorded against a fabricated citation.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest

TENANT = "3fmindset"
OTHER_TENANT = "client-other"


class ClaimsRouteTests(unittest.TestCase):
    """The claim surface is served only through the claim and source stores."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import (
                get_claim_store,
                get_source_record_store,
            )
            from redops.contexts.knowledge.infrastructure.repositories import (
                InMemoryClaimStore,
                InMemorySourceRecordStore,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.claim_dependency = staticmethod(get_claim_store)
        cls.source_dependency = staticmethod(get_source_record_store)
        cls.claim_store_class = staticmethod(InMemoryClaimStore)
        cls.source_store_class = staticmethod(InMemorySourceRecordStore)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.claims = self.claim_store_class()
        self.sources = self.source_store_class()
        self.app.dependency_overrides[self.claim_dependency] = lambda: self.claims
        self.app.dependency_overrides[self.source_dependency] = lambda: self.sources
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def source_body(checksum: str = "sha256:abc"):
        return {
            "source_id": "src-1",
            "locator": "project_sources/notes/01.md",
            "checksum": checksum,
            "captured_on": "2026-10-03",
            "access_rule": "client-and-red-only",
        }

    @staticmethod
    def claim_body(**overrides):
        body = {
            "claim_id": "claim-1",
            "tenant_id": TENANT,
            "statement": "the market cares about agency",
            "provenance": "unknown",
            "confidence_note": "interview notes",
            "citations": [],
        }
        body.update(overrides)
        return body

    def test_a_created_claim_is_listed_for_its_tenant(self) -> None:
        created = self.client.post("/red/claims", json=self.claim_body())

        self.assertEqual(201, created.status_code, created.text)
        self.assertEqual("claim-1", created.json()["claim_id"])
        self.assertFalse(created.json()["is_directly_sourced"])

        listed = self.client.get("/red/claims", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        body = listed.json()
        self.assertEqual(1, body["total"])
        self.assertEqual("claim-1", body["claims"][0]["claim_id"])

    def test_a_claim_is_not_listed_for_another_client(self) -> None:
        self.client.post("/red/claims", json=self.claim_body())

        listed = self.client.get("/red/claims", params={"tenant_id": OTHER_TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["claims"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get("/red/claims")

        self.assertEqual(422, response.status_code, response.text)

    def test_a_known_claim_without_a_citation_is_refused(self) -> None:
        response = self.client.post(
            "/red/claims", json=self.claim_body(provenance="known")
        )

        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual(
            "UnsupportedClaimError", response.json()["detail"]["error"]
        )

    def test_a_known_claim_citing_an_unknown_source_is_refused(self) -> None:
        response = self.client.post(
            "/red/claims",
            json=self.claim_body(
                provenance="known",
                citations=[
                    {
                        "source_id": "src-missing",
                        "checksum": "sha256:abc",
                        "location": "notes/01.md#p1",
                    }
                ],
            ),
        )

        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual("ClaimCitationError", response.json()["detail"]["error"])
        self.assertIsNone(self.claims.get(TENANT, "claim-1"))

    def test_a_known_claim_citing_a_mismatched_checksum_is_refused(self) -> None:
        self.client.post(
            f"/red/clients/{TENANT}/sources",
            json=self.source_body(checksum="sha256:abc"),
        )

        response = self.client.post(
            "/red/claims",
            json=self.claim_body(
                provenance="known",
                citations=[
                    {
                        "source_id": "src-1",
                        "checksum": "sha256:fabricated",
                        "location": "notes/01.md#p1",
                    }
                ],
            ),
        )

        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual("ClaimCitationError", response.json()["detail"]["error"])

    def test_a_known_claim_citing_a_stored_source_is_recorded(self) -> None:
        self.client.post(
            f"/red/clients/{TENANT}/sources", json=self.source_body()
        )

        response = self.client.post(
            "/red/claims",
            json=self.claim_body(
                provenance="known",
                citations=[
                    {
                        "source_id": "src-1",
                        "checksum": "sha256:abc",
                        "location": "notes/01.md#p1",
                    }
                ],
            ),
        )

        self.assertEqual(201, response.status_code, response.text)
        self.assertTrue(response.json()["is_directly_sourced"])
        self.assertEqual(1, len(response.json()["citations"]))

    def test_claim_pagination_is_applied_after_tenant_scoping(self) -> None:
        for index in range(3):
            self.client.post(
                "/red/claims",
                json=self.claim_body(claim_id=f"claim-{index}"),
            )

        page = self.client.get(
            "/red/claims", params={"tenant_id": TENANT, "limit": 2, "offset": 1}
        )

        self.assertEqual(200, page.status_code, page.text)
        self.assertEqual(3, page.json()["total"])
        self.assertEqual(2, page.json()["limit"])
        self.assertEqual(1, page.json()["offset"])
        self.assertEqual(2, len(page.json()["claims"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
