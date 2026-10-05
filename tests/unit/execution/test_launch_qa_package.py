"""Behavioral tests for the stage 9 "Launch Approved" asset package.

Rules under test come from SPEC.md sections 3, 4 and 12.3. Stage 9 "QA" requires
the recorded message, technical and commercial tests on desktop and mobile, forms,
CRM, email, automation, booking, tracking, payment when relevant, handoff, client
approval, budget, creative, dashboard and the launch decision, and its checkpoint
is "Launch Approved": "all critical path checks pass, exceptions have owners, and
the designated human authorizes traffic". The reference model canon that informs
this stage is files 01, 08, 21, 22 and 24 (SPEC.md section 12.3): the pre-launch
QA criteria, the funnel pre-launch checklist, the compliance assets, and the
learning-versus-optimization and set-and-forget rules.

Like the stage 1 through 8 reviewed-asset bridges, this package projects the
reviewed stage 9 ``LaunchQA`` onto the seventeen canonical stage 9 asset kinds as
exact ``StageAssetVersion`` evidence so a canonical gate can be assembled. A
``LaunchQA`` only reaches ``LaunchQAState.READY_FOR_TRAFFIC`` after
``authorize_traffic`` passes the checkpoint on a complete same-tenant funnel and a
designated human authorization, so the package refuses a QA that has not passed
"Launch Approved" rather than pinning seventeen kinds for an unauthorized QA
(SPEC.md section 4: a missing asset prevents gate completion and a waiver never
makes an absent asset appear present). It also refuses a blank identity, a
versionless QA and a cross-tenant QA.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.execution.domain.entities import LaunchQA
from redops.contexts.execution.domain.enrollment import ENROLLMENT_PLAN_KIND
from redops.contexts.execution.domain.errors import (
    InvalidLaunchQAPackageError,
    LaunchQAPackageTenantBoundaryError,
)
from redops.contexts.execution.domain.swimlanes import SWIMLANES_PLAN_KIND
from redops.contexts.execution.domain.value_objects import (
    CANONICAL_LAUNCH_KIND_CHECKS,
    CANONICAL_LAUNCH_KINDS,
    COMPLIANCE_PACKAGE_KIND,
    LaunchQAPackage,
    QACheckKind,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template

from .fixtures import (
    TENANT,
    authorization,
    compliance_package,
    launch_checks,
    launch_qa,
    ready_for_traffic,
    swimlane_moves,
    swimlanes_plan,
)
from .test_enrollment import enrollment_plan
from .test_funnel_integration_package import other_tenant_complete_funnel
from ..method.fixtures import signature_solution

OTHER_TENANT = "client-other"


def other_tenant_ready_qa() -> LaunchQA:
    return LaunchQA(
        qa_id="qa-other",
        tenant_id=OTHER_TENANT,
        funnel=other_tenant_complete_funnel(),
        owner="qa-owner",
        designated_authority="client-authority",
        checks=launch_checks(),
        compliance=compliance_package(tenant_id=OTHER_TENANT),
    ).authorize_traffic(authorization=authorization())


def other_tenant_swimlanes_plan():
    return swimlanes_plan(
        tenant_id=OTHER_TENANT,
        funnel=other_tenant_complete_funnel(),
        moves=swimlane_moves(tenant_id=OTHER_TENANT),
    )


def other_tenant_enrollment_plan():
    return enrollment_plan(
        tenant_id=OTHER_TENANT,
        funnel=other_tenant_complete_funnel(),
        method=signature_solution(tenant_id=OTHER_TENANT),
    )


def package(**overrides) -> LaunchQAPackage:
    values = {
        "package_id": "launch-package-3f",
        "tenant_id": TENANT,
        "qa": ready_for_traffic(),
        "qa_version": 1,
        "swimlanes": swimlanes_plan(),
        "swimlanes_version": 1,
        "enrollment": enrollment_plan(),
        "enrollment_version": 1,
    }
    values.update(overrides)
    return LaunchQAPackage(**values)


class LaunchQAPackageProjectionTests(unittest.TestCase):
    def test_the_package_projects_all_nineteen_canonical_stage_nine_kinds(self):
        assets = package().stage_asset_versions()

        kinds = {asset.kind for asset in assets}
        self.assertEqual(frozenset(CANONICAL_LAUNCH_KINDS), kinds)
        self.assertEqual(19, len(assets))

    def test_the_canonical_kinds_match_the_template_stage_nine_package(self):
        template_kinds = stage_zero_to_ten_template().required_asset_kinds(9)

        self.assertEqual(template_kinds, frozenset(CANONICAL_LAUNCH_KINDS))

    def test_the_canonical_mapping_covers_every_qa_check_exactly_once(self):
        mapped = [
            check
            for checks in CANONICAL_LAUNCH_KIND_CHECKS.values()
            for check in checks
        ]

        self.assertEqual(
            sorted(kind.value for kind in QACheckKind),
            sorted(check.value for check in mapped),
        )
        self.assertEqual(len(mapped), len(set(mapped)))
        self.assertEqual(
            frozenset(CANONICAL_LAUNCH_KINDS),
            frozenset(CANONICAL_LAUNCH_KIND_CHECKS)
            | {COMPLIANCE_PACKAGE_KIND, SWIMLANES_PLAN_KIND, ENROLLMENT_PLAN_KIND},
        )

    def test_every_kind_pins_the_reviewed_qa_at_its_exact_version(self):
        assets = package(qa_version=4, swimlanes_version=4, enrollment_version=4).stage_asset_versions()

        self.assertEqual(19, len(assets))
        for asset in assets:
            self.assertEqual(4, asset.version)

    def test_the_check_kinds_pin_the_reviewed_qa_identity(self):
        assets = package().stage_asset_versions()

        for asset in assets:
            if asset.kind in (
                COMPLIANCE_PACKAGE_KIND,
                SWIMLANES_PLAN_KIND,
                ENROLLMENT_PLAN_KIND,
            ):
                continue
            self.assertEqual("qa-3f", asset.asset_id)

    def test_the_compliance_kind_pins_the_reviewed_compliance_package(self):
        assets = package().stage_asset_versions()

        compliance = [
            asset for asset in assets if asset.kind == COMPLIANCE_PACKAGE_KIND
        ]
        self.assertEqual(1, len(compliance))
        self.assertEqual("compliance-3f", compliance[0].asset_id)
        self.assertEqual(1, compliance[0].version)

    def test_the_swimlanes_kind_pins_the_reviewed_recovery_plan(self):
        assets = package(swimlanes_version=3).stage_asset_versions()

        swimlanes = [
            asset for asset in assets if asset.kind == SWIMLANES_PLAN_KIND
        ]
        self.assertEqual(1, len(swimlanes))
        self.assertEqual("swimlanes-3f", swimlanes[0].asset_id)
        self.assertEqual(3, swimlanes[0].version)

    def test_the_enrollment_kind_pins_the_reviewed_enrollment_plan(self):
        assets = package(enrollment_version=3).stage_asset_versions()

        enrollment = [
            asset for asset in assets if asset.kind == ENROLLMENT_PLAN_KIND
        ]
        self.assertEqual(1, len(enrollment))
        self.assertEqual("enrollment-3f", enrollment[0].asset_id)
        self.assertEqual(3, enrollment[0].version)

    def test_the_projected_evidence_is_tenant_scoped(self):
        for asset in package().stage_asset_versions():
            self.assertEqual(TENANT, asset.tenant_id)

    def test_a_ready_package_reports_no_missing_kinds(self):
        value = package()

        self.assertTrue(value.is_complete)
        self.assertEqual((), value.missing_kinds())

    def test_the_package_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            package().package_id = "tampered"


class LaunchQAPackageBoundaryTests(unittest.TestCase):
    def test_a_cross_tenant_qa_is_refused(self):
        with self.assertRaises(LaunchQAPackageTenantBoundaryError):
            package(qa=other_tenant_ready_qa())

    def test_a_blank_package_identity_is_refused(self):
        for override in ({"package_id": ""}, {"tenant_id": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidLaunchQAPackageError):
                    package(**override)

    def test_a_versionless_reviewed_qa_is_refused(self):
        for override in ({"qa_version": 0}, {"qa_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidLaunchQAPackageError):
                    package(**override)

    def test_a_draft_qa_is_refused(self):
        with self.assertRaises(InvalidLaunchQAPackageError):
            package(qa=launch_qa())

    def test_a_review_required_qa_is_refused(self):
        qa = ready_for_traffic().mark_review_required(reason="funnel changed")

        with self.assertRaises(InvalidLaunchQAPackageError):
            package(qa=qa)

    def test_a_cross_tenant_swimlanes_plan_is_refused(self):
        with self.assertRaises(LaunchQAPackageTenantBoundaryError):
            package(swimlanes=other_tenant_swimlanes_plan())

    def test_a_versionless_swimlanes_plan_is_refused(self):
        for override in ({"swimlanes_version": 0}, {"swimlanes_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidLaunchQAPackageError):
                    package(**override)

    def test_a_cross_tenant_enrollment_plan_is_refused(self):
        with self.assertRaises(LaunchQAPackageTenantBoundaryError):
            package(enrollment=other_tenant_enrollment_plan())

    def test_a_versionless_enrollment_plan_is_refused(self):
        for override in ({"enrollment_version": 0}, {"enrollment_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidLaunchQAPackageError):
                    package(**override)


if __name__ == "__main__":
    unittest.main()
