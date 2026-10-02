"""Behavioral tests for the OfferVersion aggregate (pure domain, Commercial).

Rules under test come from SPEC.md sections 3, 4 and 11:
- OfferVersion records audience, promise, eligibility, price hypothesis and
  method refs (SPEC.md section 3 aggregate table).
- "Production requires approved dependencies" (SPEC.md section 3).
- An offer cannot become production ready without an approved method
  (Phase 3 TDD example) and pins the exact method version and intended use.
- "Changing an approved upstream method ... dependent offers ... are marked
  review required" (SPEC.md section 4).
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.commercial.domain.entities import OfferVersion
from redops.contexts.commercial.domain.errors import (
    InvalidOfferError,
    OfferReadinessError,
)
from redops.contexts.commercial.domain.value_objects import (
    MethodReference,
    OfferState,
)
from redops.contexts.method.domain.entities import MethodVersion
from redops.contexts.method.domain.value_objects import SemanticVersion

from ..method.fixtures import diagnostic_model, primary_currency

TODAY = date(2026, 10, 2)
USE = "3f pilot campaign"


def approved_method(
    version: SemanticVersion = SemanticVersion(1, 0, 0),
    tenant_id: str = "client-3f",
    method_id: str = "method-3f",
    intended_use: str = USE,
) -> MethodVersion:
    return MethodVersion(
        method_id=method_id,
        tenant_id=tenant_id,
        parent_method="signature-solution",
        semantic_version=version,
        stages=("diagnose", "position", "model"),
        currency="qualified-referrals",
        claims=frozenset({"claim-1"}),
        primary_currency=primary_currency(tenant_id),
        diagnostic_model=diagnostic_model(tenant_id),
    ).approve(approved_by="client-authority", intended_use=intended_use, on=TODAY)


def offer_version(**overrides) -> OfferVersion:
    values = {
        "offer_id": "offer-1",
        "tenant_id": "client-3f",
        "audience": "owner-operators",
        "promise": "twice the qualified referrals",
        "eligibility": "service businesses with a proven offer",
        "price_hypothesis": "USD 7,500",
        "method_refs": (
            MethodReference(
                method_id="method-3f",
                version=SemanticVersion(1, 0, 0),
                intended_use=USE,
            ),
        ),
        "owner": "offer-owner",
    }
    values.update(overrides)
    return OfferVersion(**values)


class OfferVersionInvariantTests(unittest.TestCase):
    def test_an_offer_records_its_required_fields(self):
        offer = offer_version()

        self.assertEqual("owner-operators", offer.audience)
        self.assertEqual("twice the qualified referrals", offer.promise)
        self.assertEqual("USD 7,500", offer.price_hypothesis)
        self.assertEqual(1, len(offer.method_refs))
        self.assertIs(OfferState.DRAFT, offer.state)
        self.assertFalse(offer.is_production_ready)

    def test_an_offer_without_audience_promise_eligibility_or_price_is_rejected(self):
        for override in (
            {"audience": "  "},
            {"promise": ""},
            {"eligibility": ""},
            {"price_hypothesis": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidOfferError):
                    offer_version(**override)

    def test_an_offer_without_a_method_reference_is_rejected(self):
        with self.assertRaises(InvalidOfferError):
            offer_version(method_refs=())

    def test_a_method_reference_requires_an_id_and_intended_use(self):
        with self.assertRaises(InvalidOfferError):
            MethodReference("", SemanticVersion(1, 0, 0), USE)
        with self.assertRaises(InvalidOfferError):
            MethodReference("method-3f", SemanticVersion(1, 0, 0), "   ")


class OfferProductionReadinessTests(unittest.TestCase):
    def test_an_offer_becomes_production_ready_with_its_approved_method(self):
        offer = offer_version()

        ready = offer.require_production_ready([approved_method()])

        self.assertTrue(ready.is_production_ready)
        self.assertIs(OfferState.PRODUCTION_READY, ready.state)
        self.assertFalse(offer.is_production_ready)

    def test_an_offer_without_an_approved_method_cannot_be_production_ready(self):
        offer = offer_version()

        with self.assertRaises(OfferReadinessError):
            offer.require_production_ready([])

    def test_an_offer_cannot_use_a_method_approved_for_a_different_version(self):
        offer = offer_version()

        with self.assertRaises(OfferReadinessError):
            offer.require_production_ready([approved_method(SemanticVersion(1, 1, 0))])

    def test_an_offer_cannot_use_a_method_approved_for_a_different_intended_use(self):
        offer = offer_version()

        with self.assertRaises(OfferReadinessError):
            offer.require_production_ready(
                [approved_method(intended_use="another engagement")]
            )

    def test_an_offer_cannot_use_another_tenants_approved_method(self):
        offer = offer_version()

        with self.assertRaises(OfferReadinessError):
            offer.require_production_ready([approved_method(tenant_id="client-other")])

    def test_a_production_ready_offer_is_immutable(self):
        ready = offer_version().require_production_ready([approved_method()])

        with self.assertRaises(FrozenInstanceError):
            ready.audience = "tampered"

    def test_a_terminal_offer_cannot_become_production_ready(self):
        offer = offer_version(state=OfferState.SUPERSEDED)

        with self.assertRaises(OfferReadinessError):
            offer.require_production_ready([approved_method()])


class OfferChangeImpactTests(unittest.TestCase):
    def test_an_upstream_method_change_marks_the_offer_review_required(self):
        ready = offer_version().require_production_ready([approved_method()])

        marked = ready.mark_review_required(
            reason="upstream method advanced to 1.1.0"
        )

        self.assertIs(OfferState.REVIEW_REQUIRED, marked.state)
        self.assertFalse(marked.is_production_ready)
        self.assertTrue(marked.review_reason)

    def test_marking_review_required_needs_a_reason(self):
        with self.assertRaises(InvalidOfferError):
            offer_version().mark_review_required(reason="  ")

    def test_a_superseded_offer_cannot_be_marked_review_required(self):
        with self.assertRaises(InvalidOfferError):
            offer_version(state=OfferState.SUPERSEDED).mark_review_required(
                reason="late change"
            )


if __name__ == "__main__":
    unittest.main()
