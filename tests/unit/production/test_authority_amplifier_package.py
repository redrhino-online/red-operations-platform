"""Behavioral tests for the stage 7 "Authority Amplifier Approved" asset package.

Rules under test come from SPEC.md sections 3, 4 and 12.3. Stage 7 "Produce"
requires the approved script "in Promise, Proof, Problems, Steps, Context, Action
order" plus the storyboard, brand treatment, presentation, speaker notes,
recording, edited and hosted video and player assets, and its checkpoint is
"Authority Amplifier Approved": "message and supported proof pass review before
visual or video production; final asset gives a credible next action". The
reference model canon that informs this stage is files 13-18 and 28 (SPEC.md
section 12.3): the Authority Amplifier script and video, the slide template, the
style guide and branding images, and the recording and editing method.

Like the stage 1 ``DiagnosisPackage`` (cycle 69), stage 2 ``CurrencyPackage``
(cycle 71), stage 3 ``DiagnosticPackage`` (cycle 73), stage 4 ``SignaturePackage``
(cycle 75), stage 5 ``OfferPackage`` (cycle 77) and stage 6
``CampaignMessagePackage`` (cycle 79) bridges, this package projects the reviewed
stage 7 ``AuthorityAmplifier`` onto the nine canonical stage 7 asset kinds as
exact ``StageAssetVersion`` evidence so a canonical gate can be assembled. Unlike
the earlier constructively-complete values, an ``AuthorityAmplifier`` only owns
its visual assets after the script is approved and ``produce_visuals`` attaches a
complete ``VisualProductionPackage``, so the package refuses an amplifier that
has no visual package rather than pinning eight absent video kinds (SPEC.md
section 4: a missing asset prevents gate completion and a waiver never makes an
absent asset appear present). It also refuses a blank identity, a versionless
amplifier and a cross-tenant amplifier.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.production.domain.entities import AuthorityAmplifier
from redops.contexts.production.domain.errors import (
    AuthorityAmplifierTenantBoundaryError,
    InvalidAuthorityAmplifierPackageError,
)
from redops.contexts.production.domain.value_objects import (
    CANONICAL_AMPLIFIER_KINDS,
    AuthorityAmplifierPackage,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template

from ..commercial.fixtures import (
    approved_method,
    campaign_message,
    delivery_specification,
    offer_version,
)
from ..method.fixtures import signature_solution
from .fixtures import (
    TENANT,
    TODAY,
    USE,
    authority_amplifier,
    script_approved_amplifier,
    visual_package,
)

OTHER_TENANT = "client-other"


def other_tenant_amplifier() -> AuthorityAmplifier:
    solution = signature_solution(tenant_id=OTHER_TENANT)
    delivery = delivery_specification(signature_solution=solution)
    offer = offer_version(
        tenant_id=OTHER_TENANT, delivery_specification=delivery
    ).require_production_ready(
        (approved_method(tenant_id=OTHER_TENANT, solution=solution),)
    )
    message = campaign_message(offer=offer).approve(
        (approved_method(tenant_id=OTHER_TENANT, solution=solution),)
    )
    return authority_amplifier(
        message=message,
        amplifier_id="amplifier-other",
        tenant_id=OTHER_TENANT,
    )


def reviewed_amplifier() -> AuthorityAmplifier:
    amplifier = script_approved_amplifier().produce_visuals(
        package=visual_package()
    )
    return amplifier.approve_creative(
        approved_by="client-authority", intended_use=USE, on=TODAY
    )


def package(**overrides) -> AuthorityAmplifierPackage:
    values = {
        "package_id": "amplifier-package-3f",
        "tenant_id": TENANT,
        "amplifier": reviewed_amplifier(),
        "amplifier_version": 1,
    }
    values.update(overrides)
    return AuthorityAmplifierPackage(**values)


class AuthorityAmplifierPackageProjectionTests(unittest.TestCase):
    def test_the_package_projects_all_nine_canonical_stage_seven_kinds(self):
        assets = package().stage_asset_versions()

        kinds = {asset.kind for asset in assets}
        self.assertEqual(frozenset(CANONICAL_AMPLIFIER_KINDS), kinds)
        self.assertEqual(9, len(assets))

    def test_the_canonical_kinds_match_the_template_stage_seven_package(self):
        template_kinds = stage_zero_to_ten_template().required_asset_kinds(7)

        self.assertEqual(template_kinds, frozenset(CANONICAL_AMPLIFIER_KINDS))

    def test_every_kind_pins_the_reviewed_amplifier_at_its_exact_version(self):
        assets = package(amplifier_version=4).stage_asset_versions()

        self.assertEqual(9, len(assets))
        for asset in assets:
            self.assertEqual(4, asset.version)

    def test_each_kind_pins_the_reviewed_amplifier_identity(self):
        assets = package().stage_asset_versions()

        for asset in assets:
            self.assertEqual("amplifier-3f", asset.asset_id)

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


class AuthorityAmplifierPackageBoundaryTests(unittest.TestCase):
    def test_a_cross_tenant_amplifier_is_refused(self):
        with self.assertRaises(AuthorityAmplifierTenantBoundaryError):
            package(amplifier=other_tenant_amplifier())

    def test_a_blank_package_identity_is_refused(self):
        for override in ({"package_id": ""}, {"tenant_id": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidAuthorityAmplifierPackageError):
                    package(**override)

    def test_a_versionless_reviewed_amplifier_is_refused(self):
        for override in ({"amplifier_version": 0}, {"amplifier_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidAuthorityAmplifierPackageError):
                    package(**override)

    def test_an_amplifier_without_its_visual_package_is_refused(self):
        with self.assertRaises(InvalidAuthorityAmplifierPackageError):
            package(amplifier=authority_amplifier())

    def test_a_script_approved_amplifier_without_visuals_is_refused(self):
        with self.assertRaises(InvalidAuthorityAmplifierPackageError):
            package(amplifier=script_approved_amplifier())


if __name__ == "__main__":
    unittest.main()
