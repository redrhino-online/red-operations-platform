"""Behavioral tests for the stage 3 "Diagnostic Model Approved" asset package.

Rules under test come from SPEC.md sections 3, 4 and 12.3. Stage 3 "Model"
requires the asset package "Profit Pyramid levels, observable measures,
symptoms, behaviors and problems per level, progression, qualification logic,
name, visual and explanatory copy", and its checkpoint is "Diagnostic Model
Approved": "a prospect can recognize their current level and desired next level
using observable differences". The reference model canon that informs this stage
is files 07 and 08 (SPEC.md section 12.3): the Profit Pyramid training and
examples require a clear currency, four observable levels with clear titles,
symptoms and metrics, one powerful visual model presented to every prospect, and
explanatory copy, graded by a pre-launch checklist.

Like the stage 1 ``DiagnosisPackage`` (cycle 69) and stage 2 ``CurrencyPackage``
(cycle 71) bridges, this package projects the reviewed stage 3 ``DiagnosticModel``
onto the ten canonical stage 3 asset kinds as exact ``StageAssetVersion``
evidence so a canonical gate can be assembled. It refuses a blank identity, a
versionless model or a cross-tenant model rather than silently pinning inexact
or foreign evidence.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    DiagnosticTenantBoundaryError,
    InvalidDiagnosticPackageError,
)
from redops.contexts.commercial.domain.value_objects import (
    CANONICAL_DIAGNOSTIC_KINDS,
    DiagnosticPackage,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.method.domain.entities import DiagnosticModel
from redops.contexts.method.domain.value_objects import ProfitPyramidLevel

TENANT = "client-3f"
OTHER_TENANT = "client-other"


def level(
    level_id: str,
    name: str,
    measure: str,
    tenant_id: str = TENANT,
) -> ProfitPyramidLevel:
    return ProfitPyramidLevel(
        level_id=level_id,
        tenant_id=tenant_id,
        name=name,
        observable_measures=(measure,),
        symptoms=(f"{name} symptoms",),
        behaviors=(f"{name} behaviors",),
        problems=(f"{name} problems",),
    )


def model(tenant_id: str = TENANT) -> DiagnosticModel:
    return DiagnosticModel(
        model_id="model-3f",
        tenant_id=tenant_id,
        name="Growth Pyramid",
        levels=(
            level("level-1", "Stuck", "under 4 qualified referrals per month", tenant_id),
            level("level-2", "Scaling", "12 or more qualified referrals per month", tenant_id),
        ),
        progression="climb from Stuck to Scaling by installing the referral network",
        qualification_logic="rank the prospect by observable monthly referral count",
        visual="asset://diagnostic/3f-growth-pyramid.png",
        explanatory_copy=(
            "Four levels from Stuck to Scaling, each placed by observable "
            "monthly referral count"
        ),
    )


def package(**overrides) -> DiagnosticPackage:
    values = {
        "package_id": "diagnostic-3f",
        "tenant_id": TENANT,
        "model": model(),
        "model_version": 1,
    }
    values.update(overrides)
    return DiagnosticPackage(**values)


class DiagnosticPackageProjectionTests(unittest.TestCase):
    def test_the_package_projects_all_ten_canonical_stage_three_kinds(self):
        assets = package().stage_asset_versions()

        kinds = {asset.kind for asset in assets}
        self.assertEqual(frozenset(CANONICAL_DIAGNOSTIC_KINDS), kinds)
        self.assertEqual(10, len(assets))

    def test_the_canonical_kinds_match_the_template_stage_three_package(self):
        template_kinds = stage_zero_to_ten_template().required_asset_kinds(3)

        self.assertEqual(template_kinds, frozenset(CANONICAL_DIAGNOSTIC_KINDS))

    def test_every_kind_pins_the_reviewed_model_at_its_exact_version(self):
        assets = package(model_version=4).stage_asset_versions()

        self.assertEqual(10, len(assets))
        for asset in assets:
            self.assertEqual(4, asset.version)

    def test_each_kind_pins_the_reviewed_model_identity(self):
        assets = package().stage_asset_versions()

        for asset in assets:
            self.assertEqual("model-3f", asset.asset_id)

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


class DiagnosticPackageBoundaryTests(unittest.TestCase):
    def test_a_cross_tenant_model_is_refused(self):
        with self.assertRaises(DiagnosticTenantBoundaryError):
            package(model=model(tenant_id=OTHER_TENANT))

    def test_a_blank_package_identity_is_refused(self):
        for override in ({"package_id": ""}, {"tenant_id": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidDiagnosticPackageError):
                    package(**override)

    def test_a_versionless_reviewed_model_is_refused(self):
        for override in ({"model_version": 0}, {"model_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidDiagnosticPackageError):
                    package(**override)


if __name__ == "__main__":
    unittest.main()
