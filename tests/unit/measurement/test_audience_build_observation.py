"""Behavioral tests for the canon's content measurement loop.

Rules under test come from SPEC.md section 12.5 (the audience-building and
content flywheel canon gap: the top-of-funnel audience campaign and its
measurement) and SPEC.md section 3, whose Measurement invariant keeps
observations distinct from causal conclusions. The shape is grounded in the
canon's promotion and dashboard training:

- The audience campaign's success is measured in the audience it builds: "So now
  I have is 22,000 people to advertise to" (canon file 30) and the dashboard's
  "top of funnel audience" of "25,000 people" at "20 cents each" (canon file 23).
- The cost per ten-second view is the diagnostic number: "under 20 cents is a
  really rough metric" and "$0.03 for a 10 second video view"; "if you see that
  [cost] is super high. Then you have a problem with the topic. So you can stop
  it" (canon file 30).
- A result is read only after the period it covers has elapsed, and a placeholder
  figure is not a real metric (canon files 23 and 24), so the loop records an
  observed audience over a closed window, never a planned figure.
- The observation is an observation, not a causal conclusion (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

from redops.contexts.commercial.domain.value_objects import (
    AvatarProfile,
    DailyPromotionBudget,
)
from redops.contexts.execution.domain.value_objects import ClaimKind
from redops.contexts.measurement.domain.errors import (
    AudienceBuildObservationBasisError,
    AudienceBuildObservationDependencyError,
    AudienceBuildObservationTenantBoundaryError,
    AudienceBuildObservationWindowOpenError,
    InvalidAudienceBuildObservationError,
)
from redops.contexts.measurement.domain.value_objects import (
    AudienceBuildObservation,
    AudienceBuildingObjective,
    ConversionGoal,
    InterestTargeting,
    MeasurementBasis,
    MeasurementWindow,
    RetargetingAudience,
    TrackingCode,
    VideoViewAudienceCampaign,
    VideoViewWindow,
)

TENANT = "client-3f"
WINDOW = MeasurementWindow(start=date(2026, 9, 1), end=date(2026, 9, 30))
RECORDED_ON = date(2026, 10, 1)


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
        "targeting": InterestTargeting(
            targeting_id="target-funnel-experts",
            tenant_id=TENANT,
            avatar=avatar(),
            interests=("frank-kern", "hubspot"),
        ),
        "view_window": VideoViewWindow(view_seconds=10, retention_days=30),
        "daily_budget": DailyPromotionBudget(amount=Decimal("10"), currency="USD"),
        "target_cost_per_view": Decimal("0.20"),
        "tracking_code": tracking_code(),
        "retargeting_lists": (retargeting_audience(),),
    }
    values.update(overrides)
    return VideoViewAudienceCampaign(**values)


def on_tenant(tenant_id: str) -> VideoViewAudienceCampaign:
    """A complete audience campaign wholly owned by another tenant."""
    code = tracking_code(tenant_id=tenant_id)
    return video_view_campaign(
        tenant_id=tenant_id,
        targeting=InterestTargeting(
            targeting_id="target-other",
            tenant_id=tenant_id,
            avatar=avatar(tenant_id=tenant_id, avatar_id="avatar-other"),
            interests=("frank-kern", "hubspot"),
        ),
        tracking_code=code,
        retargeting_lists=(
            retargeting_audience(
                tenant_id=tenant_id,
                audience_id="list-other",
                achieved_goal=conversion_goal(
                    tenant_id=tenant_id,
                    goal_id="goal-other",
                    tracking_code=code,
                ),
                tracking_code=code,
            ),
        ),
    )



def observation(**overrides) -> AudienceBuildObservation:
    values = {
        "observation_id": "observe-audience-3f",
        "tenant_id": TENANT,
        "owner": "campaign-operator",
        "campaign": video_view_campaign(),
        "window": WINDOW,
        "basis": MeasurementBasis.OBSERVED,
        "audience_size": 25000,
        "cost_per_view": Decimal("0.03"),
        "source": "analytics://facebook-video-views",
        "recorded_on": RECORDED_ON,
    }
    values.update(overrides)
    return AudienceBuildObservation(**values)


class AudienceBuildObservationTests(unittest.TestCase):
    def test_an_observation_records_the_built_audience_and_cost_per_view(self):
        observed = observation()

        self.assertEqual(25000, observed.audience_size)
        self.assertEqual(Decimal("0.03"), observed.cost_per_view)
        self.assertEqual(WINDOW, observed.window)

    def test_an_observation_is_grounded_on_the_same_tenant_campaign(self):
        observed = observation()

        self.assertEqual(TENANT, observed.campaign.tenant_id)
        self.assertTrue(observed.meets_target_cost)

    def test_a_cost_at_or_below_the_target_meets_it(self):
        at_target = observation(cost_per_view=Decimal("0.20"))
        below_target = observation(cost_per_view=Decimal("0.01"))

        self.assertTrue(at_target.meets_target_cost)
        self.assertTrue(below_target.meets_target_cost)

    def test_a_cost_above_the_target_indicates_a_topic_problem(self):
        expensive = observation(cost_per_view=Decimal("0.73"))

        self.assertFalse(expensive.meets_target_cost)
        self.assertTrue(expensive.indicates_topic_problem)

    def test_an_observation_requires_a_typed_campaign(self):
        with self.assertRaises(AudienceBuildObservationDependencyError):
            observation(campaign="campaign-audience-video-views")

    def test_an_observation_refuses_a_campaign_from_another_tenant(self):
        with self.assertRaises(AudienceBuildObservationTenantBoundaryError):
            observation(campaign=on_tenant("other-client"))

    def test_an_observation_requires_a_typed_window_and_basis(self):
        with self.assertRaises(AudienceBuildObservationDependencyError):
            observation(window="september")
        with self.assertRaises(AudienceBuildObservationDependencyError):
            observation(basis="observed")

    def test_an_observation_refuses_a_placeholder_basis(self):
        with self.assertRaises(AudienceBuildObservationBasisError):
            observation(basis=MeasurementBasis.PLACEHOLDER)

    def test_an_observation_requires_its_identification_fields(self):
        for field in ("observation_id", "tenant_id", "owner", "source"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidAudienceBuildObservationError):
                    observation(**{field: "  "})

    def test_an_observation_requires_a_positive_audience_size(self):
        for size in (0, -1, 1.5, True, "25000"):
            with self.subTest(size=size):
                with self.assertRaises(InvalidAudienceBuildObservationError):
                    observation(audience_size=size)

    def test_an_observation_requires_a_positive_decimal_cost_per_view(self):
        for cost in (Decimal("0"), Decimal("-0.01"), 0.03, "0.03"):
            with self.subTest(cost=cost):
                with self.assertRaises(InvalidAudienceBuildObservationError):
                    observation(cost_per_view=cost)

    def test_an_observation_cannot_be_recorded_before_its_window_closes(self):
        with self.assertRaises(AudienceBuildObservationWindowOpenError):
            observation(recorded_on=date(2026, 9, 15))

    def test_an_observation_is_never_a_causal_conclusion(self):
        observed = observation()

        claim = observed.performance_claim(claim_id="claim-audience-3f")

        self.assertIs(ClaimKind.OBSERVATION, claim.kind)
        self.assertEqual(TENANT, claim.tenant_id)
        self.assertEqual(25000, claim.sample_size)
        self.assertIn("25000", claim.statement)
        self.assertIn("0.03", claim.statement)

    def test_an_observation_is_immutable(self):
        observed = observation()

        with self.assertRaises(FrozenInstanceError):
            observed.audience_size = 1


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
