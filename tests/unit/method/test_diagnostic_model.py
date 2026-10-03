"""Behavioral tests for the stage 3 DiagnosticModel rule (pure domain, Method).

Rules under test come from SPEC.md section 4, stage 3 "Model" and its "Diagnostic
Model Approved" checkpoint: the Profit Pyramid levels, per level observable
measures, symptoms, behaviors and problems, and progression; the checkpoint
requires that "a prospect can recognize their current level and desired next
level using observable differences". Phase 3 TDD example: "pyramid levels
require observable differences". A level whose observable signature is identical
to its neighbor cannot be told apart, so a model containing such levels cannot
represent an approved diagnostic model or be pinned as stage 3 gate evidence.
"""

import unittest
from dataclasses import FrozenInstanceError, replace

from redops.contexts.method.domain.entities import DiagnosticModel
from redops.contexts.method.domain.errors import (
    InvalidDiagnosticModelError,
    InvalidMethodError,
    InvalidProfitPyramidLevelError,
)
from redops.contexts.method.domain.value_objects import ProfitPyramidLevel


def level(
    level_id: str = "level-1",
    *,
    name: str = "Stuck",
    observable_measures: tuple[str, ...] = ("under 4 qualified referrals per month",),
    symptoms: tuple[str, ...] = ("pipeline dries up between projects",),
    behaviors: tuple[str, ...] = ("trades more hours for fewer leads",),
    problems: tuple[str, ...] = ("no predictable growth",),
    tenant_id: str = "client-3f",
) -> ProfitPyramidLevel:
    return ProfitPyramidLevel(
        level_id=level_id,
        tenant_id=tenant_id,
        name=name,
        observable_measures=observable_measures,
        symptoms=symptoms,
        behaviors=behaviors,
        problems=problems,
    )


def scaling_level(level_id: str = "level-2") -> ProfitPyramidLevel:
    return level(
        level_id,
        name="Scaling",
        observable_measures=("12 or more qualified referrals per month",),
        symptoms=("demand exceeds delivery capacity",),
        behaviors=("delegates delivery to trained staff",),
        problems=("protecting margin while adding capacity",),
    )


def diagnostic_model(levels: tuple[ProfitPyramidLevel, ...] | None = None) -> DiagnosticModel:
    return DiagnosticModel(
        model_id="model-3f",
        tenant_id="client-3f",
        name="Growth Pyramid",
        levels=levels if levels is not None else (level(), scaling_level()),
        progression="climb from Stuck to Scaling by installing the referral network",
        qualification_logic="rank the prospect by observable monthly referral count",
        visual="asset://diagnostic/3f-growth-pyramid.png",
        explanatory_copy=(
            "Four levels from Stuck to Scaling, each placed by observable "
            "monthly referral count"
        ),
    )


class ProfitPyramidLevelTests(unittest.TestCase):
    def test_a_level_records_its_observable_criteria(self):
        candidate = level()

        self.assertEqual("Stuck", candidate.name)
        self.assertEqual(("under 4 qualified referrals per month",), candidate.observable_measures)
        self.assertEqual(("pipeline dries up between projects",), candidate.symptoms)
        self.assertEqual(("trades more hours for fewer leads",), candidate.behaviors)
        self.assertEqual(("no predictable growth",), candidate.problems)

    def test_a_level_missing_an_observable_dimension_is_rejected(self):
        for override in (
            {"observable_measures": ()},
            {"symptoms": ()},
            {"behaviors": ()},
            {"problems": ()},
            {"observable_measures": ("   ",)},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidProfitPyramidLevelError):
                    level(**override)

    def test_a_level_without_an_identity_is_rejected(self):
        for override in ({"level_id": ""}, {"name": "  "}, {"tenant_id": ""}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidProfitPyramidLevelError):
                    level(**override)

    def test_a_level_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            level().name = "tampered"


class DiagnosticModelCheckpointTests(unittest.TestCase):
    def test_a_model_records_its_levels_progression_and_qualification_logic(self):
        model = diagnostic_model()

        self.assertEqual("Growth Pyramid", model.name)
        self.assertEqual(2, len(model.levels))
        self.assertTrue(model.progression)
        self.assertTrue(model.qualification_logic)

    def test_a_model_records_its_visual_and_explanatory_copy(self):
        model = diagnostic_model()

        self.assertEqual(
            "asset://diagnostic/3f-growth-pyramid.png", model.visual
        )
        self.assertTrue(model.explanatory_copy)

    def test_a_model_missing_its_visual_or_copy_is_rejected(self):
        for override in ({"visual": ""}, {"explanatory_copy": "  "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidMethodError):
                    replace(diagnostic_model(), **override)

    def test_a_model_requires_at_least_two_levels(self):
        for levels in ((), (level(),)):
            with self.subTest(count=len(levels)):
                with self.assertRaises(InvalidDiagnosticModelError):
                    diagnostic_model(levels)

    def test_adjacent_levels_with_identical_observable_signatures_are_rejected(self):
        twin = level("level-2", name="Also Stuck")

        with self.assertRaises(InvalidDiagnosticModelError):
            diagnostic_model((level(), twin))

    def test_adjacent_levels_differing_in_any_observable_dimension_are_accepted(self):
        same_symptoms = level(
            "level-2",
            name="Aligned",
            observable_measures=("12 or more qualified referrals per month",),
            symptoms=level().symptoms,
            behaviors=level().behaviors,
            problems=level().problems,
        )

        model = diagnostic_model((level(), same_symptoms))

        self.assertEqual(2, len(model.levels))

    def test_a_model_cannot_mix_levels_from_another_tenant(self):
        foreign = scaling_level("level-foreign")
        foreign = ProfitPyramidLevel(
            level_id=foreign.level_id,
            tenant_id="client-other",
            name=foreign.name,
            observable_measures=foreign.observable_measures,
            symptoms=foreign.symptoms,
            behaviors=foreign.behaviors,
            problems=foreign.problems,
        )

        with self.assertRaises(InvalidDiagnosticModelError):
            diagnostic_model((level(), foreign))

    def test_a_model_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            diagnostic_model().name = "tampered"


if __name__ == "__main__":
    unittest.main()
