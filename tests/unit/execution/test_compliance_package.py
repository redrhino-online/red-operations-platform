"""Behavioral tests for the stage 9 launch compliance and consent package.

Rules under test come from SPEC.md section 4, stage 9 "QA" ("Launch Approved"
requires "consent where applicable") and section 9 ("Define retention, export and
deletion policies before onboarding production clients"), and from the reference
model canon that informs the stage 9 compliance assets: files 21 and 34 (SPEC.md
section 12.3 and 12.5). The canon treats the GDPR consent/acknowledgment, the
Facebook advertising disclaimer, the income and FTC disclaimer, the privacy
policy, the terms of use and attorney review as launch-blocking compliance assets
that "can kill your funnel or your business if you don't do them".

The package is pure domain and reject-only: a missing required asset cannot be
represented as present, and a scoped human waiver names a risk owner and never
makes an absent asset appear present (SPEC.md section 4). The policy refuses the
"Launch Approved" checkpoint's traffic authorization until every required
compliance asset exists or is covered by a live, owned waiver.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.execution.domain.entities import LaunchQA
from redops.contexts.execution.domain.errors import (
    ComplianceTenantBoundaryError,
    ExpiredComplianceWaiverError,
    InvalidComplianceError,
    InvalidLaunchQAError,
    LaunchQADependencyError,
    MissingComplianceAssetError,
)
from redops.contexts.execution.domain.value_objects import (
    ALWAYS_REQUIRED_COMPLIANCE_KINDS,
    ComplianceAssetKind,
)

from .fixtures import (
    authorization,
    compliance_asset,
    compliance_assets,
    compliance_package,
    compliance_waiver,
    launch_qa,
    ready_for_traffic,
)

ON = date(2026, 10, 3)
OTHER_TENANT = "client-other"


class ComplianceAssetTests(unittest.TestCase):
    def test_an_asset_keeps_its_kind_reference_and_version(self):
        asset = compliance_asset(
            ComplianceAssetKind.PRIVACY_POLICY,
            reference="asset://legal/privacy",
            version=3,
        )

        self.assertIs(ComplianceAssetKind.PRIVACY_POLICY, asset.kind)
        self.assertEqual("asset://legal/privacy", asset.reference)
        self.assertEqual(3, asset.version)

    def test_an_asset_requires_tenant_reference_and_a_positive_version(self):
        for override in (
            {"tenant_id": " "},
            {"reference": ""},
            {"version": 0},
            {"version": -1},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidComplianceError):
                    compliance_asset(ComplianceAssetKind.TERMS_OF_USE, **override)

    def test_an_asset_is_immutable(self):
        asset = compliance_asset(ComplianceAssetKind.TERMS_OF_USE)

        with self.assertRaises(FrozenInstanceError):
            asset.version = 9


class ComplianceWaiverTests(unittest.TestCase):
    def test_a_waiver_names_a_risk_owner_and_a_review_trigger(self):
        waiver = compliance_waiver(
            ComplianceAssetKind.INCOME_DISCLAIMER,
            risk_owner="red-principal",
            review_trigger="before EU traffic begins",
        )

        self.assertEqual("red-principal", waiver.risk_owner)
        self.assertEqual("before EU traffic begins", waiver.review_trigger)

    def test_a_waiver_requires_reason_risk_owner_and_review_trigger(self):
        for override in (
            {"reason": " "},
            {"risk_owner": ""},
            {"review_trigger": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidComplianceError):
                    compliance_waiver(
                        ComplianceAssetKind.TERMS_OF_USE, **override
                    )

    def test_a_waiver_expires_on_a_boundary_date(self):
        waiver = compliance_waiver(
            ComplianceAssetKind.TERMS_OF_USE, expires_on=date(2026, 10, 5)
        )

        self.assertFalse(waiver.is_expired(date(2026, 10, 5)))
        self.assertTrue(waiver.is_expired(date(2026, 10, 6)))


class CompliancePackageTests(unittest.TestCase):
    def test_a_package_keeps_its_assets_and_target_markets(self):
        package = compliance_package(target_markets=("us", "ca"))

        self.assertEqual(("us", "ca"), package.target_markets)
        self.assertEqual(
            len(tuple(ComplianceAssetKind)), len(package.assets)
        )

    def test_a_package_requires_identity_tenant_and_target_markets(self):
        for override in (
            {"package_id": " "},
            {"tenant_id": ""},
            {"target_markets": ()},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidComplianceError):
                    compliance_package(**override)

    def test_a_package_rejects_duplicate_assets_and_waivers(self):
        duplicate_assets = compliance_assets() + (
            compliance_asset(ComplianceAssetKind.TERMS_OF_USE),
        )
        with self.assertRaises(InvalidComplianceError):
            compliance_package(assets=duplicate_assets)

        duplicate_waivers = (
            compliance_waiver(ComplianceAssetKind.TERMS_OF_USE),
            compliance_waiver(ComplianceAssetKind.TERMS_OF_USE),
        )
        with self.assertRaises(InvalidComplianceError):
            compliance_package(
                assets=compliance_assets(kinds=ALWAYS_REQUIRED_COMPLIANCE_KINDS),
                waivers=duplicate_waivers,
            )

    def test_a_package_refuses_another_tenants_asset(self):
        with self.assertRaises(ComplianceTenantBoundaryError):
            compliance_package(
                assets=compliance_assets(tenant_id=OTHER_TENANT)
            )

    def test_a_non_consent_market_does_not_require_gdpr_consent(self):
        package = compliance_package(
            target_markets=("us",),
            assets=compliance_assets(kinds=ALWAYS_REQUIRED_COMPLIANCE_KINDS),
        )

        self.assertFalse(package.requires_consent)
        self.assertNotIn(
            ComplianceAssetKind.GDPR_CONSENT, package.required_kinds
        )
        self.assertTrue(package.is_complete(on=ON))

    def test_a_consent_jurisdiction_requires_gdpr_consent(self):
        package = compliance_package(
            target_markets=("eu",),
            assets=compliance_assets(kinds=ALWAYS_REQUIRED_COMPLIANCE_KINDS),
        )

        self.assertTrue(package.requires_consent)
        self.assertIn(ComplianceAssetKind.GDPR_CONSENT, package.required_kinds)
        self.assertFalse(package.is_complete(on=ON))

    def test_a_missing_required_asset_keeps_the_package_incomplete(self):
        package = compliance_package(
            assets=tuple(
                asset
                for asset in compliance_assets()
                if asset.kind is not ComplianceAssetKind.PRIVACY_POLICY
            )
        )

        self.assertFalse(package.is_complete(on=ON))
        self.assertIn(
            ComplianceAssetKind.PRIVACY_POLICY, package.missing_kinds
        )

    def test_a_live_owned_waiver_covers_an_absent_asset(self):
        package = compliance_package(
            assets=tuple(
                asset
                for asset in compliance_assets()
                if asset.kind is not ComplianceAssetKind.ATTORNEY_REVIEW
            ),
            waivers=(
                compliance_waiver(ComplianceAssetKind.ATTORNEY_REVIEW),
            ),
        )

        self.assertTrue(package.is_complete(on=ON))
        self.assertIn(
            ComplianceAssetKind.ATTORNEY_REVIEW, package.missing_kinds
        )
        self.assertIn(
            ComplianceAssetKind.ATTORNEY_REVIEW, package.waived_kinds
        )

    def test_a_waiver_never_makes_an_absent_asset_appear_present(self):
        package = compliance_package(
            assets=tuple(
                asset
                for asset in compliance_assets()
                if asset.kind is not ComplianceAssetKind.TERMS_OF_USE
            ),
            waivers=(compliance_waiver(ComplianceAssetKind.TERMS_OF_USE),),
        )

        self.assertNotIn(ComplianceAssetKind.TERMS_OF_USE, package.present_kinds)

    def test_an_expired_waiver_does_not_cover_an_absent_asset(self):
        package = compliance_package(
            assets=tuple(
                asset
                for asset in compliance_assets()
                if asset.kind is not ComplianceAssetKind.TERMS_OF_USE
            ),
            waivers=(
                compliance_waiver(
                    ComplianceAssetKind.TERMS_OF_USE,
                    expires_on=date(2026, 10, 1),
                ),
            ),
        )

        self.assertFalse(package.is_complete(on=ON))

    def test_a_package_is_immutable(self):
        package = compliance_package()

        with self.assertRaises(FrozenInstanceError):
            package.package_id = "tampered"


class LaunchComplianceTests(unittest.TestCase):
    def test_launch_is_refused_without_a_compliance_package(self):
        with self.assertRaises(MissingComplianceAssetError):
            launch_qa(compliance=None).authorize_traffic(
                authorization=authorization()
            )

    def test_launch_is_refused_when_a_required_asset_is_missing(self):
        package = compliance_package(
            assets=tuple(
                asset
                for asset in compliance_assets()
                if asset.kind is not ComplianceAssetKind.FACEBOOK_DISCLAIMER
            )
        )

        with self.assertRaises(MissingComplianceAssetError):
            launch_qa(compliance=package).authorize_traffic(
                authorization=authorization()
            )

    def test_launch_is_refused_when_a_waiver_is_expired(self):
        package = compliance_package(
            assets=tuple(
                asset
                for asset in compliance_assets()
                if asset.kind is not ComplianceAssetKind.INCOME_DISCLAIMER
            ),
            waivers=(
                compliance_waiver(
                    ComplianceAssetKind.INCOME_DISCLAIMER,
                    expires_on=date(2026, 10, 1),
                ),
            ),
        )

        with self.assertRaises(ExpiredComplianceWaiverError):
            launch_qa(compliance=package).authorize_traffic(
                authorization=authorization()
            )

    def test_launch_succeeds_with_a_complete_owned_package(self):
        approved = launch_qa().authorize_traffic(
            authorization=authorization()
        )

        self.assertTrue(approved.is_ready_for_traffic)
        self.assertIsNotNone(approved.compliance)

    def test_a_ready_qa_pins_the_reviewed_compliance_package(self):
        package = compliance_package()
        approved = launch_qa(compliance=package).authorize_traffic(
            authorization=authorization()
        )

        self.assertIs(package, approved.compliance)

    def test_a_qa_cannot_carry_another_tenants_compliance_package(self):
        with self.assertRaises(LaunchQADependencyError):
            launch_qa(compliance=compliance_package(tenant_id=OTHER_TENANT))

    def test_a_ready_qa_cannot_be_constructed_without_compliance(self):
        base = ready_for_traffic()

        with self.assertRaises(InvalidLaunchQAError):
            LaunchQA(
                qa_id=base.qa_id,
                tenant_id=base.tenant_id,
                funnel=base.funnel,
                owner=base.owner,
                designated_authority=base.designated_authority,
                checks=base.checks,
                state=base.state,
                authorization=base.authorization,
            )

    def test_a_draft_qa_may_omit_compliance_until_review(self):
        qa = launch_qa(compliance=None)

        self.assertIsNone(qa.compliance)
        self.assertFalse(qa.is_ready_for_traffic)


if __name__ == "__main__":
    unittest.main()
