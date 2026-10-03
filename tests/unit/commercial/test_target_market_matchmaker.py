"""Behavioral tests for the canon target market matchmaker (Commercial domain).

Rules under test come from SPEC.md section 12.5 (the positioning and decision
tools are a canon gap) and the stage 1/stage 2 gate contract, shaped by the
canon's target market matchmaker (canon file 00):

- The tool takes two or three candidate target markets and narrows them to the
  one to serve now (canon file 00: "take maybe two or three potential target
  markets and narrow it down to the one you should be serving now").
- Each candidate is judged on the same dimensions: an audience you are
  passionate to help, a clear problem the offer solves, real profit, a place
  where you can have a presence and be known to them, and a clear pathway from
  point A to point B (canon file 00).
- The awareness research (canon file 04) places the chosen market, and the canon
  does not target the completely unaware initially, so a chosen market whose
  awareness position is the completely unaware cannot be served now.

The matchmaker is a planning decision asset for stages 1 and 2. Per the owner
decision in SPEC.md section 12.5 a canon-informed asset already implemented
becomes a required asset kind of its target stage gate in stage order, so it is
pinned as the stage 1 ``target-market-match`` kind, and it is never an
observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    InvalidTargetMarketMatchmakerError,
    TargetMarketMatchError,
    TargetMarketObservationError,
    TargetMarketTenantBoundaryError,
)
from redops.contexts.commercial.domain.policies import TargetMarketMatchPolicy
from redops.contexts.commercial.domain.value_objects import (
    MarketAwarenessLevel,
    MarketAwarenessMap,
    TargetMarketCandidate,
    TargetMarketMatchmaker,
)

from .fixtures import TENANT


def awareness_map(**overrides) -> MarketAwarenessMap:
    values = {
        "map_id": "awareness-3f",
        "tenant_id": TENANT,
        "primary_level": MarketAwarenessLevel.PROBLEM_AWARE,
        "research_evidence": ("owner-operators ask how to get steady referrals",),
        "message_requirements": ("name the problem they already feel",),
    }
    values.update(overrides)
    return MarketAwarenessMap(**values)


def candidate(market_id: str = "market-referrals", **overrides):
    values = {
        "market_id": market_id,
        "name": "Referral-starved service business owners",
        "passion": "we have run this play inside the trade",
        "problem": "unpredictable referral flow",
        "profit": "they already spend on lead generation",
        "reachability": "active in two owner-operator communities",
        "pathway": "from a referral drought to a referral partner engine",
    }
    values.update(overrides)
    return TargetMarketCandidate(**values)


def matchmaker(**overrides) -> TargetMarketMatchmaker:
    values = {
        "matchmaker_id": "match-3f",
        "tenant_id": TENANT,
        "candidates": (
            candidate(),
            candidate(
                market_id="market-coaches",
                name="New executive coaches",
                problem="no repeatable client acquisition",
            ),
        ),
        "selected_market_id": "market-referrals",
        "awareness_map": awareness_map(),
    }
    values.update(overrides)
    return TargetMarketMatchmaker(**values)


class TargetMarketCandidateTests(unittest.TestCase):
    def test_a_candidate_requires_every_canon_match_criterion(self):
        self.assertEqual("market-referrals", candidate().market_id)
        for override in (
            {"market_id": ""},
            {"name": "  "},
            {"passion": ""},
            {"problem": "  "},
            {"profit": ""},
            {"reachability": "  "},
            {"pathway": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidTargetMarketMatchmakerError):
                    candidate(**override)

    def test_a_candidate_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            candidate().passion = "changed"


class TargetMarketMatchmakerTests(unittest.TestCase):
    def test_a_match_narrows_candidates_to_the_one_selected_market(self):
        match = matchmaker()

        self.assertEqual(
            "Referral-starved service business owners", match.selected_market.name
        )
        self.assertEqual(2, len(match.candidates))

    def test_a_match_requires_identity_candidates_and_a_selected_market(self):
        for override in (
            {"matchmaker_id": ""},
            {"tenant_id": "  "},
            {"candidates": ()},
            {"candidates": (candidate(),)},
            {"selected_market_id": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidTargetMarketMatchmakerError):
                    matchmaker(**override)

    def test_a_match_refuses_a_selected_market_not_among_the_candidates(self):
        with self.assertRaises(InvalidTargetMarketMatchmakerError):
            matchmaker(selected_market_id="market-does-not-exist")

    def test_a_match_refuses_duplicate_candidate_ids(self):
        with self.assertRaises(InvalidTargetMarketMatchmakerError):
            matchmaker(
                candidates=(candidate(), candidate()),
            )

    def test_a_match_refuses_a_cross_tenant_awareness_map(self):
        with self.assertRaises(TargetMarketTenantBoundaryError):
            matchmaker(awareness_map=awareness_map(tenant_id="client-other"))

    def test_a_match_refuses_an_untyped_awareness_map(self):
        with self.assertRaises(InvalidTargetMarketMatchmakerError):
            matchmaker(awareness_map="problem aware")

    def test_a_match_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            matchmaker().selected_market_id = "market-coaches"

    def test_a_match_projects_onto_the_stage_one_gate_kind(self):
        asset = matchmaker().as_stage_asset(version=3)

        self.assertEqual("target-market-match", asset.kind)
        self.assertEqual("match-3f", asset.asset_id)
        self.assertEqual(3, asset.version)

    def test_a_versionless_match_projection_is_refused(self):
        with self.assertRaises(InvalidTargetMarketMatchmakerError):
            matchmaker().as_stage_asset(version=0)

    def test_a_match_is_never_an_observation(self):
        with self.assertRaises(TargetMarketObservationError):
            matchmaker().as_observation(claim_id="claim-1")


class TargetMarketMatchPolicyTests(unittest.TestCase):
    def test_a_match_to_a_targetable_market_is_servable_now(self):
        TargetMarketMatchPolicy().require_servable(matchmaker())

    def test_a_match_to_the_completely_unaware_market_is_refused(self):
        unaware = matchmaker(
            awareness_map=awareness_map(
                primary_level=MarketAwarenessLevel.COMPLETELY_UNAWARE
            )
        )

        with self.assertRaises(TargetMarketMatchError):
            TargetMarketMatchPolicy().require_servable(unaware)


if __name__ == "__main__":
    unittest.main()
