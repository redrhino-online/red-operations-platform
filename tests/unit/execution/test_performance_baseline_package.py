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
assembled. A ``PerformanceBaseline`` only reaches
``PerformanceBaselineState.ESTABLISHED`` after ``establish`` passes the
checkpoint on the stage 9 traffic authorization and an observed first qualified
traffic milestone, so the package refuses a baseline that has not passed
"Performance Baseline Established" rather than pinning twelve kinds for an
unestablished baseline (SPEC.md section 4: a missing asset prevents gate
completion and a waiver never makes an absent asset appear present). It also
refuses a blank identity, a versionless baseline and a cross-tenant baseline.
"""

import unittest
from dataclasses import FrozenInstanceError

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


def package(**overrides) -> PerformanceBaselinePackage:
    values = {
        "package_id": "baseline-package-3f",
        "tenant_id": TENANT,
        "baseline": established_baseline(),
        "baseline_version": 1,
    }
    values.update(overrides)
    return PerformanceBaselinePackage(**values)


class PerformanceBaselinePackageProjectionTests(unittest.TestCase):
    def test_the_package_projects_all_twelve_canonical_stage_ten_kinds(self):
        assets = package().stage_asset_versions()

        kinds = {asset.kind for asset in assets}
        self.assertEqual(frozenset(CANONICAL_BASELINE_KINDS), kinds)
        self.assertEqual(12, len(assets))

    def test_the_canonical_kinds_match_the_template_stage_ten_package(self):
        template_kinds = stage_zero_to_ten_template().required_asset_kinds(10)

        self.assertEqual(template_kinds, frozenset(CANONICAL_BASELINE_KINDS))

    def test_every_kind_pins_the_reviewed_baseline_at_its_exact_version(self):
        assets = package(baseline_version=4).stage_asset_versions()

        self.assertEqual(12, len(assets))
        for asset in assets:
            self.assertEqual(4, asset.version)

    def test_each_kind_pins_the_reviewed_baseline_identity(self):
        assets = package().stage_asset_versions()

        for asset in assets:
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
