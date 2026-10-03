"""Behavioral tests for the retargeting roadmap (Measurement domain).

Rules under test come from SPEC.md section 4, stage 8 ("Funnel Complete") and
stage 10 ("performance recommendations require evidence and owner approval before
material changes"), shaped by the canon's retargeting roadmap (canon files 33 and
34):

- The canon's six-step roadmap runs tracking code, then conversion goals, then
  retargeting lists, then focused campaigns, then effective ads, then metrics
  (canon file 34: "Step one Tracking code", "set up conversion goals", "create
  retargeting lists", "create super focused campaigns", "effective ads", "metrics").
  A tracking code and a goal must exist before a list or a campaign (canon file 34:
  "once you've pixeled them, you can go to step two... Create an audience... set up
  conversion goals").
- A list segments "user groups with a defined state within a defined stage of your
  funnel" (canon file 34).
- A campaign "should accomplish one goal at a time" and move people from one named
  funnel step to the next (canon file 34: "what ad will I present to get people
  from point A to point B").
- The roadmap is a plan; it is not an observed result (SPEC.md section 3 keeps
  observations distinct from conclusions).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.measurement.domain.errors import (
    InvalidRetargetingError,
    RetargetingDependencyError,
    RetargetingObservationError,
    RetargetingStepError,
    RetargetingTenantBoundaryError,
)
from redops.contexts.measurement.domain.value_objects import (
    ConversionGoal,
    MeasurementBasis,
    RetargetingAudience,
    RetargetingCampaign,
    RetargetingChannel,
    RetargetingPlan,
    RetargetingStep,
    TrackingCode,
)

TENANT = "client-3f"


def tracking_code(**overrides) -> TrackingCode:
    values = {
        "code_id": "pixel-3f",
        "tenant_id": TENANT,
        "provider": "perfect-audience",
        "pages": ("/opt-in", "/authority-amplifier", "/booking"),
    }
    values.update(overrides)
    return TrackingCode(**values)


def conversion_goal(**overrides) -> ConversionGoal:
    values = {
        "goal_id": "goal-lead",
        "tenant_id": TENANT,
        "name": "lead magnet opt in",
        "url": "/thank-you",
        "value": 10.0,
        "basis": MeasurementBasis.OBSERVED,
        "tracking_code": tracking_code(),
        "funnel_step": "lead",
    }
    values.update(overrides)
    return ConversionGoal(**values)


def retargeting_audience(**overrides) -> RetargetingAudience:
    values = {
        "audience_id": "list-opted-not-booked",
        "tenant_id": TENANT,
        "name": "opted in but did not book",
        "funnel_step": "lead",
        "achieved_goal": conversion_goal(),
        "lookback_days": 30,
        "tracking_code": tracking_code(),
    }
    values.update(overrides)
    return RetargetingAudience(**values)


def retargeting_campaign(**overrides) -> RetargetingCampaign:
    values = {
        "campaign_id": "campaign-book",
        "tenant_id": TENANT,
        "name": "nudge opted-in leads to book",
        "audience": retargeting_audience(),
        "from_step": "lead",
        "to_step": "appointment",
        "target_goal": conversion_goal(
            goal_id="goal-book",
            name="strategy session booked",
            url="/booked",
            funnel_step="appointment",
        ),
        "channel": RetargetingChannel.FACEBOOK_NEWSFEED,
    }
    values.update(overrides)
    return RetargetingCampaign(**values)


def retargeting_plan(**overrides) -> RetargetingPlan:
    values = {
        "plan_id": "retarget-3f",
        "tenant_id": TENANT,
        "owner": "campaign-operator",
        "tracking_code": tracking_code(),
        "goals": (
            conversion_goal(),
            conversion_goal(
                goal_id="goal-book",
                name="strategy session booked",
                url="/booked",
                funnel_step="appointment",
            ),
        ),
        "audiences": (retargeting_audience(),),
        "campaigns": (retargeting_campaign(),),
    }
    values.update(overrides)
    return RetargetingPlan(**values)


class TrackingCodeTests(unittest.TestCase):
    def test_a_tracking_code_names_its_provider_and_pages(self):
        code = tracking_code()

        self.assertEqual("perfect-audience", code.provider)
        self.assertEqual(
            ("/opt-in", "/authority-amplifier", "/booking"), code.pages
        )

    def test_a_tracking_code_requires_its_identification_fields(self):
        for field in ("code_id", "tenant_id", "provider"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidRetargetingError):
                    tracking_code(**{field: "  "})

    def test_a_tracking_code_is_installed_on_at_least_one_page(self):
        with self.assertRaises(InvalidRetargetingError):
            tracking_code(pages=())

    def test_a_tracking_code_rejects_a_blank_page(self):
        with self.assertRaises(InvalidRetargetingError):
            tracking_code(pages=("/opt-in", " "))

    def test_a_tracking_code_is_immutable(self):
        code = tracking_code()

        with self.assertRaises(FrozenInstanceError):
            code.provider = "other"


class ConversionGoalTests(unittest.TestCase):
    def test_a_goal_names_its_url_value_and_basis(self):
        goal = conversion_goal()

        self.assertEqual("/thank-you", goal.url)
        self.assertEqual(10.0, goal.value)
        self.assertIs(MeasurementBasis.OBSERVED, goal.basis)

    def test_a_goal_value_may_be_a_placeholder_estimate(self):
        goal = conversion_goal(
            value=5.0, basis=MeasurementBasis.PLACEHOLDER
        )

        self.assertTrue(goal.is_placeholder)

    def test_a_goal_requires_its_name_and_url(self):
        for field in ("goal_id", "tenant_id", "name", "url", "funnel_step"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidRetargetingError):
                    conversion_goal(**{field: "  "})

    def test_a_goal_value_cannot_be_negative(self):
        with self.assertRaises(InvalidRetargetingError):
            conversion_goal(value=-1.0)

    def test_a_goal_requires_the_matching_tracking_code_tenant(self):
        with self.assertRaises(RetargetingTenantBoundaryError):
            conversion_goal(tracking_code=tracking_code(tenant_id="other-client"))


class RetargetingAudienceTests(unittest.TestCase):
    def test_a_list_segments_a_defined_state_in_a_defined_step(self):
        audience = retargeting_audience()

        self.assertEqual("lead", audience.funnel_step)
        self.assertEqual("lead magnet opt in", audience.achieved_goal.name)
        self.assertEqual(30, audience.lookback_days)

    def test_a_list_needs_a_typed_achieved_goal(self):
        with self.assertRaises(RetargetingDependencyError):
            retargeting_audience(achieved_goal="lead magnet opt in")

    def test_a_list_needs_a_tracking_code(self):
        with self.assertRaises(RetargetingDependencyError):
            retargeting_audience(tracking_code="pixel-3f")

    def test_a_list_refuses_a_goal_from_another_tracking_code(self):
        with self.assertRaises(RetargetingDependencyError):
            retargeting_audience(
                achieved_goal=conversion_goal(
                    tracking_code=tracking_code(code_id="pixel-other")
                )
            )

    def test_a_list_segments_the_goal_recorded_at_its_own_step(self):
        with self.assertRaises(RetargetingStepError):
            retargeting_audience(
                achieved_goal=conversion_goal(
                    goal_id="goal-book",
                    name="strategy session booked",
                    url="/booked",
                    funnel_step="appointment",
                )
            )

    def test_a_list_lookback_window_must_be_positive(self):
        with self.assertRaises(InvalidRetargetingError):
            retargeting_audience(lookback_days=0)

    def test_a_list_cannot_cross_a_tenant_boundary(self):
        with self.assertRaises(RetargetingTenantBoundaryError):
            retargeting_audience(
                tenant_id="other-client",
                tracking_code=tracking_code(tenant_id="other-client"),
            )

    def test_a_list_requires_its_identification_fields(self):
        for field in ("audience_id", "tenant_id", "name", "funnel_step"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidRetargetingError):
                    retargeting_audience(**{field: "  "})


class RetargetingCampaignTests(unittest.TestCase):
    def test_a_campaign_moves_a_list_from_one_named_step_to_the_next(self):
        campaign = retargeting_campaign()

        self.assertIs(RetargetingChannel.FACEBOOK_NEWSFEED, campaign.channel)
        self.assertEqual("lead", campaign.from_step)
        self.assertEqual("appointment", campaign.to_step)

    def test_a_campaign_requires_a_named_next_step(self):
        with self.assertRaises(InvalidRetargetingError):
            retargeting_campaign(to_step="  ")

    def test_a_campaign_requires_a_typed_audience_list(self):
        with self.assertRaises(RetargetingDependencyError):
            retargeting_campaign(audience="list-opted-not-booked")

    def test_a_campaign_must_target_a_step_it_is_not_already_on(self):
        with self.assertRaises(RetargetingStepError):
            retargeting_campaign(to_step="lead")

    def test_a_campaign_must_start_from_its_lists_own_funnel_step(self):
        with self.assertRaises(RetargetingStepError):
            retargeting_campaign(from_step="webinar")

    def test_a_campaign_target_goal_must_share_the_list_tracking_code(self):
        with self.assertRaises(RetargetingDependencyError):
            retargeting_campaign(
                target_goal=conversion_goal(
                    tracking_code=tracking_code(code_id="pixel-other")
                )
            )

    def test_a_campaign_target_goal_must_be_recorded_at_its_target_step(self):
        with self.assertRaises(RetargetingStepError):
            retargeting_campaign(
                target_goal=conversion_goal(
                    goal_id="goal-book",
                    name="strategy session booked",
                    url="/booked",
                    funnel_step="lead",
                )
            )

    def test_a_campaign_requires_a_named_channel(self):
        with self.assertRaises(InvalidRetargetingError):
            retargeting_campaign(channel="facebook")

    def test_a_campaign_cannot_cross_a_tenant_boundary(self):
        with self.assertRaises(RetargetingTenantBoundaryError):
            retargeting_campaign(
                tenant_id="other-client",
                audience=retargeting_audience(
                    tenant_id="other-client",
                    tracking_code=tracking_code(tenant_id="other-client"),
                ),
            )

    def test_a_campaign_requires_its_identification_fields(self):
        for field in ("campaign_id", "tenant_id", "name", "from_step"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidRetargetingError):
                    retargeting_campaign(**{field: "  "})


class RetargetingPlanTests(unittest.TestCase):
    def test_a_plan_records_its_required_sections(self):
        plan = retargeting_plan()

        self.assertEqual(
            (
                RetargetingStep.TRACKING_CODE,
                RetargetingStep.CONVERSION_GOALS,
                RetargetingStep.RETARGETING_LISTS,
                RetargetingStep.FOCUSED_CAMPAIGNS,
            ),
            plan.sections,
        )
        self.assertEqual((), plan.missing_sections())
        self.assertTrue(plan.is_complete)

    def test_a_plan_reports_a_missing_campaign_section(self):
        plan = retargeting_plan(campaigns=())

        self.assertEqual(
            (RetargetingStep.FOCUSED_CAMPAIGNS,), plan.missing_sections()
        )
        self.assertFalse(plan.is_complete)

    def test_a_plan_requires_a_named_owner(self):
        with self.assertRaises(InvalidRetargetingError):
            retargeting_plan(owner="  ")

    def test_a_plan_requires_its_identification_fields(self):
        for field in ("plan_id", "tenant_id"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidRetargetingError):
                    retargeting_plan(**{field: "  "})

    def test_a_plan_list_must_be_grounded_in_a_declared_goal(self):
        with self.assertRaises(RetargetingDependencyError):
            retargeting_plan(
                audiences=(
                    retargeting_audience(
                        achieved_goal=conversion_goal(
                            goal_id="goal-undeclared", name="undeclared"
                        )
                    ),
                )
            )

    def test_a_plan_campaign_must_use_a_declared_list(self):
        with self.assertRaises(RetargetingDependencyError):
            retargeting_plan(
                campaigns=(
                    retargeting_campaign(
                        audience=retargeting_audience(
                            audience_id="list-other",
                            achieved_goal=conversion_goal(),
                        )
                    ),
                )
            )

    def test_a_plan_campaign_must_be_grounded_in_a_declared_goal(self):
        with self.assertRaises(RetargetingDependencyError):
            retargeting_plan(
                campaigns=(
                    retargeting_campaign(
                        target_goal=conversion_goal(
                            goal_id="goal-undeclared",
                            name="undeclared",
                            funnel_step="appointment",
                        )
                    ),
                )
            )

    def test_a_plan_goal_must_share_the_plan_tracking_code(self):
        with self.assertRaises(RetargetingDependencyError):
            retargeting_plan(
                goals=(
                    conversion_goal(),
                    conversion_goal(
                        goal_id="goal-book",
                        name="strategy session booked",
                        url="/booked",
                    ),
                    conversion_goal(
                        goal_id="goal-other-pixel",
                        tracking_code=tracking_code(code_id="pixel-other"),
                    ),
                )
            )

    def test_a_plan_cannot_cross_a_tenant_boundary(self):
        with self.assertRaises(RetargetingTenantBoundaryError):
            retargeting_plan(
                tracking_code=tracking_code(tenant_id="other-client")
            )

    def test_a_plan_is_never_an_observed_result(self):
        plan = retargeting_plan()

        self.assertTrue(plan.is_plan)
        with self.assertRaises(RetargetingObservationError):
            plan.as_observation(claim_id="claim-retargeting")

    def test_a_plan_is_immutable(self):
        plan = retargeting_plan()

        with self.assertRaises(FrozenInstanceError):
            plan.owner = "other"


if __name__ == "__main__":
    unittest.main()
