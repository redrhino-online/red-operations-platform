"""Behavioral tests for the ten-second-view audience building campaign.

Rules under test come from SPEC.md section 4, stage 10 ("Performance Baseline
Established") and section 12.5 (the audience-building and content flywheel canon
gap), shaped by the canon's top-of-funnel audience campaign (canon file 30):

- The campaign objective is video views, not leads, appointments or page post
  engagement (canon file 30: "the goal of the campaign is not to generate leads,
  not to get customers, not to get appointments... I'm gonna bid on video views";
  page post engagement "was too weak of engagement").
- It optimizes for a ten-second view: "I'm trying to pay 5 to 20 cents for people
  to watch 10 seconds of the video" and "10 seconds to start with" (canon file 30).
- It retargets people who watched in "the last 30 days" and "10 second video
  views, 30 days is a good catch all" (canon file 30).
- The targeting comes from the avatar and is "interest stacking" over the
  avatar's "interests, likes, affinities, associations, publications" (canon file
  30).
- It spends a low starting daily budget: "$5 a day... I'll spend ten. Ten bucks a
  day" (canon file 30; the same dollar-a-day strategy as canon file 31).
- The target is "under 20 cents" per ten-second view, caller-supplied because the
  canon calls it a "rough metric" (canon file 30).
- It builds the warm audience the existing retargeting lists later segment, and
  it is a plan, not an observed result (SPEC.md section 3 keeps observations
  distinct from conclusions).
"""

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from redops.contexts.commercial.domain.value_objects import (
    AvatarProfile,
    DailyPromotionBudget,
)
from redops.contexts.measurement.domain.errors import (
    InvalidVideoViewAudienceError,
    VideoViewAudienceBudgetError,
    VideoViewAudienceDependencyError,
    VideoViewAudienceObjectiveError,
    VideoViewAudienceObservationError,
    VideoViewAudienceTargetCostError,
    VideoViewAudienceTenantBoundaryError,
    VideoViewAudienceWindowError,
)
from redops.contexts.measurement.domain.value_objects import (
    AudienceBuildingObjective,
    ConversionGoal,
    InterestTargeting,
    MeasurementBasis,
    RetargetingAudience,
    TrackingCode,
    VideoViewAudienceCampaign,
    VideoViewAudiencePolicy,
    VideoViewWindow,
)

TENANT = "client-3f"


def avatar(**overrides) -> AvatarProfile:
    values = {
        "avatar_id": "avatar-3f",
        "tenant_id": TENANT,
        "name": "the founder",
        "demographics": "coaches aged 35 to 55",
        "psychographics": "wants authority without a big brand",
        "pains": ("lead flow is unpredictable",),
        "goals": ("a predictable high-ticket offer",),
        "consequences_of_inaction": ("the offer never launches",),
        "awareness": "problem aware",
        "customer_evidence_claim_ids": ("claim-voice-1",),
        "voice_notes": ("wants proof before spending",),
    }
    values.update(overrides)
    return AvatarProfile(**values)


def interest_targeting(**overrides) -> InterestTargeting:
    values = {
        "targeting_id": "target-funnel-experts",
        "tenant_id": TENANT,
        "avatar": avatar(),
        "interests": ("frank-kern", "hubspot"),
    }
    values.update(overrides)
    return InterestTargeting(**values)


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
    }
    values.update(overrides)
    return ConversionGoal(**values)


def retargeting_audience(**overrides) -> RetargetingAudience:
    values = {
        "audience_id": "list-video-warm",
        "tenant_id": TENANT,
        "name": "watched 10 seconds in the last 30 days",
        "funnel_step": "top-of-funnel",
        "achieved_goal": conversion_goal(),
        "lookback_days": 30,
        "tracking_code": tracking_code(),
    }
    values.update(overrides)
    return RetargetingAudience(**values)


def video_view_campaign(**overrides) -> VideoViewAudienceCampaign:
    values = {
        "campaign_id": "campaign-audience-video-views",
        "tenant_id": TENANT,
        "owner": "campaign-operator",
        "name": "top of funnel audience building",
        "objective": AudienceBuildingObjective.VIDEO_VIEWS,
        "targeting": interest_targeting(),
        "view_window": VideoViewWindow(view_seconds=10, retention_days=30),
        "daily_budget": DailyPromotionBudget(
            amount=Decimal("10"), currency="USD"
        ),
        "target_cost_per_view": Decimal("0.20"),
        "tracking_code": tracking_code(),
        "retargeting_lists": (retargeting_audience(),),
    }
    values.update(overrides)
    return VideoViewAudienceCampaign(**values)


class VideoViewWindowTests(unittest.TestCase):
    def test_the_canon_catch_all_is_a_ten_second_view_over_thirty_days(self):
        window = VideoViewWindow.canon()

        self.assertEqual(10, window.view_seconds)
        self.assertEqual(30, window.retention_days)
        self.assertTrue(window.uses_canon_catch_all)

    def test_a_window_requires_at_least_a_ten_second_view(self):
        with self.assertRaises(VideoViewAudienceWindowError):
            VideoViewWindow(view_seconds=3, retention_days=30)

    def test_a_window_may_be_stricter_than_the_catch_all(self):
        window = VideoViewWindow(view_seconds=15, retention_days=7)

        self.assertFalse(window.uses_canon_catch_all)
        self.assertEqual(15, window.view_seconds)

    def test_a_window_retention_is_bounded_to_thirty_days(self):
        for days in (0, 31, -1):
            with self.subTest(days=days):
                with self.assertRaises(VideoViewAudienceWindowError):
                    VideoViewWindow(view_seconds=10, retention_days=days)

    def test_a_window_rejects_a_non_integer_value(self):
        for field in ("view_seconds", "retention_days"):
            with self.subTest(field=field):
                values = {"view_seconds": 10, "retention_days": 30}
                values[field] = "10"
                with self.assertRaises(VideoViewAudienceWindowError):
                    VideoViewWindow(**values)

    def test_a_window_is_immutable(self):
        window = VideoViewWindow.canon()

        with self.assertRaises(FrozenInstanceError):
            window.view_seconds = 5


class InterestTargetingTests(unittest.TestCase):
    def test_targeting_stacks_the_avatar_interests(self):
        targeting = interest_targeting()

        self.assertEqual(("frank-kern", "hubspot"), targeting.interests)
        self.assertEqual(TENANT, targeting.avatar.tenant_id)

    def test_targeting_requires_a_typed_avatar(self):
        with self.assertRaises(VideoViewAudienceDependencyError):
            interest_targeting(avatar="avatar-3f")

    def test_targeting_refuses_an_avatar_from_another_tenant(self):
        with self.assertRaises(VideoViewAudienceTenantBoundaryError):
            interest_targeting(avatar=avatar(tenant_id="other-client"))

    def test_targeting_requires_at_least_two_stacked_interests(self):
        with self.assertRaises(InvalidVideoViewAudienceError):
            interest_targeting(interests=("frank-kern",))

    def test_targeting_refuses_a_duplicate_interest(self):
        with self.assertRaises(InvalidVideoViewAudienceError):
            interest_targeting(interests=("frank-kern", "frank-kern"))

    def test_targeting_refuses_a_blank_interest(self):
        with self.assertRaises(InvalidVideoViewAudienceError):
            interest_targeting(interests=("frank-kern", " "))

    def test_targeting_requires_its_identification_fields(self):
        for field in ("targeting_id", "tenant_id"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidVideoViewAudienceError):
                    interest_targeting(**{field: "  "})

    def test_targeting_is_immutable(self):
        targeting = interest_targeting()

        with self.assertRaises(FrozenInstanceError):
            targeting.interests = ("other", "more")


class VideoViewAudienceCampaignTests(unittest.TestCase):
    def test_a_campaign_records_its_objective_window_budget_and_target(self):
        campaign = video_view_campaign()

        self.assertIs(AudienceBuildingObjective.VIDEO_VIEWS, campaign.objective)
        self.assertEqual(10, campaign.view_window.view_seconds)
        self.assertEqual(Decimal("10"), campaign.daily_budget.amount)
        self.assertEqual(Decimal("0.20"), campaign.target_cost_per_view)

    def test_a_campaign_requires_the_video_views_objective(self):
        for objective in (
            AudienceBuildingObjective.PAGE_POST_ENGAGEMENT,
            AudienceBuildingObjective.LEAD_GENERATION,
            AudienceBuildingObjective.CONVERSIONS,
        ):
            with self.subTest(objective=objective):
                with self.assertRaises(VideoViewAudienceObjectiveError):
                    video_view_campaign(objective=objective)

    def test_a_campaign_requires_a_typed_objective(self):
        with self.assertRaises(VideoViewAudienceObjectiveError):
            video_view_campaign(objective="video_views")

    def test_a_campaign_requires_its_identification_fields(self):
        for field in ("campaign_id", "tenant_id", "owner", "name"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidVideoViewAudienceError):
                    video_view_campaign(**{field: "  "})

    def test_a_campaign_requires_typed_targeting(self):
        with self.assertRaises(VideoViewAudienceDependencyError):
            video_view_campaign(targeting="frank-kern")

    def test_a_campaign_refuses_targeting_from_another_tenant(self):
        with self.assertRaises(VideoViewAudienceTenantBoundaryError):
            video_view_campaign(
                targeting=interest_targeting(
                    tenant_id="other-client",
                    avatar=avatar(tenant_id="other-client"),
                )
            )

    def test_a_campaign_requires_a_typed_view_window(self):
        with self.assertRaises(VideoViewAudienceDependencyError):
            video_view_campaign(view_window=(10, 30))

    def test_a_campaign_requires_a_typed_daily_budget(self):
        with self.assertRaises(VideoViewAudienceDependencyError):
            video_view_campaign(daily_budget=Decimal("10"))

    def test_a_campaign_target_cost_is_positive(self):
        for cost in (Decimal("0"), Decimal("-0.01")):
            with self.subTest(cost=cost):
                with self.assertRaises(InvalidVideoViewAudienceError):
                    video_view_campaign(target_cost_per_view=cost)

    def test_a_campaign_target_cost_must_be_a_decimal(self):
        with self.assertRaises(InvalidVideoViewAudienceError):
            video_view_campaign(target_cost_per_view=0.2)

    def test_a_campaign_requires_a_typed_tracking_code(self):
        with self.assertRaises(VideoViewAudienceDependencyError):
            video_view_campaign(tracking_code="pixel-3f")

    def test_a_campaign_refuses_a_tracking_code_from_another_tenant(self):
        with self.assertRaises(VideoViewAudienceTenantBoundaryError):
            video_view_campaign(
                tracking_code=tracking_code(tenant_id="other-client")
            )

    def test_a_campaign_requires_at_least_one_retargeting_list(self):
        with self.assertRaises(VideoViewAudienceDependencyError):
            video_view_campaign(retargeting_lists=())

    def test_a_campaign_requires_typed_retargeting_lists(self):
        with self.assertRaises(VideoViewAudienceDependencyError):
            video_view_campaign(retargeting_lists=("list-video-warm",))

    def test_a_campaign_refuses_a_retargeting_list_from_another_tenant(self):
        with self.assertRaises(VideoViewAudienceTenantBoundaryError):
            video_view_campaign(
                retargeting_lists=(
                    retargeting_audience(
                        tenant_id="other-client",
                        achieved_goal=conversion_goal(
                            tenant_id="other-client",
                            tracking_code=tracking_code(
                                tenant_id="other-client"
                            ),
                        ),
                        tracking_code=tracking_code(tenant_id="other-client"),
                    ),
                )
            )

    def test_a_campaign_refuses_a_retargeting_list_on_another_tracking_code(self):
        with self.assertRaises(VideoViewAudienceDependencyError):
            video_view_campaign(
                retargeting_lists=(
                    retargeting_audience(
                        achieved_goal=conversion_goal(
                            tracking_code=tracking_code(code_id="pixel-other")
                        ),
                        tracking_code=tracking_code(code_id="pixel-other"),
                    ),
                )
            )

    def test_a_campaign_reports_the_audience_it_builds_for(self):
        campaign = video_view_campaign()

        self.assertEqual(("top-of-funnel",), campaign.retargeting_steps)
        self.assertTrue(campaign.builds_for(retargeting_audience()))
        self.assertFalse(campaign.builds_for(retargeting_audience(audience_id="x")))

    def test_a_campaign_is_never_an_observed_result(self):
        campaign = video_view_campaign()

        self.assertTrue(campaign.is_campaign)
        with self.assertRaises(VideoViewAudienceObservationError):
            campaign.as_observation(claim_id="claim-audience")

    def test_a_campaign_is_immutable(self):
        campaign = video_view_campaign()

        with self.assertRaises(FrozenInstanceError):
            campaign.owner = "other"


class VideoViewAudiencePolicyTests(unittest.TestCase):
    def test_a_low_starting_budget_is_required(self):
        campaign = video_view_campaign(
            daily_budget=DailyPromotionBudget(amount=Decimal("10"), currency="USD")
        )

        VideoViewAudiencePolicy.require_low_daily_budget(
            campaign, ceiling=Decimal("10")
        )
        with self.assertRaises(VideoViewAudienceBudgetError):
            VideoViewAudiencePolicy.require_low_daily_budget(
                campaign, ceiling=Decimal("5")
            )

    def test_the_canon_target_cost_ceiling_is_enforced(self):
        campaign = video_view_campaign(
            target_cost_per_view=Decimal("0.20")
        )

        VideoViewAudiencePolicy.require_target_cost_below(
            campaign, ceiling=Decimal("0.20")
        )
        with self.assertRaises(VideoViewAudienceTargetCostError):
            VideoViewAudiencePolicy.require_target_cost_below(
                campaign, ceiling=Decimal("0.10")
            )


if __name__ == "__main__":
    unittest.main()
