"""Behavioral tests for the stage 0 gate assembly (pure domain).

Rules under test come from SPEC.md section 4: a stage is complete only when its
required assets exist, pass a defined checkpoint, and receive approval for
downstream use; a passing gate "pins the exact evidence and intended downstream
use", and the stage 0 "Production Ready" checkpoint requires owners and
prerequisites to be explicit. SPEC.md sections 4 and 5 require the gate to be
approved by the client-designated authority, not a free caller-supplied string,
and SPEC.md section 3 requires every child resource to belong to exactly one
client.

The Engagement context already owns the stage 0 ``ClientWorkspace`` (cycle 56),
the twelve-kind ``IntakePackage`` (cycle 59), the ``ProductionReadyPolicy``
(cycle 60) and the ``GateApproverAuthorityPolicy`` (cycle 61); Governance owns
``StageGate.from_assets`` (cycle 58). Nothing yet binds them into one canonical
stage 0 gate, so an unvalidated gate can still be handed to
``GateDecision.from_gate``. These tests assert the the assembler refuses a gate
that is not exactly the template's twelve asset versions with a named-authority
approver, and never invents a concrete human identity (SPEC.md section 11).
"""

import unittest
from datetime import date

from redops.contexts.engagement.domain.assemblies import StageZeroGateAssembler
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    GateApproverNotAuthorizedError,
    IncompleteIntakePackageError,
    IntakeOwnerNotAuthorizedError,
    TenantBoundaryError,
    UnsourcedIntakeEvidenceError,
)
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
APPROVER = "client-approver-1"


def workspace(**overrides) -> ClientWorkspace:
    values = {
        "workspace_id": "ws-3f",
        "tenant_id": TENANT,
        "authorities": (
            ClientAuthority(actor=OWNER, authority="production-owner"),
            ClientAuthority(actor=APPROVER, authority="client-designated-authority"),
        ),
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
        "version": 1,
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


class StageZeroGateAssemblerTests(unittest.TestCase):
    def setUp(self):
        self.assembler = StageZeroGateAssembler()
        self.template = stage_zero_to_ten_template()

    def assemble(self, *, workspace_=None, package_=None, approver=APPROVER, claims=None, **overrides):
        return self.assembler.assemble(
            template=overrides.pop("template", self.template),
            workspace=workspace_ or workspace(),
            package=package_ or package(),
            approver=approver,
            claims=claims if claims is not None else (sourced_claim(),),
            **overrides,
        )

    def test_a_ready_package_assembles_the_canonical_stage_zero_gate(self):
        gate = self.assemble()

        self.assertEqual(0, gate.stage_number)
        self.assertEqual(self.template.version, gate.template_version)
        self.assertEqual("Production Ready", gate.checkpoint)
        self.assertEqual(frozenset(), gate.dependencies)
        self.assertEqual(APPROVER, gate.approver)
        self.assertEqual(
            self.template.required_asset_kinds(0),
            {ref.asset_id for ref in gate.required_assets},
        )
        self.assertEqual(12, len(gate.required_assets))

    def test_the_gate_pins_the_exact_version_each_asset_carries(self):
        gate = self.assemble(package_=package(assets=complete_assets(version=4)))

        self.assertEqual({4}, {ref.version for ref in gate.required_assets})

    def test_the_assembler_records_the_author_distinct_from_the_approver(self):
        gate = self.assemble(proposed_by=OWNER)

        self.assertEqual(OWNER, gate.proposed_by)
        self.assertNotEqual(gate.approver, gate.proposed_by)

    def test_a_partial_package_cannot_assemble_a_gate(self):
        partial = package(assets=(asset(IntakeAssetKind.CLIENT_RECORD),))

        with self.assertRaises(IncompleteIntakePackageError):
            self.assemble(package_=partial)

    def test_a_package_owned_by_a_non_authority_cannot_assemble_a_gate(self):
        unknown_owner = package(assets=complete_assets(owner="stranger"))

        with self.assertRaises(IntakeOwnerNotAuthorizedError):
            self.assemble(package_=unknown_owner)

    def test_unsourced_evidence_cannot_assemble_a_gate(self):
        with self.assertRaises(UnsourcedIntakeEvidenceError):
            self.assemble(
                claims=(sourced_claim(provenance=ProvenanceClass.DERIVED),)
            )

    def test_a_cross_tenant_package_cannot_assemble_a_gate(self):
        foreign = IntakePackage(
            package_id="intake-other",
            tenant_id="client-other",
            assets=complete_assets(tenant_id="client-other"),
        )

        with self.assertRaises(TenantBoundaryError):
            self.assemble(package_=foreign)

    def test_an_approver_without_workspace_authority_cannot_assemble_a_gate(self):
        with self.assertRaises(GateApproverNotAuthorizedError) as caught:
            self.assemble(approver="stranger")
        self.assertIn("stranger", str(caught.exception))

    def test_an_absent_approver_cannot_assemble_a_gate(self):
        with self.assertRaises(GateApproverNotAuthorizedError):
            self.assemble(approver="")

    def test_the_assembler_does_not_mutate_the_workspace_or_package(self):
        root = workspace()
        box = package()

        self.assemble(workspace_=root, package_=box)

        self.assertEqual(2, len(root.authorities))
        self.assertEqual(len(CANONICAL_INTAKE_KINDS), len(box.assets))


if __name__ == "__main__":
    unittest.main()
