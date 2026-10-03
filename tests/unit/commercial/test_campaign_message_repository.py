"""Behavioral tests for the approved message store (Commercial application).

Rules under test come from SPEC.md sections 3, 4 and 9:
- A passing gate pins exact approved asset versions and intended use (SPEC.md
  section 3).
- A previous approved version stays historically identifiable, and a change is a
  new revision rather than an overwrite (SPEC.md section 4).
- A message is a client resource: it must carry its tenant on every read and
  write, and one client's message cannot be resolved for another (SPEC.md
  sections 3 and 9).

The stage 7 to 10 gates resolve the exact stage 6 message a prior gate approved
from this seam instead of trusting a repeated request body.
"""

from __future__ import annotations

import unittest

from redops.contexts.commercial.domain.errors import (
    CampaignMessageDependencyError,
    CampaignMessageReadinessError,
    CampaignMessageVersionConflictError,
    CampaignMessageVersionTenantBoundaryError,
    InvalidDeliverySpecificationError,
    OfferDependencyError,
)
from redops.contexts.commercial.infrastructure.mappers import (
    campaign_message_from_payload,
    campaign_message_to_payload,
)
from redops.contexts.commercial.infrastructure.repositories import (
    InMemoryCampaignMessageRepository,
)

from .fixtures import (
    TENANT,
    approved_campaign_message,
    campaign_message,
)


class CampaignMessageRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryCampaignMessageRepository()

    def test_a_saved_approved_message_is_resolved_by_its_id(self):
        message = approved_campaign_message()

        self.repository.save(message)

        self.assertEqual(
            message, self.repository.get(TENANT, message.message_id)
        )

    def test_unknown_message_resolves_to_none(self):
        self.repository.save(approved_campaign_message())

        self.assertIsNone(self.repository.get(TENANT, "message-other"))

    def test_a_different_body_under_the_same_id_is_refused(self):
        self.repository.save(approved_campaign_message())

        with self.assertRaises(CampaignMessageVersionConflictError):
            self.repository.save(
                approved_campaign_message(story="a different story")
            )

    def test_re_saving_the_identical_message_is_idempotent(self):
        message = approved_campaign_message()
        self.repository.save(message)

        self.repository.save(message)

        self.assertEqual(
            message, self.repository.get(TENANT, message.message_id)
        )

    def test_a_message_that_is_not_approved_cannot_be_stored(self):
        with self.assertRaises(CampaignMessageReadinessError):
            self.repository.save(campaign_message())

    def test_a_blank_tenant_is_refused_on_read(self):
        message = approved_campaign_message()
        self.repository.save(message)

        for tenant in ("", "   "):
            with self.subTest(tenant=tenant):
                with self.assertRaises(
                    CampaignMessageVersionTenantBoundaryError
                ):
                    self.repository.get(tenant, message.message_id)

    def test_one_clients_message_is_not_visible_to_another(self):
        self.repository.save(approved_campaign_message())

        self.assertIsNone(self.repository.get("client-other", "message-3f"))


class CampaignMessageMapperTests(unittest.TestCase):
    """The durable payload round-trips the full approved message aggregate.

    SPEC.md section 4: a passing gate pins the exact approved version, so the
    payload the PostgreSQL adapter stores must rebuild an equal message -- its
    grounding offer, its pinned method reference and all twelve canonical message
    parts included -- rather than a laxer message that would read back after a
    restart.
    """

    def test_an_approved_message_round_trips_exactly(self):
        message = approved_campaign_message()

        self.assertEqual(
            message,
            campaign_message_from_payload(campaign_message_to_payload(message)),
        )

    def test_the_grounding_offer_survives_the_round_trip(self):
        message = approved_campaign_message()

        rebuilt = campaign_message_from_payload(
            campaign_message_to_payload(message)
        )

        self.assertEqual(message.offer, rebuilt.offer)
        self.assertTrue(rebuilt.offer.is_production_ready)

    def test_a_stored_payload_the_domain_would_reject_raises(self):
        payload = campaign_message_to_payload(approved_campaign_message())
        payload["offer"]["tenant_id"] = "client-other"

        with self.assertRaises(
            (
                CampaignMessageDependencyError,
                InvalidDeliverySpecificationError,
                OfferDependencyError,
            )
        ):
            campaign_message_from_payload(payload)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
