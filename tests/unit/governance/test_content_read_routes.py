"""HTTP-boundary behavioral tests for the hidden-content read routes (spec §4.1).

The stage 6 campaign messages, stage 7 authority amplifiers and stage 8 funnel
integrations were write-only before this spec: a gate stored them and no read
route exposed their content, so the asset review panel could not render what
was approved. These tests drive the real FastAPI app against fresh in-memory
stores substituted through the overridable dependencies (the same wiring the
``DATABASE_URL`` store selection serves in production), so a stored aggregate
is listed with its full content only under its own tenant, an unknown tenant
lists nothing, and the tenant parameter is mandatory.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest

from tests.unit.commercial.fixtures import TENANT, approved_campaign_message
from tests.unit.execution.fixtures import complete_funnel
from tests.unit.production.fixtures import approved_amplifier

OTHER_TENANT = "client-other"
UNKNOWN_TENANT = "tenant-unknown"

MESSAGE_CONTENT_FIELDS = (
    "message_id",
    "owner",
    "avatar",
    "currency",
    "problem",
    "promise",
    "cta",
    "problem_hierarchy",
    "desired_outcome",
    "proof_objections",
    "story",
    "method_explanation",
    "lead_magnet",
    "hook",
    "angles",
    "landing_message",
    "authority_amplifier_outline",
    "product_offer_id",
)

FUNNEL_ASSET_FIELDS = (
    "campaign_architecture",
    "pages",
    "forms",
    "qualification",
    "booking",
    "sequences",
    "crm",
    "tags",
    "automation",
    "analytics",
    "tracking",
    "sales_handoff",
    "sops",
)


class CampaignMessageReadRouteTests(unittest.TestCase):
    """The message surface is a tenant-scoped read of the approved message store."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient

            from redops.api.app import create_app
            from redops.api.routes import get_campaign_message_repository
            from redops.contexts.commercial.infrastructure.repositories import (
                InMemoryCampaignMessageRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.message_dependency = staticmethod(get_campaign_message_repository)
        cls.message_store_class = staticmethod(InMemoryCampaignMessageRepository)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.messages = self.message_store_class()
        self.app.dependency_overrides[self.message_dependency] = (
            lambda: self.messages
        )
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_a_stored_message_is_listed_with_its_full_content(self) -> None:
        self.messages.save(approved_campaign_message())

        listed = self.client.get("/red/messages", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        body = listed.json()
        self.assertEqual(1, body["total"])
        message = body["messages"][0]
        for field in MESSAGE_CONTENT_FIELDS:
            self.assertIn(field, message)
        self.assertEqual("message-3f", message["message_id"])
        self.assertEqual(TENANT, message["tenant_id"])
        self.assertEqual(
            ["no predictable referral flow", "referrals depend on luck"],
            message["problem_hierarchy"],
        )
        self.assertEqual(
            [
                "proof: referral partner network",
                "objection: no time to build it",
            ],
            message["proof_objections"],
        )
        self.assertEqual(
            ["referral drought", "referral engine"], message["angles"]
        )
        self.assertEqual("an owner-operator story", message["story"])
        self.assertEqual(
            "turn referrals into a system", message["landing_message"]
        )
        self.assertEqual("offer-1", message["product_offer_id"])
        self.assertEqual("offer-1", message["offer_id"])
        self.assertEqual("method-3f", message["method_ref"]["method_id"])
        self.assertEqual("1.0.0", message["method_ref"]["version"])
        self.assertEqual("approved", message["state"])
        self.assertTrue(message["is_approved"])

    def test_a_message_is_not_listed_for_another_client(self) -> None:
        self.messages.save(approved_campaign_message())

        listed = self.client.get(
            "/red/messages", params={"tenant_id": OTHER_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["messages"])

    def test_an_unknown_tenant_lists_no_messages(self) -> None:
        self.messages.save(approved_campaign_message())

        listed = self.client.get(
            "/red/messages", params={"tenant_id": UNKNOWN_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["messages"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get("/red/messages")

        self.assertEqual(422, response.status_code, response.text)

    def test_message_pagination_is_applied_after_tenant_scoping(self) -> None:
        for index in range(3):
            self.messages.save(
                approved_campaign_message(message_id=f"message-{index}")
            )

        page = self.client.get(
            "/red/messages",
            params={"tenant_id": TENANT, "limit": 2, "offset": 1},
        )

        self.assertEqual(200, page.status_code, page.text)
        body = page.json()
        self.assertEqual(3, body["total"])
        self.assertEqual(2, body["limit"])
        self.assertEqual(1, body["offset"])
        self.assertEqual(2, len(body["messages"]))
        self.assertEqual(
            ["message-1", "message-2"],
            [message["message_id"] for message in body["messages"]],
        )


class AuthorityAmplifierReadRouteTests(unittest.TestCase):
    """The amplifier surface is a tenant-scoped read of the amplifier store."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient

            from redops.api.app import create_app
            from redops.api.routes import get_authority_amplifier_repository
            from redops.contexts.production.infrastructure.repositories import (
                InMemoryAuthorityAmplifierRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.amplifier_dependency = staticmethod(
            get_authority_amplifier_repository
        )
        cls.amplifier_store_class = staticmethod(
            InMemoryAuthorityAmplifierRepository
        )

    def setUp(self) -> None:
        self.app = self.create_app()
        self.amplifiers = self.amplifier_store_class()
        self.app.dependency_overrides[self.amplifier_dependency] = (
            lambda: self.amplifiers
        )
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_a_stored_amplifier_is_listed_with_script_and_visuals(self) -> None:
        self.amplifiers.save(approved_amplifier())

        listed = self.client.get("/red/amplifiers", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        body = listed.json()
        self.assertEqual(1, body["total"])
        amplifier = body["amplifiers"][0]
        self.assertEqual("amplifier-3f", amplifier["amplifier_id"])
        self.assertEqual(TENANT, amplifier["tenant_id"])
        self.assertEqual(
            ["promise", "proof", "problems", "steps", "context", "action"],
            [section["kind"] for section in amplifier["script"]],
        )
        self.assertTrue(
            all(section["content"] for section in amplifier["script"])
        )
        self.assertEqual(
            {
                "storyboard": "asset://aa/storyboard",
                "brand_treatment": "asset://aa/brand",
                "presentation": "asset://aa/slides",
                "speaker_notes": "asset://aa/notes",
                "recording": "asset://aa/recording",
                "edited_video": "asset://aa/edited",
                "hosted_video": "asset://aa/hosted",
                "player_assets": "asset://aa/player",
            },
            amplifier["visuals"],
        )
        self.assertEqual(["claim-1"], amplifier["proof_claim_ids"])
        self.assertEqual("message-3f", amplifier["message_id"])
        self.assertEqual("method-3f", amplifier["method_ref"]["method_id"])
        self.assertEqual("offer-1", amplifier["offer_id"])
        self.assertEqual(
            "production-manager", amplifier["script_approval"]["approved_by"]
        )
        self.assertEqual(
            "client-authority", amplifier["creative_approval"]["approved_by"]
        )
        self.assertEqual("approved", amplifier["state"])
        self.assertTrue(amplifier["is_script_approved"])
        self.assertTrue(amplifier["is_approved"])

    def test_an_amplifier_is_not_listed_for_another_client(self) -> None:
        self.amplifiers.save(approved_amplifier())

        listed = self.client.get(
            "/red/amplifiers", params={"tenant_id": OTHER_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["amplifiers"])

    def test_an_unknown_tenant_lists_no_amplifiers(self) -> None:
        self.amplifiers.save(approved_amplifier())

        listed = self.client.get(
            "/red/amplifiers", params={"tenant_id": UNKNOWN_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["amplifiers"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get("/red/amplifiers")

        self.assertEqual(422, response.status_code, response.text)

    def test_amplifier_pagination_is_applied_after_tenant_scoping(self) -> None:
        for index in range(3):
            self.amplifiers.save(
                approved_amplifier(amplifier_id=f"amplifier-{index}")
            )

        page = self.client.get(
            "/red/amplifiers",
            params={"tenant_id": TENANT, "limit": 2, "offset": 1},
        )

        self.assertEqual(200, page.status_code, page.text)
        body = page.json()
        self.assertEqual(3, body["total"])
        self.assertEqual(2, body["limit"])
        self.assertEqual(1, body["offset"])
        self.assertEqual(2, len(body["amplifiers"]))
        self.assertEqual(
            ["amplifier-1", "amplifier-2"],
            [item["amplifier_id"] for item in body["amplifiers"]],
        )


class FunnelReadRouteTests(unittest.TestCase):
    """The funnel surface is a tenant-scoped read of the funnel store."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient

            from redops.api.app import create_app
            from redops.api.routes import get_funnel_integration_repository
            from redops.contexts.execution.infrastructure.repositories import (
                InMemoryFunnelIntegrationRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.funnel_dependency = staticmethod(get_funnel_integration_repository)
        cls.funnel_store_class = staticmethod(
            InMemoryFunnelIntegrationRepository
        )

    def setUp(self) -> None:
        self.app = self.create_app()
        self.funnels = self.funnel_store_class()
        self.app.dependency_overrides[self.funnel_dependency] = (
            lambda: self.funnels
        )
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_a_stored_funnel_is_listed_with_assets_and_routing(self) -> None:
        self.funnels.save(complete_funnel())

        listed = self.client.get("/red/funnels", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        body = listed.json()
        self.assertEqual(1, body["total"])
        funnel = body["funnels"][0]
        self.assertEqual("funnel-3f", funnel["integration_id"])
        self.assertEqual(TENANT, funnel["tenant_id"])
        for field in FUNNEL_ASSET_FIELDS:
            self.assertIn(field, funnel["assets"])
            self.assertTrue(funnel["assets"][field])
        self.assertEqual("amplifier-3f", funnel["amplifier_id"])
        self.assertEqual("message-3f", funnel["message_id"])
        self.assertEqual("method-3f", funnel["method_ref"]["method_id"])
        self.assertEqual("offer-1", funnel["offer_id"])
        routing = funnel["routing"]
        self.assertIsNotNone(routing)
        self.assertEqual("dry-run-3f", routing["dry_run_id"])
        self.assertEqual(
            ["capture", "engagement", "conversion"],
            [handoff["kind"] for handoff in routing["handoffs"]],
        )
        self.assertTrue(
            all(handoff["outcome"] == "routed" for handoff in routing["handoffs"])
        )
        self.assertTrue(
            all(handoff["record_id"] for handoff in routing["handoffs"])
        )
        self.assertEqual("complete", funnel["state"])
        self.assertTrue(funnel["is_complete"])

    def test_a_funnel_is_not_listed_for_another_client(self) -> None:
        self.funnels.save(complete_funnel())

        listed = self.client.get(
            "/red/funnels", params={"tenant_id": OTHER_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["funnels"])

    def test_an_unknown_tenant_lists_no_funnels(self) -> None:
        self.funnels.save(complete_funnel())

        listed = self.client.get(
            "/red/funnels", params={"tenant_id": UNKNOWN_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["funnels"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get("/red/funnels")

        self.assertEqual(422, response.status_code, response.text)

    def test_funnel_pagination_is_applied_after_tenant_scoping(self) -> None:
        for index in range(3):
            self.funnels.save(
                complete_funnel(integration_id=f"funnel-{index}")
            )

        page = self.client.get(
            "/red/funnels",
            params={"tenant_id": TENANT, "limit": 2, "offset": 1},
        )

        self.assertEqual(200, page.status_code, page.text)
        body = page.json()
        self.assertEqual(3, body["total"])
        self.assertEqual(2, body["limit"])
        self.assertEqual(1, body["offset"])
        self.assertEqual(2, len(body["funnels"]))
        self.assertEqual(
            ["funnel-1", "funnel-2"],
            [item["integration_id"] for item in body["funnels"]],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
