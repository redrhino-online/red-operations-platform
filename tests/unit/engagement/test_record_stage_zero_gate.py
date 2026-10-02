"""Behavioral tests for the stage 0 gate recording use case (application layer).

SPEC.md section 6 gives the onion dependency rule: application use cases depend
on domain types and ports, and the API and workers call use cases rather than
mutating persistence directly. SPEC.md section 4 makes a stage complete only
when its required assets exist, pass the checkpoint, and receive approval for
downstream use, and a passing gate pins "the exact evidence and intended
downstream use".

The Engagement domain already assembles the canonical stage 0 gate
(``StageZeroGateAssembler``, cycle 62) and records the passing decision
(``StageZeroGateRecorder``, cycle 63). But those are two separate domain
services a caller must remember to chain, and the recorder trusts the
``StageGate`` it is handed, so a caller can bypass ``ProductionReadyPolicy``
(owner authority and sourced evidence) by building the gate directly. This use
case is the application boundary that owns assembly *and* recording, so a stage
0 gate can only be produced from a real ``IntakePackage`` whose owners and
evidence the policy has checked. These tests assert the use case records a
passing decision for the exact package versions and refuses a package that is
not production ready, without mutating the workspace or package.
"""

import unittest
from datetime import date

from redops.contexts.engagement.application.commands import (
    RecordStageZeroGateCommand,
)
from redops.contexts.engagement.application.handlers import (
    RecordStageZeroGateHandler,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    GateApproverNotAuthorizedError,
    IncompleteIntakePackageError,
    IntakeOwnerNotAuthorizedError,
    UnsourcedIntakeEvidenceError,
)
from redops.contexts.engagement.domain.value_objects import (
    CANONICAL_INTAKE_KINDS,
    ClientAuthority,
    IntakeAsset,
    IntakeAssetKind,
    IntakePackage,
)
from redops.contexts.governance.domain.entities import GateLedger
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    GateDisposition,
    PipelineProgress,
)
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.value_objects import (
    ProvenanceClass,
    SourceCitation,
)

ON = date(2026, 10, 2)
DUE = date(2026, 10, 16)
TENANT = "client-3f"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE = "stage-1-diagnosis"


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
    provenance: ProvenanceClass = ProvenanceClass.KNOWN,
) -> Claim:
    return Claim(
        claim_id=claim_id,
        tenant_id=TENANT,
        statement="Intake fact recorded with the client",
        provenance=provenance,
        citations=(
            frozenset({SourceCitation("source-intake", "sha256:abc", "p.1")})
            if provenance is ProvenanceClass.KNOWN
            else frozenset()
        ),
        confidence_note="captured during intake",
    )


def asset(kind: IntakeAssetKind, version: int = 1, **overrides) -> IntakeAsset:
    values = {
        "asset_id": f"{kind.value}-3f@{version}",
        "tenant_id": TENANT,
        "kind": kind,
        "version": version,
        "owner": OWNER,
        "summary": f"Recorded {kind.value}",
        "evidence_claim_ids": ("claim-intake-1",),
    }
    values.update(overrides)
    return IntakeAsset(**values)


def package(version: int = 1, **overrides) -> IntakePackage:
    values = {
        "package_id": "intake-3f",
        "tenant_id": TENANT,
        "assets": tuple(asset(kind, version) for kind in CANONICAL_INTAKE_KINDS),
    }
    values.update(overrides)
    return IntakePackage(**values)


class RecordStageZeroGateHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = RecordStageZeroGateHandler()
        self.template = stage_zero_to_ten_template()

    def command(self, *, workspace_=None, package_=None, claims=None, **overrides):
        values = {
            "template": self.template,
            "workspace": workspace_ or workspace(),
            "package": package_ or package(),
            "claims": claims if claims is not None else (sourced_claim(),),
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE,
            "checkpoint_evidence": "all twelve stage 0 assets reviewed",
            "rationale": "intake complete and owned",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
        }
        values.update(overrides)
        return RecordStageZeroGateCommand(**values)

    def test_records_a_passing_stage_zero_decision_from_the_real_package(self):
        ledger = GateLedger(self.template)

        decision = self.handler.handle(self.command(), ledger=ledger)

        self.assertEqual(0, decision.stage_number)
        self.assertIs(GateDisposition.APPROVED, decision.disposition)
        self.assertEqual(APPROVER, decision.reviewer)
        self.assertIs(decision, ledger.decision_for(0))
        self.assertEqual(
            1, PipelineProgress.from_ledger(ledger, on=ON).approved_gates
        )

    def test_the_use_case_pins_the_exact_version_each_asset_carries(self):
        ledger = GateLedger(self.template)

        decision = self.handler.handle(
            self.command(package_=package(version=4)), ledger=ledger
        )

        self.assertEqual(12, len(decision.required_assets))
        self.assertEqual({4}, {ref.version for ref in decision.required_assets})
        self.assertEqual(frozenset(), decision.unapproved_assets())

    def test_the_use_case_owns_assembly_so_owner_authority_cannot_be_bypassed(self):
        ledger = GateLedger(self.template)
        unknown_owner = package(
            assets=tuple(
                asset(kind, owner="stranger") for kind in CANONICAL_INTAKE_KINDS
            )
        )

        with self.assertRaises(IntakeOwnerNotAuthorizedError):
            self.handler.handle(self.command(package_=unknown_owner), ledger=ledger)

        self.assertIsNone(ledger.decision_for(0))

    def test_the_use_case_owns_assembly_so_sourced_evidence_cannot_be_bypassed(self):
        ledger = GateLedger(self.template)

        with self.assertRaises(UnsourcedIntakeEvidenceError):
            self.handler.handle(
                self.command(
                    claims=(sourced_claim(provenance=ProvenanceClass.DERIVED),)
                ),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(0))

    def test_an_incomplete_package_cannot_record_a_passing_decision(self):
        ledger = GateLedger(self.template)
        partial = package(assets=(asset(IntakeAssetKind.CLIENT_RECORD),))

        with self.assertRaises(IncompleteIntakePackageError):
            self.handler.handle(self.command(package_=partial), ledger=ledger)

        self.assertIsNone(ledger.decision_for(0))

    def test_an_approver_without_workspace_authority_cannot_record(self):
        ledger = GateLedger(self.template)

        with self.assertRaises(GateApproverNotAuthorizedError):
            self.handler.handle(self.command(approver="stranger"), ledger=ledger)

        self.assertIsNone(ledger.decision_for(0))

    def test_the_use_case_does_not_mutate_the_workspace_or_package(self):
        root = workspace()
        box = package()

        self.handler.handle(
            self.command(workspace_=root, package_=box), ledger=GateLedger(self.template)
        )

        self.assertEqual(2, len(root.authorities))
        self.assertEqual(len(CANONICAL_INTAKE_KINDS), len(box.assets))


if __name__ == "__main__":
    unittest.main()
