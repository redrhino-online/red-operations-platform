"""Behavioral tests for the stage 10 advertising scaling rule (Measurement domain).

Rules under test come from SPEC.md section 4, stage 10 ("performance
recommendations require evidence and owner approval before material changes")
shaped by the canon's scaling discipline (canon files 22, 23 and 24):

- Do nothing while Facebook is still in its learning phase: the canon waits for
  the first seven to ten days or 100 plus conversions before touching a campaign
  (canon file 22 and 24).
- Once past learning, the only question that matters is the return on ad spend,
  never a vanity cost per lead: a cost per lead at or below the target derived
  from the desired return is a reason to scale up, and a cost per lead above the
  target is a reason to pause and revisit (canon files 22 and 24: "it's all about
  the roi... not some vanity metric, cost per lead").
- If the campaign cannot feed the algorithm at least ten leads a day, bid on
  clicks at an earlier funnel objective instead of starving learning (canon file
  24: "if you can't afford to get 10 leads a day... bid on clicks").
- A placeholder figure or a metric of the wrong funnel step never drives a
  spending recommendation, and every recommendation stays a recommendation that a
  named owner approves before spend changes.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.measurement.domain.errors import (
    InvalidScalingRecommendationError,
    ScalingLearningPhaseError,
    ScalingMetricError,
    ScalingObservationError,
    ScalingRecommendationObservationError,
    ScalingTenantBoundaryError,
)
from redops.contexts.measurement.domain.policies import AdScalingPolicy
from redops.contexts.measurement.domain.value_objects import (
    LearningPhase,
    MeasurementBasis,
    MeasurementWindow,
    MetricUnit,
    ScalingAction,
)

from .fixtures import (
    funnel_economics,
    measurement_record,
    metric_definition,
    placeholder_record,
)

TENANT = "client-3f"
WINDOW = MeasurementWindow(start=date(2026, 9, 23), end=date(2026, 10, 2))


def learning_phase(**overrides) -> LearningPhase:
    values = {
        "started_on": date(2026, 9, 23),
        "minimum_days": 7,
        "minimum_events": 100,
    }
    values.update(overrides)
    return LearningPhase(**values)


def cost_per_lead_record(**overrides) -> object:
    values = {
        "metric": metric_definition(),
        "tenant_id": TENANT,
        "value": 8.0,
        "window": WINDOW,
        "basis": MeasurementBasis.OBSERVED,
        "sample_size": 150,
        "recorded_on": date(2026, 10, 2),
    }
    values.update(overrides)
    return measurement_record(**values)


class LearningPhaseTests(unittest.TestCase):
    def test_learning_completes_once_the_minimum_days_elapse(self):
        phase = learning_phase()

        self.assertTrue(
            phase.is_complete(observed_on=date(2026, 10, 2), event_count=5)
        )

    def test_learning_completes_once_the_minimum_events_accumulate(self):
        phase = learning_phase()

        self.assertTrue(
            phase.is_complete(observed_on=date(2026, 9, 25), event_count=100)
        )

    def test_learning_is_incomplete_before_either_threshold(self):
        phase = learning_phase()

        self.assertFalse(
            phase.is_complete(observed_on=date(2026, 9, 25), event_count=5)
        )

    def test_a_learning_phase_requires_a_start_and_positive_minimum_days(self):
        for started_on in (None, "yesterday"):
            with self.subTest(started_on=started_on):
                with self.assertRaises(ScalingLearningPhaseError):
                    LearningPhase(started_on=started_on)
        for minimum_days in (0, -1):
            with self.subTest(minimum_days=minimum_days):
                with self.assertRaises(ScalingLearningPhaseError):
                    learning_phase(minimum_days=minimum_days)

    def test_a_learning_phase_is_immutable(self):
        phase = learning_phase()

        with self.assertRaises(FrozenInstanceError):
            phase.minimum_days = 30


class AdScalingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = AdScalingPolicy()

    def recommend(self, **overrides):
        values = {
            "observed": cost_per_lead_record(),
            "economics": funnel_economics(),
            "target_return_on_ad_spend": 10.0,
            "learning_phase": learning_phase(),
        }
        values.update(overrides)
        return self.policy.recommend(**values)

    def test_a_cost_per_lead_below_target_scales_up(self):
        recommendation = self.recommend(
            observed=cost_per_lead_record(value=8.0)
        )

        self.assertIs(ScalingAction.SCALE_UP, recommendation.action)
        self.assertEqual(12.5, recommendation.target_cost_per_lead)

    def test_a_cost_per_lead_at_target_scales_up(self):
        recommendation = self.recommend(
            observed=cost_per_lead_record(value=12.5)
        )

        self.assertIs(ScalingAction.SCALE_UP, recommendation.action)

    def test_a_cost_per_lead_above_target_pauses_and_revisits(self):
        recommendation = self.recommend(
            observed=cost_per_lead_record(value=20.0)
        )

        self.assertIs(ScalingAction.PAUSE_AND_REVIEW, recommendation.action)

    def test_a_good_roi_is_not_stopped_by_a_high_vanity_cost_per_lead(self):
        recommendation = self.recommend(
            observed=cost_per_lead_record(value=11.0)
        )

        self.assertIs(ScalingAction.SCALE_UP, recommendation.action)

    def test_the_campaign_holds_while_still_in_the_learning_phase(self):
        recommendation = self.recommend(
            observed=cost_per_lead_record(
                value=20.0,
                window=MeasurementWindow(
                    start=date(2026, 9, 23), end=date(2026, 9, 25)
                ),
                sample_size=30,
                recorded_on=date(2026, 9, 25),
            )
        )

        self.assertIs(ScalingAction.HOLD, recommendation.action)

    def test_too_little_volume_past_learning_bids_up_the_funnel(self):
        recommendation = self.recommend(
            observed=cost_per_lead_record(
                value=8.0, sample_size=30, window=WINDOW
            )
        )

        self.assertIs(ScalingAction.BID_UP_FUNNEL, recommendation.action)
        self.assertEqual(3.0, recommendation.leads_per_day)

    def test_the_volume_floor_is_caller_supplied(self):
        recommendation = self.recommend(
            observed=cost_per_lead_record(value=8.0, sample_size=30),
            minimum_leads_per_day=2.0,
        )

        self.assertIs(ScalingAction.SCALE_UP, recommendation.action)

    def test_a_placeholder_figure_cannot_drive_a_recommendation(self):
        with self.assertRaises(ScalingObservationError):
            self.recommend(
                observed=placeholder_record(metric=metric_definition())
            )

    def test_a_metric_of_the_wrong_funnel_role_is_refused(self):
        booking = metric_definition(unit=MetricUnit.PERCENT)

        with self.assertRaises(ScalingMetricError):
            self.recommend(
                observed=cost_per_lead_record(metric=booking)
            )

    def test_another_tenants_observation_cannot_be_scaled(self):
        with self.assertRaises(ScalingTenantBoundaryError):
            self.recommend(
                observed=cost_per_lead_record(
                    tenant_id="other-client",
                    metric=metric_definition(tenant_id="other-client"),
                )
            )

    def test_a_target_return_on_ad_spend_must_be_positive(self):
        for target in (0.0, -1.0):
            with self.subTest(target=target):
                with self.assertRaises(InvalidScalingRecommendationError):
                    self.recommend(target_return_on_ad_spend=target)

    def test_a_recommendation_is_immutable(self):
        recommendation = self.recommend()

        with self.assertRaises(FrozenInstanceError):
            recommendation.action = ScalingAction.HOLD


class ScalingRecommendationTests(unittest.TestCase):
    def setUp(self):
        self.policy = AdScalingPolicy()

    def recommendation(self, **overrides):
        values = {
            "observed": cost_per_lead_record(),
            "economics": funnel_economics(),
            "target_return_on_ad_spend": 10.0,
            "learning_phase": learning_phase(),
        }
        values.update(overrides)
        return self.policy.recommend(**values)

    def test_a_recommendation_requires_owner_approval_before_spend(self):
        recommendation = self.recommendation()

        self.assertTrue(recommendation.is_recommendation)
        self.assertTrue(recommendation.requires_owner_approval)

    def test_a_recommendation_carries_its_evidence_and_rationale(self):
        recommendation = self.recommendation()

        self.assertEqual(recommendation.observed.value, 8.0)
        self.assertTrue(recommendation.rationale.strip())

    def test_a_recommendation_is_never_an_observed_result(self):
        recommendation = self.recommendation()

        with self.assertRaises(ScalingRecommendationObservationError):
            recommendation.as_observation(claim_id="claim-scaling")


if __name__ == "__main__":
    unittest.main()
