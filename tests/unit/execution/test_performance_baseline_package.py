"""Behavioral tests for the stage 10 "Performance Baseline" asset package.

Rules under test come from SPEC.md sections 3, 4 and 12.3. Stage 10 "Launch"
requires the live campaign, spend and lead records, conversion and engagement
measures, applications, bookings, shows, closes, acquisition cost, attribution
and issue log, and its checkpoint is "Performance Baseline Established": the
first qualified traffic and the subsequent lead, appointment and sale are
distinct observed milestones, with missing observations shown as pending. The
reference model canon that informs this stage is files 22, 23, 29-31, 33 and 34
(SPEC.md section 12.3): the Facebook Ads quick start, the Metrics Matrix and the
Mastery Advertising Metrics Dashboard (annual customer value, cost per lead,
cost per strategy session, customer acquisition cost and return on ad spend),
the Content Blitz produce/publish/promote/syndicate sequence and the Retargeting
Roadmap.

Like the stage 1 through 9 reviewed-asset bridges, this package projects the
reviewed stage 10 ``PerformanceBaseline`` onto the twelve canonical stage 10
asset kinds as exact ``StageAssetVersion`` evidence so a canonical gate can be
assembled. The ``nurture-plan`` kind is projected from the reviewed Commercial
Design ``NurturePlan`` at its own identity and version, because the methodology
owner placed the canon follow-up and nurture lifecycle as a required stage 10 kind
(owner decision 2026-10-04, P2; SPEC.md sections 4 and 12.5). A
``PerformanceBaseline`` only reaches ``PerformanceBaselineState.ESTABLISHED``
after ``establish`` passes the checkpoint on the stage 9 traffic authorization and
an observed first qualified traffic milestone, so the package refuses a baseline
that has not passed "Performance Baseline Established" rather than pinning
thirteen kinds for an unestablished baseline (SPEC.md section 4: a missing asset
prevents gate completion and a waiver never makes an absent asset appear present).
It also refuses a blank identity, a versionless baseline, a foreign or versionless
nurture plan and a cross-tenant baseline.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.value_objects import NurtureModality
from redops.contexts.execution.domain.entities import PerformanceBaseline
from redops.contexts.execution.domain.errors import (
    InvalidPerformanceBaselinePackageError,
    PerformanceBaselinePackageTenantBoundaryError,
)
from redops.contexts.execution.domain.value_objects import (
    CANONICAL_BASELINE_KINDS,
    MILESTONE_ORDER,
    PerformanceBaselinePackage,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template

from .fixtures import (
    TENANT,
    established_baseline,
    milestone,
    performance_baseline,
)
from .test_launch_qa_package import other_tenant_ready_qa
from ..commercial.test_nurture_lifecycle import (
    nurture_message,
    nurture_plan,
    nurture_sequence,
)
from ..method.fixtures import signature_solution
from ..production.fixtures import TODAY

OTHER_TENANT = "client-other"


def other_tenant_established_baseline() -> PerformanceBaseline:
    return performance_baseline(
        tenant_id=OTHER_TENANT,
        launch_qa=other_tenant_ready_qa(),
        milestones=tuple(
            milestone(kind, tenant_id=OTHER_TENANT)
            for kind in MILESTONE_ORDER
        ),
    ).establish(on=TODAY)


def other_tenant_nurture_plan():
    return nurture_plan(
        tenant_id=OTHER_TENANT,
        method=signature_solution(tenant_id=OTHER_TENANT),
        sequences=(
            nurture_sequence(
                tenant_id=OTHER_TENANT,
                messages=(
                    nurture_message(tenant_id=OTHER_TENANT),
                    nurture_message(
                        message_id="nurture-2",
                        tenant_id=OTHER_TENANT,
                        name="book a referral diagnostic",
                        modality=NurtureModality.PROMOTION,
                        subject="your referral diagnostic is open",
                        purpose="promote the next step",
                    ),
                ),
            ),
        ),
    )


def package(**overrides) -> PerformanceBaselinePackage:
    values = {
        "package_id": "baseline-package-3f",
        "tenant_id": TENANT,
        "baseline": established_baseline(),
        "baseline_version": 1,
        "nurture": nurture_plan(),
        "nurture_version": 1,
    }
    values.update(overrides)
    return PerformanceBaselinePackage(**values)


class PerformanceBaselinePackageProjectionTests(unittest.TestCase):
    def test_the_package_projects_all_thirteen_canonical_stage_ten_kinds(self):
        assets = package().stage_asset_versions()

        kinds = {asset.kind for asset in assets}
        self.assertEqual(frozenset(CANONICAL_BASELINE_KINDS), kinds)
        self.assertEqual(13, len(assets))

    def test_the_canonical_kinds_match_the_template_stage_ten_package(self):
        template_kinds = stage_zero_to_ten_template().required_asset_kinds(10)

        self.assertEqual(template_kinds, frozenset(CANONICAL_BASELINE_KINDS))

    def test_every_baseline_kind_pins_the_reviewed_baseline_at_its_version(self):
        assets = package(baseline_version=4).stage_asset_versions()

        baseline_assets = [
            asset for asset in assets if asset.kind != "nurture-plan"
        ]
        self.assertEqual(12, len(baseline_assets))
        for asset in baseline_assets:
            self.assertEqual(4, asset.version)

    def test_the_nurture_kind_pins_the_reviewed_plan_at_its_own_version(self):
        assets = package(nurture_version=7).stage_asset_versions()

        nurture = next(asset for asset in assets if asset.kind == "nurture-plan")
        self.assertEqual("nurture-3f", nurture.asset_id)
        self.assertEqual(7, nurture.version)

    def test_each_baseline_kind_pins_the_reviewed_baseline_identity(self):
        assets = package().stage_asset_versions()

        for asset in assets:
            if asset.kind == "nurture-plan":
                continue
            self.assertEqual("baseline-3f", asset.asset_id)

    def test_the_projected_evidence_is_tenant_scoped(self):
        for asset in package().stage_asset_versions():
            self.assertEqual(TENANT, asset.tenant_id)

    def test_an_established_package_reports_no_missing_kinds(self):
        value = package()

        self.assertTrue(value.is_complete)
        self.assertEqual((), value.missing_kinds())

    def test_the_package_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            package().package_id = "tampered"


class PerformanceBaselinePackageBoundaryTests(unittest.TestCase):
    def test_a_cross_tenant_baseline_is_refused(self):
        with self.assertRaises(PerformanceBaselinePackageTenantBoundaryError):
            package(baseline=other_tenant_established_baseline())

    def test_a_cross_tenant_nurture_plan_is_refused(self):
        with self.assertRaises(PerformanceBaselinePackageTenantBoundaryError):
            package(nurture=other_tenant_nurture_plan())

    def test_a_blank_package_identity_is_refused(self):
        for override in ({"package_id": ""}, {"tenant_id": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidPerformanceBaselinePackageError):
                    package(**override)

    def test_a_versionless_reviewed_baseline_is_refused(self):
        for override in ({"baseline_version": 0}, {"baseline_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidPerformanceBaselinePackageError):
                    package(**override)

    def test_a_versionless_nurture_plan_is_refused(self):
        for override in ({"nurture_version": 0}, {"nurture_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidPerformanceBaselinePackageError):
                    package(**override)

    def test_a_draft_baseline_is_refused(self):
        with self.assertRaises(InvalidPerformanceBaselinePackageError):
            package(baseline=performance_baseline())

    def test_a_review_required_baseline_is_refused(self):
        baseline = established_baseline().mark_review_required(
            reason="launch QA changed"
        )

        with self.assertRaises(InvalidPerformanceBaselinePackageError):
            package(baseline=baseline)


if __name__ == "__main__":
    unittest.main()
