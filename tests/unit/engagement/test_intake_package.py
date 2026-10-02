"""Behavioral tests for the stage 0 "Intake" required asset package (pure domain).

Rules under test come from SPEC.md section 4, stage 0 "Intake": the required asset
package is the client record, signed scope, billing confirmation, questionnaire,
existing and brand asset inventories, access checklist, baseline measures,
workspace, communication channel, timeline, responsibilities and launch
definition, and the stage is complete only when its required assets exist and pass
the "Production Ready" checkpoint ("building for whom, success measure, owners,
boundaries, and prerequisites are explicit"). SPEC.md section 1 requires every
output to have a source and an owner, so each asset records a named owner and the
Knowledge claim ids that evidence it, and SPEC.md section 3 requires every child
resource to belong to exactly one client. These tests never invent a named client
approver; the governance template owns the exact required kinds.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    IncompleteIntakePackageError,
    IntakeOwnerNotAuthorizedError,
    InvalidIntakeAssetError,
    InvalidIntakePackageError,
    TenantBoundaryError,
    UnsourcedIntakeEvidenceError,
)
from redops.contexts.engagement.domain.policies import ProductionReadyPolicy
from redops.contexts.engagement.domain.value_objects import (
    CANONICAL_INTAKE_KINDS,
    ClientAuthority,
    IntakeAsset,
    IntakeAssetKind,
    IntakePackage,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.value_objects import (
    ProvenanceClass,
    SourceCitation,
)

ON = date(2026, 10, 2)
TENANT = "client-3f"
OWNER = "red-owner"


def workspace(**overrides) -> ClientWorkspace:
    values = {
        "workspace_id": "ws-3f",
        "tenant_id": TENANT,
        "authorities": (ClientAuthority(actor=OWNER, authority="production-owner"),),
    }
    values.update(overrides)
    return ClientWorkspace(**values)


def sourced_claim(
    claim_id: str = "claim-intake-1",
    *,
    tenant_id: str = TENANT,
    provenance: ProvenanceClass = ProvenanceClass.KNOWN,
    citations: frozenset[SourceCitation] | None = None,
) -> Claim:
    if citations is None:
        citations = (
            frozenset({SourceCitation("source-intake", "sha256:abc", "p.1")})
            if provenance is ProvenanceClass.KNOWN
            else frozenset()
        )
    return Claim(
        claim_id=claim_id,
        tenant_id=tenant_id,
        statement="Intake fact recorded with the client",
        provenance=provenance,
        citations=citations,
        confidence_note="captured during intake",
    )


def asset(kind: IntakeAssetKind, **overrides) -> IntakeAsset:
    values = {
        "asset_id": f"{kind.value}-3f@1",
        "tenant_id": TENANT,
        "kind": kind,
        "owner": OWNER,
        "summary": f"Recorded {kind.value}",
        "evidence_claim_ids": ("claim-intake-1",),
    }
    values.update(overrides)
    return IntakeAsset(**values)


def complete_assets(**overrides) -> tuple[IntakeAsset, ...]:
    return tuple(asset(kind, **overrides) for kind in CANONICAL_INTAKE_KINDS)


def package(assets=None, **overrides) -> IntakePackage:
    values = {
        "package_id": "intake-3f",
        "tenant_id": TENANT,
        "assets": complete_assets() if assets is None else assets,
    }
    values.update(overrides)
    return IntakePackage(**values)


class IntakeAssetKindTests(unittest.TestCase):
    def test_the_kinds_match_the_canonical_stage_zero_template(self):
        template_kinds = stage_zero_to_ten_template().required_asset_kinds(0)

        self.assertEqual(
            template_kinds,
            frozenset(kind.value for kind in IntakeAssetKind),
        )

    def test_every_canonical_kind_is_listed_once(self):
        self.assertEqual(len(IntakeAssetKind), len(CANONICAL_INTAKE_KINDS))
        self.assertEqual(12, len(CANONICAL_INTAKE_KINDS))


class IntakeAssetTests(unittest.TestCase):
    def test_an_asset_records_its_kind_owner_summary_and_sources(self):
        entry = asset(IntakeAssetKind.SIGNED_SCOPE)

        self.assertEqual(IntakeAssetKind.SIGNED_SCOPE, entry.kind)
        self.assertEqual(OWNER, entry.owner)
        self.assertEqual("Recorded signed-scope", entry.summary)
        self.assertEqual(("claim-intake-1",), entry.evidence_claim_ids)

    def test_an_asset_without_identity_owner_or_summary_is_rejected(self):
        for override in (
            {"asset_id": ""},
            {"tenant_id": "   "},
            {"owner": ""},
            {"summary": "  "},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidIntakeAssetError):
                    asset(IntakeAssetKind.TIMELINE, **override)

    def test_an_asset_without_a_source_is_rejected(self):
        for override in ({"evidence_claim_ids": ()}, {"evidence_claim_ids": ("  ",)}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidIntakeAssetError):
                    asset(IntakeAssetKind.BASELINE_MEASURES, **override)

    def test_an_asset_kind_must_be_canonical(self):
        with self.assertRaises(InvalidIntakeAssetError):
            IntakeAsset(
                asset_id="client-record-3f@1",
                tenant_id=TENANT,
                kind="client-record",
                owner=OWNER,
                summary="Recorded client record",
                evidence_claim_ids=("claim-intake-1",),
            )

    def test_an_asset_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            asset(IntakeAssetKind.CLIENT_RECORD).owner = "mallory"


class IntakePackageTests(unittest.TestCase):
    def test_a_complete_package_reports_every_kind_present(self):
        root = package()

        self.assertTrue(root.is_complete)
        self.assertEqual((), root.missing_kinds())
        self.assertEqual(set(IntakeAssetKind), set(root.kinds))

    def test_a_partial_package_reports_its_missing_kinds(self):
        partial = package(
            assets=(
                asset(IntakeAssetKind.CLIENT_RECORD),
                asset(IntakeAssetKind.SIGNED_SCOPE),
            )
        )

        self.assertFalse(partial.is_complete)
        self.assertIn(IntakeAssetKind.WORKSPACE, partial.missing_kinds())
        self.assertTrue(partial.has(IntakeAssetKind.CLIENT_RECORD))

    def test_a_package_retrieves_an_asset_by_kind(self):
        entry = package().asset(IntakeAssetKind.LAUNCH_DEFINITION)

        self.assertEqual(IntakeAssetKind.LAUNCH_DEFINITION, entry.kind)

    def test_retrieving_an_absent_asset_is_refused(self):
        partial = package(assets=(asset(IntakeAssetKind.CLIENT_RECORD),))

        with self.assertRaises(InvalidIntakePackageError):
            partial.asset(IntakeAssetKind.TIMELINE)

    def test_a_package_rejects_a_duplicate_asset_kind(self):
        with self.assertRaises(InvalidIntakePackageError):
            package(
                assets=(
                    asset(IntakeAssetKind.TIMELINE),
                    asset(IntakeAssetKind.TIMELINE, asset_id="timeline-3f@2"),
                )
            )

    def test_a_package_rejects_a_foreign_tenant_asset(self):
        with self.assertRaises(TenantBoundaryError):
            package(
                assets=(
                    asset(IntakeAssetKind.CLIENT_RECORD, tenant_id="client-other"),
                )
            )

    def test_a_package_without_identity_is_rejected(self):
        for override in ({"package_id": ""}, {"tenant_id": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidIntakePackageError):
                    package(**override)

    def test_a_package_reports_its_distinct_owners(self):
        root = package(
            assets=(
                asset(IntakeAssetKind.CLIENT_RECORD, owner="owner-a"),
                asset(IntakeAssetKind.SIGNED_SCOPE, owner="owner-b"),
            )
        )

        self.assertEqual(frozenset({"owner-a", "owner-b"}), root.owners)


class ProductionReadyPolicyTests(unittest.TestCase):
    def test_a_complete_owned_and_sourced_package_is_production_ready(self):
        ProductionReadyPolicy().require(
            package(), workspace(), (sourced_claim(),)
        )

    def test_an_incomplete_package_cannot_be_production_ready(self):
        partial = package(assets=(asset(IntakeAssetKind.CLIENT_RECORD),))

        with self.assertRaises(IncompleteIntakePackageError) as caught:
            ProductionReadyPolicy().require(partial, workspace(), (sourced_claim(),))
        self.assertIn("signed-scope", str(caught.exception))

    def test_a_package_for_another_tenant_cannot_be_production_ready(self):
        foreign = IntakePackage(
            package_id="intake-other",
            tenant_id="client-other",
            assets=complete_assets(tenant_id="client-other"),
        )

        with self.assertRaises(TenantBoundaryError):
            ProductionReadyPolicy().require(
                foreign, workspace(), (sourced_claim(tenant_id="client-other"),)
            )

    def test_an_asset_owned_by_a_non_authority_cannot_be_production_ready(self):
        unknown_owner = package(assets=complete_assets(owner="stranger"))

        with self.assertRaises(IntakeOwnerNotAuthorizedError):
            ProductionReadyPolicy().require(
                unknown_owner, workspace(), (sourced_claim(),)
            )

    def test_an_asset_with_unsourced_evidence_cannot_be_production_ready(self):
        with self.assertRaises(UnsourcedIntakeEvidenceError):
            ProductionReadyPolicy().require(
                package(),
                workspace(),
                (sourced_claim(provenance=ProvenanceClass.DERIVED),),
            )

    def test_an_asset_evidenced_by_another_client_cannot_be_production_ready(self):
        with self.assertRaises(UnsourcedIntakeEvidenceError):
            ProductionReadyPolicy().require(
                package(),
                workspace(),
                (sourced_claim(tenant_id="client-other"),),
            )

    def test_an_asset_whose_evidence_claim_is_absent_cannot_be_production_ready(self):
        with self.assertRaises(UnsourcedIntakeEvidenceError):
            ProductionReadyPolicy().require(
                package(), workspace(), (sourced_claim("claim-other"),)
            )


if __name__ == "__main__":
    unittest.main()
