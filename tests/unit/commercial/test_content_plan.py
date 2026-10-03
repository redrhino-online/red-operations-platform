"""Behavioral tests for the Extract content plan (Commercial domain).

Rules under test come from SPEC.md section 12.5 (the Extract motion is a canon
gap recorded in the implementation plan's canon gap register: "pull key ideas
from the signature solution ... group themes around the one currency, and build
an email and social content plan") and section 12.3 (stage 6 uses canon files
25-28). The canon's Content Blitz shapes the extract sources and the method
grounding:

- Content never leaves the method: "we're forbidding you to create content that
  doesn't live inside your signature solution" (canon file 27) and "we never
  create a piece of content that doesn't live in the signature solution" (canon
  file 28).
- The plan is built from the questions the audience asks about each step: "just
  brainstorming FAQs and questions you already know your audience is asking"
  (canon file 27).
- The ideas group around the one currency and become an email and social plan
  (SPEC.md section 12.5).

The plan is a stage 6 planning asset, not a new required gate kind. It does not
authorize publishing or spend (SPEC.md sections 4 and 9) and it is never an
observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    ContentPlanDependencyError,
    ContentPlanObservationError,
    ContentPlanTenantBoundaryError,
    ContentPlanThemeError,
    InvalidContentPlanError,
)
from redops.contexts.commercial.domain.value_objects import (
    CONTENT_PLAN_CANON_REFERENCE,
    ContentIdea,
    ContentIdeaSource,
    ContentPlan,
    ContentPlanChannel,
    ContentTheme,
)

from .fixtures import TENANT
from ..method.fixtures import primary_currency, signature_solution


def content_theme(**overrides) -> ContentTheme:
    values = {
        "theme_id": "theme-problem",
        "tenant_id": TENANT,
        "name": "referral drought",
        "currency_measure": "4 qualified referrals per month",
    }
    values.update(overrides)
    return ContentTheme(**values)


def content_idea(**overrides) -> ContentIdea:
    values = {
        "idea_id": "idea-diagnose",
        "tenant_id": TENANT,
        "signature_step": "Diagnose",
        "source": ContentIdeaSource.FAQ,
        "prompt": "why do my referrals stop at four a month?",
        "theme_id": "theme-problem",
        "channels": (ContentPlanChannel.EMAIL,),
    }
    values.update(overrides)
    return ContentIdea(**values)


def content_plan(**overrides) -> ContentPlan:
    values = {
        "plan_id": "plan-3f",
        "tenant_id": TENANT,
        "owner": "content-operator",
        "method": signature_solution(),
        "currency": primary_currency(),
        "themes": (
            content_theme(),
            content_theme(
                theme_id="theme-outcome",
                name="referral engine",
                currency_measure="12 qualified referrals per month",
            ),
        ),
        "ideas": (
            content_idea(),
            content_idea(
                idea_id="idea-position",
                signature_step="Position",
                source=ContentIdeaSource.PROBLEM,
                prompt="which referral outcome should I measure?",
                theme_id="theme-outcome",
                channels=(ContentPlanChannel.SOCIAL,),
            ),
        ),
    }
    values.update(overrides)
    return ContentPlan(**values)


class ContentIdeaSourceTests(unittest.TestCase):
    def test_the_extract_sources_are_named(self):
        self.assertEqual(
            {"faq", "problem", "process", "review_and_praise"},
            {source.value for source in ContentIdeaSource},
        )

    def test_the_canon_reference_is_recorded(self):
        self.assertEqual("25, 27, 28", CONTENT_PLAN_CANON_REFERENCE)


class ContentPlanChannelTests(unittest.TestCase):
    def test_the_two_extract_deliveries_are_named(self):
        self.assertEqual(
            {"email", "social"},
            {channel.value for channel in ContentPlanChannel},
        )


class ContentThemeTests(unittest.TestCase):
    def test_a_theme_requires_its_identity_name_and_currency_measure(self):
        for override in (
            {"theme_id": ""},
            {"tenant_id": ""},
            {"name": ""},
            {"currency_measure": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidContentPlanError):
                    content_theme(**override)


class ContentIdeaTests(unittest.TestCase):
    def test_an_idea_requires_its_identity_step_prompt_and_theme(self):
        for override in (
            {"idea_id": ""},
            {"tenant_id": ""},
            {"signature_step": ""},
            {"prompt": ""},
            {"theme_id": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidContentPlanError):
                    content_idea(**override)

    def test_an_idea_requires_a_typed_source(self):
        with self.assertRaises(InvalidContentPlanError):
            content_idea(source="faq")

    def test_an_idea_requires_at_least_one_typed_channel(self):
        with self.assertRaises(InvalidContentPlanError):
            content_idea(channels=())
        with self.assertRaises(InvalidContentPlanError):
            content_idea(channels=("email",))

    def test_an_idea_refuses_a_duplicate_channel(self):
        with self.assertRaises(InvalidContentPlanError):
            content_idea(
                channels=(ContentPlanChannel.EMAIL, ContentPlanChannel.EMAIL)
            )


class ContentPlanTests(unittest.TestCase):
    def test_a_valid_plan_covers_its_steps_and_groups_its_ideas(self):
        plan = content_plan()
        self.assertEqual(("Diagnose", "Position"), plan.covered_steps)
        self.assertFalse(plan.is_complete)
        self.assertTrue(plan.is_plan)
        self.assertEqual(7, len(plan.missing_steps()))
        self.assertEqual(
            (content_idea().idea_id,),
            tuple(idea.idea_id for idea in plan.ideas_for_theme("theme-problem")),
        )

    def test_a_plan_requires_its_identity_owner(self):
        for override in (
            {"plan_id": ""},
            {"tenant_id": ""},
            {"owner": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidContentPlanError):
                    content_plan(**override)

    def test_a_plan_requires_a_typed_stage_four_solution(self):
        with self.assertRaises(ContentPlanDependencyError):
            content_plan(method="solution")

    def test_a_plan_requires_a_typed_stage_two_currency(self):
        with self.assertRaises(ContentPlanDependencyError):
            content_plan(currency="currency")

    def test_a_plan_refuses_a_method_or_currency_from_another_tenant(self):
        with self.assertRaises(ContentPlanTenantBoundaryError):
            content_plan(method=signature_solution("other-tenant"))
        with self.assertRaises(ContentPlanTenantBoundaryError):
            content_plan(currency=primary_currency("other-tenant"))

    def test_a_plan_refuses_a_theme_or_idea_from_another_tenant(self):
        with self.assertRaises(ContentPlanTenantBoundaryError):
            content_plan(themes=(content_theme(tenant_id="other-tenant"),))
        with self.assertRaises(ContentPlanTenantBoundaryError):
            content_plan(ideas=(content_idea(tenant_id="other-tenant"),))

    def test_a_plan_requires_at_least_one_theme_and_one_idea(self):
        with self.assertRaises(InvalidContentPlanError):
            content_plan(themes=())
        with self.assertRaises(InvalidContentPlanError):
            content_plan(ideas=())

    def test_a_plan_refuses_a_duplicate_theme_or_idea_id(self):
        with self.assertRaises(InvalidContentPlanError):
            content_plan(
                themes=(content_theme(), content_theme(name="duplicate name"))
            )
        with self.assertRaises(InvalidContentPlanError):
            content_plan(
                ideas=(content_idea(), content_idea(prompt="another question"))
            )

    def test_a_plan_requires_themes_to_group_around_the_locked_currency(self):
        with self.assertRaises(ContentPlanThemeError):
            content_plan(
                themes=(content_theme(currency_measure="99 referrals per month"),)
            )

    def test_a_plan_refuses_an_idea_from_a_step_the_solution_does_not_name(self):
        with self.assertRaises(ContentPlanDependencyError):
            content_plan(ideas=(content_idea(signature_step="Invent"),))

    def test_a_plan_refuses_an_idea_grouped_under_an_undeclared_theme(self):
        with self.assertRaises(InvalidContentPlanError):
            content_plan(ideas=(content_idea(theme_id="theme-missing"),))

    def test_a_plan_must_build_both_an_email_and_a_social_plan(self):
        with self.assertRaises(InvalidContentPlanError):
            content_plan(ideas=(content_idea(),))

    def test_a_plan_is_frozen(self):
        plan = content_plan()
        with self.assertRaises(FrozenInstanceError):
            plan.owner = "tampered"

    def test_a_plan_is_never_an_observation(self):
        with self.assertRaises(ContentPlanObservationError):
            content_plan().as_observation(claim_id="claim-1")


if __name__ == "__main__":
    unittest.main()
