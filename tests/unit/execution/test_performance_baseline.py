"""Behavioral tests for the PerformanceBaseline aggregate (Execution domain).

Rules under test come from SPEC.md section 4, stage 10 "Launch":
- The required asset package is the live campaign, spend and lead records,
  conversion and engagement measures, application, booking, show, close,
  acquisition cost, attribution and issue log.
- The "Performance Baseline Established" checkpoint treats first qualified
  traffic and the subsequent lead, appointment and sale as distinct observed
  milestones, with missing observations shown as pending.
- Campaign activation alone does not complete the engagement (Phase 5 TDD
  example: "launch alone cannot complete the engagement").
- Traffic, lead, qualified appointment and sale are distinct observed
  milestones (Phase 5 TDD example).
- A missing baseline blocks a before-and-after claim and a low sample size keeps
  a causal claim as an interpretation (Phase 5 TDD examples; SPEC.md section 3
  Measurement invariant: "Observations are distinct from causal conclusions").
- The stage is grounded on the stage 9 LaunchQA that authorizes traffic
  (SPEC.md section 3: production requires approved dependencies).
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.execution.domain.errors import (
    InvalidPerformanceBaselineError,
    InvalidPerformanceClaimError,
    MilestoneObservationPrecedenceError,
    PerformanceBaselineDependencyError,
    PerformanceBaselineIncompleteError,
    PerformanceBaselinePrecedenceError,
    PerformanceClaimSupportError,
)
from redops.contexts.execution.domain.value_objects import (
    MILESTONE_ORDER,
    ClaimKind,
    MilestoneKind,
    MilestoneObservation,
    ObservationStatus,
    PerformanceBaselineState,
)

from .fixtures import (
    authorization,
    established_baseline,
    launch_assets,
    launch_qa,
    milestone,
    milestone_observations,
    performance_baseline,
    performance_claim,
)
from ..production.fixtures import TODAY


class BaselineEstablishmentTests(unittest.TestCase):
    def test_a_grounded_baseline_with_observed_traffic_is_established(self):
        baseline = performance_baseline()

        established = baseline.establish(on=TODAY)

        self.assertIs(PerformanceBaselineState.ESTABLISHED, established.state)
        self.assertTrue(established.is_established)
        self.assertEqual(TODAY, established.established_on)

    def test_launch_authorization_alone_does_not_establish_a_baseline(self):
        pending_traffic = milestone_observations(
            {MilestoneKind.FIRST_QUALIFIED_TRAFFIC: ObservationStatus.PENDING}
        )

        with self.assertRaises(PerformanceBaselineIncompleteError):
            performance_baseline(milestones=pending_traffic).establish(on=TODAY)

    def test_later_milestones_may_stay_pending_when_traffic_is_observed(self):
        baseline = established_baseline()

        self.assertIn(MilestoneKind.FIRST_QUALIFIED_TRAFFIC, baseline.observed_kinds)
        self.assertIn(MilestoneKind.SALE, baseline.pending_kinds)
        self.assertFalse(baseline.pending_kinds & baseline.observed_kinds)

    def test_a_missing_milestone_must_be_recorded_as_pending(self):
        partial = tuple(
            observation
            for observation in milestone_observations()
            if observation.kind is not MilestoneKind.SALE
        )

        with self.assertRaises(PerformanceBaselineIncompleteError):
            performance_baseline(milestones=partial).establish(on=TODAY)

    def test_a_baseline_requires_a_ready_for_traffic_stage_9_qa(self):
        from .fixtures import launch_qa

        with self.assertRaises(PerformanceBaselineDependencyError):
            performance_baseline(launch_qa=launch_qa()).establish(on=TODAY)

    def test_a_terminal_baseline_cannot_establish(self):
        with self.assertRaises(PerformanceBaselineDependencyError):
            performance_baseline(
                state=PerformanceBaselineState.ARCHIVED
            ).establish(on=TODAY)

    def test_the_four_milestones_are_distinct_and_ordered(self):
        kinds = [observation.kind for observation in milestone_observations()]

        self.assertEqual(list(MILESTONE_ORDER), kinds)
        self.assertEqual(len(set(kinds)), len(kinds))

    def test_duplicate_milestones_are_rejected(self):
        duplicate = milestone_observations() + (
            milestone(MilestoneKind.LEAD),
        )

        with self.assertRaises(InvalidPerformanceBaselineError):
            performance_baseline(milestones=duplicate)

    def test_a_baseline_cannot_record_another_tenants_milestone(self):
        foreign = milestone(MilestoneKind.SALE, tenant_id="client-other")

        with self.assertRaises(PerformanceBaselineDependencyError):
            performance_baseline(milestones=(foreign,))

    def test_a_baseline_cannot_be_grounded_on_another_tenants_qa(self):
        with self.assertRaises(PerformanceBaselineDependencyError):
            performance_baseline(tenant_id="client-other")

    def test_a_baseline_requires_identity_and_owner(self):
        for override in ({"baseline_id": "  "}, {"owner": ""}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidPerformanceBaselineError):
                    performance_baseline(**override)


class BaselinePrecedenceTests(unittest.TestCase):
    """A baseline cannot be established before its own evidence exists.

    SPEC.md section 4, stage 10: the "Performance Baseline Established"
    checkpoint reports a baseline of the campaign that the stage 9 authority
    authorized and that first qualified traffic reached. Canon files 23 and 24
    ("you need a baseline of metrics", "don't touch anything for 10 days") treat
    the baseline as accumulating only after the campaign has run, so the
    establishment date must not precede the traffic authorization date or the
    observed first-qualified-traffic date.
    """

    def _traffic_observed_on(self, day):
        return tuple(
            milestone(
                kind,
                status=(
                    ObservationStatus.OBSERVED
                    if kind is MilestoneKind.FIRST_QUALIFIED_TRAFFIC
                    else ObservationStatus.PENDING
                ),
                observed_on=day,
            )
            for kind in MILESTONE_ORDER
        )

    def test_a_baseline_cannot_establish_before_traffic_was_observed(self):
        observed_on = date(2026, 10, 5)

        with self.assertRaises(PerformanceBaselinePrecedenceError):
            performance_baseline(
                milestones=self._traffic_observed_on(observed_on)
            ).establish(on=TODAY)

    def test_a_baseline_cannot_establish_before_the_stage_9_authorization(self):
        authorized_on = date(2026, 10, 5)
        qa = launch_qa().authorize_traffic(
            authorization=authorization(authorized_on=authorized_on)
        )

        with self.assertRaises(PerformanceBaselinePrecedenceError):
            performance_baseline(
                launch_qa=qa,
                milestones=self._traffic_observed_on(authorized_on),
            ).establish(on=TODAY)

    def test_a_baseline_can_establish_on_or_after_its_evidence_date(self):
        established = established_baseline()

        self.assertEqual(TODAY, established.established_on)


class MilestoneAuthorizationPrecedenceTests(unittest.TestCase):
    """No observed milestone may predate the authority that permitted traffic.

    SPEC.md section 4, stage 10: "Performance Baseline Established" reports first
    qualified traffic and the later lead, appointment and sale milestones, all of
    which are the traffic the stage 9 authority authorized. Canon files 23 and 24
    ("you need a baseline of metrics", "don't touch anything for 10 days") treat
    the baseline as accumulating only after the campaign has run, so an observed
    ``MilestoneObservation.observed_on`` must not precede
    ``qa.authorization.authorized_on``.
    """

    def _observations(self, *, lead_on, traffic_on):
        return tuple(
            milestone(
                kind,
                status=(
                    ObservationStatus.OBSERVED
                    if kind
                    in (
                        MilestoneKind.FIRST_QUALIFIED_TRAFFIC,
                        MilestoneKind.LEAD,
                    )
                    else ObservationStatus.PENDING
                ),
                observed_on=(
                    traffic_on
                    if kind is MilestoneKind.FIRST_QUALIFIED_TRAFFIC
                    else lead_on
                ),
            )
            for kind in MILESTONE_ORDER
        )

    def _qa_authorized_on(self, day):
        return launch_qa().authorize_traffic(
            authorization=authorization(authorized_on=day)
        )

    def test_a_later_observed_milestone_before_authorization_is_refused(self):
        authorized_on = date(2026, 10, 5)

        with self.assertRaises(MilestoneObservationPrecedenceError):
            performance_baseline(
                launch_qa=self._qa_authorized_on(authorized_on),
                milestones=self._observations(
                    traffic_on=authorized_on, lead_on=date(2026, 10, 1)
                ),
            ).establish(on=date(2026, 10, 6))

    def test_first_qualified_traffic_before_authorization_is_refused(self):
        authorized_on = date(2026, 10, 5)

        with self.assertRaises(MilestoneObservationPrecedenceError):
            performance_baseline(
                launch_qa=self._qa_authorized_on(authorized_on),
                milestones=self._observations(
                    traffic_on=date(2026, 10, 1),
                    lead_on=date(2026, 10, 5),
                ),
            ).establish(on=date(2026, 10, 6))

    def test_an_observed_milestone_on_the_authorization_date_is_allowed(self):
        authorized_on = date(2026, 10, 5)

        established = performance_baseline(
            launch_qa=self._qa_authorized_on(authorized_on),
            milestones=self._observations(
                traffic_on=authorized_on, lead_on=authorized_on
            ),
        ).establish(on=authorized_on)

        self.assertTrue(established.is_established)


class MilestoneObservationTests(unittest.TestCase):
    def test_an_observed_milestone_requires_a_date_and_source(self):
        with self.assertRaises(InvalidPerformanceBaselineError):
            milestone(
                MilestoneKind.SALE,
                status=ObservationStatus.OBSERVED,
                observed_on=None,
                source="",
            )

    def test_a_pending_milestone_cannot_carry_a_fabricated_observation(self):
        with self.assertRaises(InvalidPerformanceBaselineError):
            MilestoneObservation(
                kind=MilestoneKind.SALE,
                status=ObservationStatus.PENDING,
                tenant_id="client-3f",
                observed_on=TODAY,
                source="analytics://fabricated",
            )

    def test_an_established_baseline_is_immutable(self):
        established = established_baseline()

        with self.assertRaises(FrozenInstanceError):
            established.owner = "tampered"

    def test_an_established_baseline_can_be_marked_review_required(self):
        marked = established_baseline().mark_review_required(
            reason="launch QA changed"
        )

        self.assertIs(
            PerformanceBaselineState.REVIEW_REQUIRED, marked.state
        )
        self.assertFalse(marked.is_established)
        self.assertTrue(marked.review_reason)

    def test_marking_review_required_needs_a_reason(self):
        with self.assertRaises(InvalidPerformanceBaselineError):
            established_baseline().mark_review_required(reason="  ")


class StageTenAssetPackageTests(unittest.TestCase):
    def test_the_stage_10_asset_package_requires_every_artifact(self):
        for field in (
            "live_campaign",
            "spend_records",
            "lead_records",
            "conversion_measures",
            "engagement_measures",
            "applications",
            "bookings",
            "shows",
            "closes",
            "acquisition_cost",
            "attribution",
            "issue_log",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidPerformanceBaselineError):
                    launch_assets(**{field: "  "})


class PerformanceClaimTests(unittest.TestCase):
    def test_a_causal_claim_requires_an_established_baseline(self):
        from redops.contexts.execution.domain.policies import (
            PerformanceClaimPolicy,
        )

        with self.assertRaises(PerformanceClaimSupportError):
            PerformanceClaimPolicy().require(
                performance_claim(kind=ClaimKind.CAUSAL_CONCLUSION),
                None,
                minimum_sample=30,
            )

    def test_a_causal_claim_on_a_draft_baseline_is_refused(self):
        from redops.contexts.execution.domain.policies import (
            PerformanceClaimPolicy,
        )

        with self.assertRaises(PerformanceClaimSupportError):
            PerformanceClaimPolicy().require(
                performance_claim(kind=ClaimKind.CAUSAL_CONCLUSION),
                performance_baseline(),
                minimum_sample=30,
            )

    def test_a_low_sample_causal_claim_is_refused(self):
        from redops.contexts.execution.domain.policies import (
            PerformanceClaimPolicy,
        )

        with self.assertRaises(PerformanceClaimSupportError):
            PerformanceClaimPolicy().require(
                performance_claim(
                    kind=ClaimKind.CAUSAL_CONCLUSION, sample_size=5
                ),
                established_baseline(),
                minimum_sample=30,
            )

    def test_a_low_sample_claim_can_be_recorded_as_an_interpretation(self):
        from redops.contexts.execution.domain.policies import (
            PerformanceClaimPolicy,
        )

        interpretation = performance_claim(
            kind=ClaimKind.CAUSAL_CONCLUSION, sample_size=5
        ).as_interpretation()

        PerformanceClaimPolicy().require(
            interpretation, established_baseline(), minimum_sample=30
        )
        self.assertIs(ClaimKind.INTERPRETATION, interpretation.kind)

    def test_a_supported_causal_claim_passes_with_an_established_baseline(self):
        from redops.contexts.execution.domain.policies import (
            PerformanceClaimPolicy,
        )

        PerformanceClaimPolicy().require(
            performance_claim(kind=ClaimKind.CAUSAL_CONCLUSION, sample_size=40),
            established_baseline(),
            minimum_sample=30,
        )

    def test_an_observation_needs_no_baseline_and_is_not_causal(self):
        from redops.contexts.execution.domain.policies import (
            PerformanceClaimPolicy,
        )

        PerformanceClaimPolicy().require(
            performance_claim(kind=ClaimKind.OBSERVATION),
            None,
            minimum_sample=30,
        )

    def test_a_claim_cannot_cite_another_tenants_baseline(self):
        from redops.contexts.execution.domain.policies import (
            PerformanceClaimPolicy,
        )

        with self.assertRaises(PerformanceClaimSupportError):
            PerformanceClaimPolicy().require(
                performance_claim(
                    kind=ClaimKind.CAUSAL_CONCLUSION,
                    tenant_id="client-other",
                    baseline_id="baseline-3f",
                ),
                established_baseline(),
                minimum_sample=30,
            )

    def test_only_a_causal_claim_can_be_downgraded(self):
        with self.assertRaises(InvalidPerformanceClaimError):
            performance_claim(kind=ClaimKind.OBSERVATION).as_interpretation()


if __name__ == "__main__":
    unittest.main()
