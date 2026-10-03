"""Behavioral tests for the canon audience sizing research (Commercial domain).

Rules under test come from SPEC.md section 12.3, which maps audience sizing
research (Facebook Audience Insights and LinkedIn search) onto stage 1
"Diagnose" (canon files 02 and 03), and the canon's Market station gate that
"the market is big enough, reachable, and has a problem worth solving" (canon
README, citing canon files 02 and 03):

- The canon sizes a market with Facebook's free Audience Insights tool and
  records "one source and audience size" for a specific offer (canon file 02).
- It narrows the audience by location, age and gender and by specific interest
  signals -- experts, authors, books, tools, publications and associations --
  rather than broad interests (canon file 02).
- It confirms the market with the native LinkedIn search "in addition to
  Facebook ... just to make sure you're climbing the right mountain" (canon file
  03).
- The canon calls the sizing a rough first litmus test that will change ("it
  doesn't have to be perfect. You'll probably change it", canon file 02).

The estimate is a stage 1 research input with a named owner (SPEC.md section
12.4), not a new required gate kind (a methodology-owner decision), and it is
never an observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.commercial.domain.errors import (
    AudienceReachObservationError,
    InvalidAudienceReachError,
    MarketReachBoundaryError,
    MarketReachError,
)
from redops.contexts.commercial.domain.policies import MarketReachPolicy
from redops.contexts.commercial.domain.value_objects import (
    AudienceDefinition,
    AudienceReachEstimate,
    InterestKind,
    InterestSignal,
    ResearchPlatform,
)

from .fixtures import TENANT


def audience(**overrides) -> AudienceDefinition:
    values = {
        "location": "United States",
        "age": "30 to 55",
        "gender": "all genders",
        "interests": (
            InterestSignal(InterestKind.EXPERT, "a recognised industry expert"),
            InterestSignal(InterestKind.TOOL, "an email marketing tool"),
        ),
    }
    values.update(overrides)
    return AudienceDefinition(**values)


def estimate(**overrides) -> AudienceReachEstimate:
    values = {
        "estimate_id": "reach-3f",
        "tenant_id": TENANT,
        "owner": "discovery-and-diagnosis",
        "platform": ResearchPlatform.FACEBOOK_AUDIENCE_INSIGHTS,
        "audience": audience(),
        "estimated_reach": 1_000_000,
        "source_note": "Facebook Audience Insights, saved as the geek audience",
        "captured_on": date(2026, 10, 3),
    }
    values.update(overrides)
    return AudienceReachEstimate(**values)


class InterestSignalTests(unittest.TestCase):
    def test_a_signal_requires_a_typed_kind_and_a_value(self):
        signal = InterestSignal(InterestKind.AUTHOR, "a well known author")

        self.assertEqual(InterestKind.AUTHOR, signal.kind)
        self.assertEqual("a well known author", signal.value)

    def test_a_signal_requires_a_typed_canon_interest_kind(self):
        with self.assertRaises(InvalidAudienceReachError):
            InterestSignal(kind="author", value="a well known author")

    def test_a_signal_refuses_a_blank_value(self):
        for value in ("", "   "):
            with self.subTest(value=value):
                with self.assertRaises(InvalidAudienceReachError):
                    InterestSignal(InterestKind.BOOK, value)

    def test_a_signal_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            InterestSignal(InterestKind.TOOL, "a tool").value = "another tool"


class AudienceDefinitionTests(unittest.TestCase):
    def test_an_audience_requires_location_age_and_gender(self):
        self.assertEqual("United States", audience().location)
        for override in (
            {"location": ""},
            {"age": "  "},
            {"gender": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidAudienceReachError):
                    audience(**override)

    def test_an_audience_requires_at_least_one_specific_interest(self):
        with self.assertRaises(InvalidAudienceReachError):
            audience(interests=())

    def test_an_audience_requires_typed_interest_signals(self):
        with self.assertRaises(InvalidAudienceReachError):
            audience(interests=("a broad interest",))

    def test_an_audience_refuses_a_duplicate_interest_signal(self):
        duplicate = (
            InterestSignal(InterestKind.EXPERT, "an expert"),
            InterestSignal(InterestKind.EXPERT, "An Expert"),
        )

        with self.assertRaises(InvalidAudienceReachError):
            audience(interests=duplicate)

    def test_an_audience_allows_the_same_value_under_different_kinds(self):
        distinct = (
            InterestSignal(InterestKind.AUTHOR, "the same name"),
            InterestSignal(InterestKind.EXPERT, "the same name"),
        )

        self.assertEqual(2, len(audience(interests=distinct).interests))

    def test_an_audience_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            audience().location = "Canada"


class AudienceReachEstimateTests(unittest.TestCase):
    def test_an_estimate_records_the_canon_sizing_content(self):
        sizing = estimate()

        self.assertEqual(ResearchPlatform.FACEBOOK_AUDIENCE_INSIGHTS, sizing.platform)
        self.assertEqual(1_000_000, sizing.estimated_reach)
        self.assertEqual(TENANT, sizing.tenant_id)
        self.assertEqual("discovery-and-diagnosis", sizing.owner)

    def test_an_estimate_requires_identity_owner_and_source_note(self):
        for override in (
            {"estimate_id": ""},
            {"tenant_id": "  "},
            {"owner": ""},
            {"source_note": "   "},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidAudienceReachError):
                    estimate(**override)

    def test_an_estimate_requires_a_typed_research_platform(self):
        with self.assertRaises(InvalidAudienceReachError):
            estimate(platform="facebook")

    def test_an_estimate_requires_a_typed_audience_definition(self):
        with self.assertRaises(InvalidAudienceReachError):
            estimate(audience="owners over 30")

    def test_an_estimate_requires_a_positive_integer_reach(self):
        for reach in (0, -1, "1000", 1.5, True):
            with self.subTest(reach=reach):
                with self.assertRaises(InvalidAudienceReachError):
                    estimate(estimated_reach=reach)

    def test_an_estimate_requires_the_capture_date(self):
        with self.assertRaises(InvalidAudienceReachError):
            estimate(captured_on="2026-10-03")

    def test_an_estimate_is_the_canon_first_pass_litmus_test(self):
        sizing = estimate()

        self.assertTrue(sizing.is_litmus_test)
        self.assertTrue(sizing.is_plan)

    def test_an_estimate_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            estimate().estimated_reach = 2_000_000

    def test_an_estimate_is_never_an_observation(self):
        with self.assertRaises(AudienceReachObservationError):
            estimate().as_observation(claim_id="claim-1")


class MarketReachPolicyTests(unittest.TestCase):
    def test_a_market_at_or_above_the_minimum_is_reachable(self):
        MarketReachPolicy().require_reachable(estimate(), minimum_reach=1_000_000)
        MarketReachPolicy().require_reachable(estimate(), minimum_reach=500_000)

    def test_a_market_below_the_minimum_is_refused(self):
        with self.assertRaises(MarketReachError):
            MarketReachPolicy().require_reachable(
                estimate(estimated_reach=10_000), minimum_reach=100_000
            )

    def test_reach_requires_a_positive_minimum(self):
        for minimum in (0, -5, "1000", True):
            with self.subTest(minimum=minimum):
                with self.assertRaises(MarketReachError):
                    MarketReachPolicy().require_reachable(
                        estimate(), minimum_reach=minimum
                    )

    def test_a_market_confirmed_on_two_networks_is_reachable(self):
        facebook = estimate()
        linkedin = estimate(
            estimate_id="reach-3f-linkedin",
            platform=ResearchPlatform.LINKEDIN_SEARCH,
            estimated_reach=90_000,
        )

        MarketReachPolicy().require_multiplatform((facebook, linkedin))

    def test_a_single_platform_litmus_is_refused(self):
        for estimates in ((), (estimate(),)):
            with self.subTest(estimates=estimates):
                with self.assertRaises(MarketReachError):
                    MarketReachPolicy().require_multiplatform(estimates)

    def test_a_multi_network_confirmation_must_size_one_client(self):
        facebook = estimate()
        linkedin = estimate(
            estimate_id="reach-other-client-linkedin",
            tenant_id="another-client",
            platform=ResearchPlatform.LINKEDIN_SEARCH,
            estimated_reach=90_000,
        )

        with self.assertRaises(MarketReachBoundaryError):
            MarketReachPolicy().require_multiplatform((facebook, linkedin))

    def test_a_multi_network_confirmation_requires_typed_estimates(self):
        with self.assertRaises(MarketReachBoundaryError):
            MarketReachPolicy().require_multiplatform(
                (estimate(), "a LinkedIn search screenshot")
            )


if __name__ == "__main__":
    unittest.main()
