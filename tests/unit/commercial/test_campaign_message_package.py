"""Behavioral tests for the stage 6 "Campaign Message Approved" asset package.

Rules under test come from SPEC.md sections 3, 4 and 12.3. Stage 6 "Message"
requires the asset package "promise, problem hierarchy, desired outcome, proof
and objections, story, method explanation, CTA, lead magnet, hook, angles,
landing message, Authority Amplifier outline", and its checkpoint is "Campaign
Message Approved": "avatar, currency, problem, promise, method, product and CTA
agree". The reference model canon that informs this stage is files 06, 15, 24 and
25-28 (SPEC.md section 12.3): the Million Dollar Message reused in copy, 5P
messaging, the Authority Amplifier script as the universal content framework, and
the Content Roadmap and Content Crusher.

Like the stage 1 ``DiagnosisPackage`` (cycle 69), stage 2 ``CurrencyPackage``
(cycle 71), stage 3 ``DiagnosticPackage`` (cycle 73), stage 4 ``SignaturePackage``
(cycle 75) and stage 5 ``OfferPackage`` (cycle 77) bridges, this package projects
the reviewed stage 6 ``CampaignMessage`` onto the twelve canonical stage 6 asset
kinds as exact ``StageAssetVersion`` evidence so a canonical gate can be
assembled. It refuses a blank identity, a versionless message or a cross-tenant
message rather than silently pinning inexact or foreign evidence.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.entities import CampaignMessage
from redops.contexts.commercial.domain.errors import (
    CampaignMessageTenantBoundaryError,
    InvalidCampaignMessagePackageError,
)
from redops.contexts.commercial.domain.value_objects import (
    CANONICAL_MESSAGE_KINDS,
    CampaignMessagePackage,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template

from ..method.fixtures import signature_solution
from .fixtures import (
    TENANT,
    approved_method,
    campaign_message,
    content_roadmap,
    delivery_specification,
    offer_version,
)

OTHER_TENANT = "client-other"


def other_tenant_message() -> CampaignMessage:
    solution = signature_solution(tenant_id=OTHER_TENANT)
    delivery = delivery_specification(signature_solution=solution)
    offer = offer_version(
        tenant_id=OTHER_TENANT, delivery_specification=delivery
    ).require_production_ready(
        (approved_method(tenant_id=OTHER_TENANT, solution=solution),)
    )
    return campaign_message(offer=offer)


def package(**overrides) -> CampaignMessagePackage:
    values = {
        "package_id": "message-package-3f",
        "tenant_id": TENANT,
        "message": campaign_message(),
        "message_version": 1,
        "roadmap": content_roadmap(),
        "roadmap_version": 1,
    }
    values.update(overrides)
    return CampaignMessagePackage(**values)


class CampaignMessagePackageProjectionTests(unittest.TestCase):
    def test_the_package_projects_all_thirteen_canonical_stage_six_kinds(self):
        assets = package().stage_asset_versions()

        kinds = {asset.kind for asset in assets}
        self.assertEqual(frozenset(CANONICAL_MESSAGE_KINDS), kinds)
        self.assertEqual(13, len(assets))

    def test_the_canonical_kinds_match_the_template_stage_six_package(self):
        template_kinds = stage_zero_to_ten_template().required_asset_kinds(6)

        self.assertEqual(template_kinds, frozenset(CANONICAL_MESSAGE_KINDS))

    def test_the_twelve_message_kinds_pin_the_message_at_its_exact_version(self):
        assets = package(message_version=4).stage_asset_versions()

        message_assets = [
            asset for asset in assets if asset.kind != "content-roadmap"
        ]
        self.assertEqual(12, len(message_assets))
        for asset in message_assets:
            self.assertEqual(4, asset.version)

    def test_the_content_roadmap_kind_pins_the_roadmap_at_its_own_version(self):
        assets = package(roadmap_version=7).stage_asset_versions()

        roadmap_assets = {
            asset.kind: asset
            for asset in assets
            if asset.kind == "content-roadmap"
        }
        self.assertEqual(1, len(roadmap_assets))
        asset = roadmap_assets["content-roadmap"]
        self.assertEqual("roadmap-3f", asset.asset_id)
        self.assertEqual(7, asset.version)

    def test_each_message_kind_pins_the_reviewed_message_identity(self):
        assets = package().stage_asset_versions()

        message_assets = [
            asset for asset in assets if asset.kind != "content-roadmap"
        ]
        for asset in message_assets:
            self.assertEqual("message-3f", asset.asset_id)

    def test_the_projected_evidence_is_tenant_scoped(self):
        for asset in package().stage_asset_versions():
            self.assertEqual(TENANT, asset.tenant_id)

    def test_a_complete_package_reports_no_missing_kinds(self):
        value = package()

        self.assertTrue(value.is_complete)
        self.assertEqual((), value.missing_kinds())

    def test_the_package_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            package().package_id = "tampered"


class CampaignMessagePackageBoundaryTests(unittest.TestCase):
    def test_a_cross_tenant_message_is_refused(self):
        with self.assertRaises(CampaignMessageTenantBoundaryError):
            package(message=other_tenant_message())

    def test_a_blank_package_identity_is_refused(self):
        for override in ({"package_id": ""}, {"tenant_id": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidCampaignMessagePackageError):
                    package(**override)

    def test_a_versionless_reviewed_message_is_refused(self):
        for override in ({"message_version": 0}, {"message_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidCampaignMessagePackageError):
                    package(**override)

    def test_a_cross_tenant_roadmap_is_refused(self):
        with self.assertRaises(CampaignMessageTenantBoundaryError):
            package(
                roadmap=content_roadmap(
                    solution=signature_solution(tenant_id=OTHER_TENANT)
                )
            )

    def test_a_versionless_roadmap_is_refused(self):
        for override in ({"roadmap_version": 0}, {"roadmap_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidCampaignMessagePackageError):
                    package(**override)

    def test_an_untyped_roadmap_is_refused(self):
        with self.assertRaises(InvalidCampaignMessagePackageError):
            package(roadmap="not-a-roadmap")


if __name__ == "__main__":
    unittest.main()
