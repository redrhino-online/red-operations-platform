"""Behavioral tests for the canon market awareness map (Commercial domain).

Rules under test come from SPEC.md section 12.3 (stage 1 "Diagnose" uses canon
files 02, 03 and 04) and section 12.5 (the positioning and decision tools are a
canon gap), shaped by the canon's five levels of market awareness (canon file 04):

- Awareness is a five level progression: completely unaware, problem aware,
  solution aware, product aware and most aware (canon file 04: "there's people
  that are completely unaware... Problem aware... Solution aware... Product
  aware... the most aware").
- You must understand where the prospect sits before doing research or shaping a
  message (canon file 04: "you have to understand where your prospect is").
- The completely unaware are explicitly not the initial target (canon file 04:
  "which is who we definitely do not want to sell to initially"), while the goal
  is a market actively seeking a solution (canon file 04: "we want to go after
  people that know they're trying to actively seek a solution").
- The message depends on the level: product aware prospects need their decision
  educated and reinforced, and the most aware only need the deal (canon file 04).
- The place a prospect sits comes from real research material, not assertion
  (canon file 04: Amazon reviews, Quora, Reddit, Facebook groups and Google
  search are used to read the language and currency of the market).

The map is a decision asset that grounds the stage 1 ``awareness-map`` canonical
kind; it is never an observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    InvalidMarketAwarenessMapError,
    MarketAwarenessTargetingError,
)
from redops.contexts.commercial.domain.policies import MarketAwarenessPolicy
from redops.contexts.commercial.domain.value_objects import (
    AWARENESS_MAP_KIND,
    MarketAwarenessLevel,
    MarketAwarenessMap,
)

from .fixtures import TENANT


def awareness_map(**overrides) -> MarketAwarenessMap:
    values = {
        "map_id": "awareness-3f",
        "tenant_id": TENANT,
        "primary_level": MarketAwarenessLevel.PROBLEM_AWARE,
        "research_evidence": (
            "amazon reviews name the referral drought",
            "facebook group posts ask how to get steady referrals",
        ),
        "message_requirements": (
            "name the problem they already feel",
            "show that a solution exists",
        ),
    }
    values.update(overrides)
    return MarketAwarenessMap(**values)


class MarketAwarenessLevelTests(unittest.TestCase):
    def test_the_five_canon_levels_are_named(self):
        self.assertEqual(
            {
                "completely_unaware",
                "problem_aware",
                "solution_aware",
                "product_aware",
                "most_aware",
            },
            {level.value for level in MarketAwarenessLevel},
        )

    def test_levels_are_ordered_from_least_to_most_aware(self):
        self.assertEqual(0, MarketAwarenessLevel.COMPLETELY_UNAWARE.rank)
        self.assertEqual(1, MarketAwarenessLevel.PROBLEM_AWARE.rank)
        self.assertEqual(2, MarketAwarenessLevel.SOLUTION_AWARE.rank)
        self.assertEqual(3, MarketAwarenessLevel.PRODUCT_AWARE.rank)
        self.assertEqual(4, MarketAwarenessLevel.MOST_AWARE.rank)

    def test_only_the_completely_unaware_are_not_initially_targetable(self):
        self.assertFalse(
            MarketAwarenessLevel.COMPLETELY_UNAWARE.is_initially_targetable
        )
        for level in (
            MarketAwarenessLevel.PROBLEM_AWARE,
            MarketAwarenessLevel.SOLUTION_AWARE,
            MarketAwarenessLevel.PRODUCT_AWARE,
            MarketAwarenessLevel.MOST_AWARE,
        ):
            with self.subTest(level=level):
                self.assertTrue(level.is_initially_targetable)


class MarketAwarenessMapTests(unittest.TestCase):
    def test_a_complete_map_records_level_evidence_and_message_requirements(self):
        awareness = awareness_map()

        self.assertEqual(
            MarketAwarenessLevel.PROBLEM_AWARE, awareness.primary_level
        )
        self.assertEqual(
            "amazon reviews name the referral drought",
            awareness.research_evidence[0],
        )
        self.assertEqual(
            "name the problem they already feel",
            awareness.message_requirements[0],
        )

    def test_a_map_without_identity_level_evidence_or_requirements_is_rejected(self):
        for override in (
            {"map_id": ""},
            {"tenant_id": "   "},
            {"primary_level": "problem-aware"},
            {"research_evidence": ()},
            {"research_evidence": ("  ",)},
            {"message_requirements": ()},
            {"message_requirements": ("  ",)},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidMarketAwarenessMapError):
                    awareness_map(**override)

    def test_a_map_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            awareness_map().primary_level = MarketAwarenessLevel.MOST_AWARE

    def test_a_map_projects_to_the_canonical_awareness_map_kind(self):
        awareness = awareness_map()

        asset = awareness.as_stage_asset(version=2)

        self.assertEqual("awareness-map", AWARENESS_MAP_KIND)
        self.assertEqual(awareness.map_id, asset.asset_id)
        self.assertEqual(TENANT, asset.tenant_id)
        self.assertEqual("awareness-map", asset.kind)
        self.assertEqual(2, asset.version)

    def test_a_map_refuses_a_versionless_stage_asset(self):
        for version in (0, -1):
            with self.subTest(version=version):
                with self.assertRaises(InvalidMarketAwarenessMapError):
                    awareness_map().as_stage_asset(version=version)


class MarketAwarenessPolicyTests(unittest.TestCase):
    def test_a_map_at_a_targetable_level_is_accepted(self):
        MarketAwarenessPolicy().require_targetable(awareness_map())

    def test_a_map_targeting_the_completely_unaware_is_refused(self):
        untargetable = awareness_map(
            primary_level=MarketAwarenessLevel.COMPLETELY_UNAWARE
        )

        with self.assertRaises(MarketAwarenessTargetingError):
            MarketAwarenessPolicy().require_targetable(untargetable)

    def test_a_retarget_level_must_be_more_aware_than_the_primary_level(self):
        invalid = (
            MarketAwarenessLevel.PROBLEM_AWARE,
            MarketAwarenessLevel.COMPLETELY_UNAWARE,
        )
        for retarget in invalid:
            with self.subTest(retarget=retarget):
                with self.assertRaises(MarketAwarenessTargetingError):
                    awareness_map(retarget_level=retarget)

    def test_a_map_with_a_more_aware_retarget_level_is_accepted(self):
        awareness = awareness_map(
            primary_level=MarketAwarenessLevel.SOLUTION_AWARE,
            retarget_level=MarketAwarenessLevel.MOST_AWARE,
        )

        self.assertEqual(
            MarketAwarenessLevel.MOST_AWARE, awareness.retarget_level
        )
        MarketAwarenessPolicy().require_targetable(awareness)


if __name__ == "__main__":
    unittest.main()
