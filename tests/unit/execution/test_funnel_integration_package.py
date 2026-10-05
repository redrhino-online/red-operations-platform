"""Behavioral tests for the stage 8 "Funnel Complete" asset package.

Rules under test come from SPEC.md sections 3, 4 and 12.3. Stage 8 "Integrate"
requires the campaign architecture, pages, forms, qualification, booking,
sequences, CRM, tags, automation, analytics, tracking, sales handoff and SOPs,
and its checkpoint is "Funnel Complete": "a test prospect completes capture,
engagement and conversion handoffs with reliable records and ownership". The
reference model canon that informs this stage is files 13, 14, 21 and 22 (SPEC.md
section 12.3): the CAC funnel, the funnel template, PAG tracking
(pixel/audience/goal), the page set (opt-in, amplifier, scheduling,
confirmation/homework, checkout), Swimlanes and the Funnel Finder.

Like the stage 1 ``DiagnosisPackage`` (cycle 69), stage 2 ``CurrencyPackage``
(cycle 71), stage 3 ``DiagnosticPackage`` (cycle 73), stage 4 ``SignaturePackage``
(cycle 75), stage 5 ``OfferPackage`` (cycle 77), stage 6 ``CampaignMessagePackage``
(cycle 79) and stage 7 ``AuthorityAmplifierPackage`` (cycle 81) bridges, this
package projects the reviewed stage 8 ``FunnelIntegration`` onto the fourteen
canonical stage 8 asset kinds as exact ``StageAssetVersion`` evidence so a
canonical gate can be assembled. The methodology owner also made the canon
Swimlanes channel model a required stage 8 kind (owner decision 2026-10-04), so the
``swimlanes-plan`` kind is pinned from the reviewed ``SwimlanesPlan`` identity. A
``FunnelIntegration`` only reaches
``FunnelState.COMPLETE`` after ``mark_funnel_complete`` passes the checkpoint on a
same-tenant prospect path dry run, so the package refuses a funnel that has not
passed "Funnel Complete" rather than pinning fourteen kinds for an incomplete
funnel (SPEC.md section 4: a missing asset prevents gate completion and a waiver
never makes an absent asset appear present). It also refuses a blank identity, a
versionless funnel and a cross-tenant funnel.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.execution.domain.entities import FunnelIntegration
from redops.contexts.execution.domain.errors import (
    FunnelIntegrationPackageTenantBoundaryError,
    InvalidFunnelIntegrationPackageError,
)
from redops.contexts.execution.domain.value_objects import (
    CANONICAL_FUNNEL_KINDS,
    HANDOFF_ORDER,
    ProspectPathDryRun,
    FunnelIntegrationPackage,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template

from ..commercial.fixtures import (
    approved_method,
    campaign_message,
    delivery_specification,
    offer_version,
)
from ..method.fixtures import signature_solution
from ..production.fixtures import (
    TODAY,
    USE,
    authority_amplifier,
    known_claim,
    visual_package,
)
from .fixtures import (
    TENANT,
    complete_funnel,
    funnel_assets,
    funnel_integration,
    handoff,
    swimlane_moves,
    swimlanes_plan,
)

OTHER_TENANT = "client-other"


def other_tenant_complete_funnel() -> FunnelIntegration:
    solution = signature_solution(tenant_id=OTHER_TENANT)
    delivery = delivery_specification(signature_solution=solution)
    method = approved_method(tenant_id=OTHER_TENANT, solution=solution)
    offer = offer_version(
        tenant_id=OTHER_TENANT, delivery_specification=delivery
    ).require_production_ready((method,))
    message = campaign_message(offer=offer).approve((method,))
    amplifier = authority_amplifier(
        message=message,
        amplifier_id="amplifier-other",
        tenant_id=OTHER_TENANT,
    )
    amplifier = (
        amplifier.approve_script(
            approved_by="production-manager",
            intended_use=USE,
            on=TODAY,
            approved_methods=(method,),
            claims=(known_claim(tenant_id=OTHER_TENANT),),
        )
        .produce_visuals(package=visual_package())
        .approve_creative(
            approved_by="client-authority", intended_use=USE, on=TODAY
        )
    )
    return FunnelIntegration(
        integration_id="funnel-other",
        tenant_id=OTHER_TENANT,
        amplifier=amplifier,
        owner="funnel-owner",
        assets=funnel_assets(),
    ).mark_funnel_complete(
        ProspectPathDryRun(
            dry_run_id="dry-run-other",
            tenant_id=OTHER_TENANT,
            handoffs=tuple(
                handoff(kind, tenant_id=OTHER_TENANT)
                for kind in HANDOFF_ORDER
            ),
        )
    )


def package(**overrides) -> FunnelIntegrationPackage:
    values = {
        "package_id": "funnel-package-3f",
        "tenant_id": TENANT,
        "funnel": complete_funnel(),
        "funnel_version": 1,
        "swimlanes": swimlanes_plan(),
        "swimlanes_version": 1,
    }
    values.update(overrides)
    return FunnelIntegrationPackage(**values)


class FunnelIntegrationPackageProjectionTests(unittest.TestCase):
    def test_the_package_projects_all_fourteen_canonical_stage_eight_kinds(self):
        assets = package().stage_asset_versions()

        kinds = {asset.kind for asset in assets}
        self.assertEqual(frozenset(CANONICAL_FUNNEL_KINDS), kinds)
        self.assertEqual(14, len(assets))

    def test_the_canonical_kinds_match_the_template_stage_eight_package(self):
        template_kinds = stage_zero_to_ten_template().required_asset_kinds(8)

        self.assertEqual(template_kinds, frozenset(CANONICAL_FUNNEL_KINDS))

    def test_every_kind_pins_the_reviewed_funnel_at_its_exact_version(self):
        assets = package(funnel_version=4, swimlanes_version=3).stage_asset_versions()

        self.assertEqual(14, len(assets))
        for asset in assets:
            expected = 3 if asset.kind == "swimlanes-plan" else 4
            self.assertEqual(expected, asset.version)

    def test_each_kind_pins_the_reviewed_funnel_identity(self):
        assets = package().stage_asset_versions()

        for asset in assets:
            if asset.kind == "swimlanes-plan":
                self.assertEqual("swimlanes-3f", asset.asset_id)
            else:
                self.assertEqual("funnel-3f", asset.asset_id)

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


class FunnelIntegrationPackageBoundaryTests(unittest.TestCase):
    def test_a_cross_tenant_funnel_is_refused(self):
        with self.assertRaises(FunnelIntegrationPackageTenantBoundaryError):
            package(funnel=other_tenant_complete_funnel())

    def test_a_blank_package_identity_is_refused(self):
        for override in ({"package_id": ""}, {"tenant_id": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidFunnelIntegrationPackageError):
                    package(**override)

    def test_a_versionless_reviewed_funnel_is_refused(self):
        for override in ({"funnel_version": 0}, {"funnel_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidFunnelIntegrationPackageError):
                    package(**override)

    def test_a_versionless_swimlanes_plan_is_refused(self):
        for override in ({"swimlanes_version": 0}, {"swimlanes_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidFunnelIntegrationPackageError):
                    package(**override)

    def test_a_cross_tenant_swimlanes_plan_is_refused(self):
        plan = swimlanes_plan(
            funnel=other_tenant_complete_funnel(),
            tenant_id=OTHER_TENANT,
            moves=swimlane_moves(tenant_id=OTHER_TENANT),
        )

        with self.assertRaises(FunnelIntegrationPackageTenantBoundaryError):
            package(swimlanes=plan)

    def test_a_draft_funnel_is_refused(self):
        with self.assertRaises(InvalidFunnelIntegrationPackageError):
            package(funnel=funnel_integration())

    def test_a_review_required_funnel_is_refused(self):
        funnel = complete_funnel().mark_review_required(
            reason="upstream amplifier changed"
        )

        with self.assertRaises(InvalidFunnelIntegrationPackageError):
            package(funnel=funnel)


if __name__ == "__main__":
    unittest.main()
