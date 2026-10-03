"""Behavioral tests for the production ready offer store (Commercial application).

Rules under test come from SPEC.md sections 3, 4 and 9:
- A passing gate pins exact approved asset versions and intended use (SPEC.md
  section 3).
- A previous approved version stays historically identifiable, and a change is a
  new revision rather than an overwrite (SPEC.md section 4).
- An offer is a client resource: it must carry its tenant on every read and
  write, and one client's offer cannot be resolved for another (SPEC.md sections
  3 and 9).

The stage 6 to 10 gates resolve the exact production ready offer a prior gate
pinned from this seam instead of trusting a repeated request body.
"""

from __future__ import annotations

import unittest

from redops.contexts.commercial.domain.errors import (
    InvalidDeliverySpecificationError,
    OfferReadinessError,
    OfferVersionConflictError,
    OfferVersionTenantBoundaryError,
)
from redops.contexts.commercial.infrastructure.mappers import (
    offer_from_payload,
    offer_to_payload,
)
from redops.contexts.commercial.infrastructure.repositories import (
    InMemoryOfferVersionRepository,
)

from .fixtures import (
    TENANT,
    delivery_specification,
    offer_version,
    production_ready_offer,
)


class OfferVersionRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryOfferVersionRepository()

    def test_a_saved_production_ready_offer_is_resolved_by_its_id(self):
        offer = production_ready_offer()

        self.repository.save(offer)

        self.assertEqual(offer, self.repository.get(TENANT, offer.offer_id))

    def test_unknown_offer_resolves_to_none(self):
        self.repository.save(production_ready_offer())

        self.assertIsNone(self.repository.get(TENANT, "offer-other"))

    def test_a_different_body_under_the_same_id_is_refused(self):
        self.repository.save(production_ready_offer())

        with self.assertRaises(OfferVersionConflictError):
            self.repository.save(
                production_ready_offer(promise="a different promise")
            )

    def test_re_saving_the_identical_offer_is_idempotent(self):
        offer = production_ready_offer()
        self.repository.save(offer)

        self.repository.save(offer)

        self.assertEqual(offer, self.repository.get(TENANT, offer.offer_id))

    def test_an_offer_that_is_not_production_ready_cannot_be_stored(self):
        with self.assertRaises(OfferReadinessError):
            self.repository.save(offer_version())

    def test_a_blank_tenant_is_refused_on_read(self):
        offer = production_ready_offer()
        self.repository.save(offer)

        for tenant in ("", "   "):
            with self.subTest(tenant=tenant):
                with self.assertRaises(OfferVersionTenantBoundaryError):
                    self.repository.get(tenant, offer.offer_id)

    def test_one_clients_offer_is_not_visible_to_another(self):
        self.repository.save(production_ready_offer())

        self.assertIsNone(self.repository.get("client-other", "offer-1"))


class OfferVersionMapperTests(unittest.TestCase):
    """The durable payload round-trips the full production ready aggregate.

    SPEC.md section 4: a passing gate pins the exact approved version, so the
    payload the PostgreSQL adapter stores must rebuild an equal offer -- its
    pinned method references and its complete stage 5 delivery specification
    grounded on the locked Signature Solution included -- rather than a laxer
    offer that would read back after a restart.
    """

    def test_a_production_ready_offer_round_trips_exactly(self):
        offer = production_ready_offer()

        self.assertEqual(offer, offer_from_payload(offer_to_payload(offer)))

    def test_a_draft_offer_round_trips_with_its_delivery_specification(self):
        offer = offer_version(delivery_specification=delivery_specification())

        rebuilt = offer_from_payload(offer_to_payload(offer))

        self.assertEqual(offer, rebuilt)
        self.assertIsNotNone(rebuilt.delivery_specification)

    def test_a_stored_payload_the_domain_would_reject_raises(self):
        payload = offer_to_payload(production_ready_offer())
        payload["delivery_specification"]["tenant_id"] = "client-other"

        with self.assertRaises(InvalidDeliverySpecificationError):
            offer_from_payload(payload)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
