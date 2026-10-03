"""Behavioral tests for the canon funnel finder (Commercial domain).

Rules under test come from SPEC.md section 12.5 (the positioning and decision
tools are a canon gap) and the pre-stage-8 selection, shaped by the canon's
funnel finder (canon files 13 and 14):

- The tool helps decide "which type of marketing system or funnel to deploy"
  and is "based on the technical level ... how experienced you are, the pricing
  of your offer ... And then the business model" (canon file 13).
- The canon enumerates the funnel types it trains its community on: liquid
  funnels for low-end products, local funnels for retail or professional
  services, the CAC (coach, agency, consultant) funnel, webinar, quiz and
  launch funnels (canon file 13).
- A sales-call funnel does not fit a low-ticket offer ("it doesn't make sense
  to do a sales call to sell a product for $5") and a quick self-serve funnel
  does not fit a high-ticket consulting offer ("it doesn't make sense to try to
  sell a $20,000 consulting package online with a quick video sales letter")
  (canon file 13).

The finder is a planning decision asset for the pre-stage-8 selection, not a new
required gate kind (a methodology-owner decision, SPEC.md section 12.5), and it
is never an observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    FunnelFinderObservationError,
    FunnelFinderTenantBoundaryError,
    FunnelFitError,
    InvalidFunnelFinderError,
)
from redops.contexts.commercial.domain.policies import FunnelSelectionPolicy
from redops.contexts.commercial.domain.value_objects import (
    FunnelFinder,
    FunnelProfile,
    FunnelType,
    OfferPriceBand,
)

from .fixtures import TENANT


def profile(**overrides) -> FunnelProfile:
    values = {
        "profile_id": "profile-3f",
        "tenant_id": TENANT,
        "technical_level": "novice",
        "experience": "two years running a service business",
        "offer_price": OfferPriceBand.HIGH_TICKET,
        "business_model": "coach, agency or consultant",
    }
    values.update(overrides)
    return FunnelProfile(**values)


def finder(**overrides) -> FunnelFinder:
    values = {
        "finder_id": "finder-3f",
        "tenant_id": TENANT,
        "profile": profile(),
        "considered_types": (FunnelType.CAC, FunnelType.WEBINAR),
        "selected_type": FunnelType.CAC,
        "rationale": "a high-ticket consulting offer converts through a sales call",
    }
    values.update(overrides)
    return FunnelFinder(**values)


class FunnelProfileTests(unittest.TestCase):
    def test_a_profile_requires_every_canon_finder_factor(self):
        self.assertEqual("profile-3f", profile().profile_id)
        for override in (
            {"profile_id": ""},
            {"tenant_id": "  "},
            {"technical_level": ""},
            {"experience": "  "},
            {"business_model": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidFunnelFinderError):
                    profile(**override)

    def test_a_profile_requires_a_typed_offer_price_band(self):
        with self.assertRaises(InvalidFunnelFinderError):
            profile(offer_price="high ticket")

    def test_a_profile_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            profile().technical_level = "advanced"


class FunnelTypeTests(unittest.TestCase):
    def test_only_the_cac_funnel_converts_through_a_sales_call(self):
        self.assertTrue(FunnelType.CAC.requires_sales_conversation)
        for funnel_type in (
            FunnelType.LIQUID,
            FunnelType.LOCAL,
            FunnelType.WEBINAR,
            FunnelType.QUIZ,
            FunnelType.LAUNCH,
        ):
            with self.subTest(funnel_type=funnel_type):
                self.assertFalse(funnel_type.requires_sales_conversation)


class FunnelFinderTests(unittest.TestCase):
    def test_a_finder_selects_one_type_from_the_considered_types(self):
        decision = finder()

        self.assertEqual(FunnelType.CAC, decision.selected_type)
        self.assertEqual(2, len(decision.considered_types))

    def test_a_finder_requires_identity_profile_selection_and_rationale(self):
        for override in (
            {"finder_id": ""},
            {"tenant_id": "  "},
            {"profile": "high ticket consulting"},
            {"considered_types": ()},
            {"considered_types": (FunnelType.CAC,)},
            {"selected_type": "cac"},
            {"rationale": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidFunnelFinderError):
                    finder(**override)

    def test_a_finder_refuses_a_selected_type_not_among_the_considered(self):
        with self.assertRaises(InvalidFunnelFinderError):
            finder(selected_type=FunnelType.QUIZ)

    def test_a_finder_refuses_duplicate_considered_types(self):
        with self.assertRaises(InvalidFunnelFinderError):
            finder(considered_types=(FunnelType.CAC, FunnelType.CAC))

    def test_a_finder_refuses_a_cross_tenant_profile(self):
        with self.assertRaises(FunnelFinderTenantBoundaryError):
            finder(profile=profile(tenant_id="client-other"))

    def test_a_finder_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            finder().selected_type = FunnelType.WEBINAR

    def test_a_finder_is_never_an_observation(self):
        with self.assertRaises(FunnelFinderObservationError):
            finder().as_observation(claim_id="claim-1")


class FunnelSelectionPolicyTests(unittest.TestCase):
    def test_a_high_ticket_offer_with_a_sales_call_funnel_fits(self):
        FunnelSelectionPolicy().require_price_fit(finder())

    def test_a_high_ticket_offer_with_a_self_serve_funnel_is_refused(self):
        high_ticket_self_serve = finder(
            considered_types=(FunnelType.CAC, FunnelType.WEBINAR),
            selected_type=FunnelType.WEBINAR,
        )

        with self.assertRaises(FunnelFitError):
            FunnelSelectionPolicy().require_price_fit(high_ticket_self_serve)

    def test_a_low_ticket_offer_with_a_sales_call_funnel_is_refused(self):
        low_ticket_sales_call = finder(
            profile=profile(offer_price=OfferPriceBand.LOW_TICKET),
            considered_types=(FunnelType.CAC, FunnelType.LIQUID),
            selected_type=FunnelType.CAC,
        )

        with self.assertRaises(FunnelFitError):
            FunnelSelectionPolicy().require_price_fit(low_ticket_sales_call)

    def test_a_low_ticket_offer_with_a_self_serve_funnel_fits(self):
        low_ticket_self_serve = finder(
            profile=profile(offer_price=OfferPriceBand.LOW_TICKET),
            considered_types=(FunnelType.CAC, FunnelType.LIQUID),
            selected_type=FunnelType.LIQUID,
        )

        FunnelSelectionPolicy().require_price_fit(low_ticket_self_serve)


if __name__ == "__main__":
    unittest.main()
