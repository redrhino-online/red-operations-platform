"""Behavioral tests for the stage 0 "Production Ready" recording path.

Rules under test come from SPEC.md sections 3, 4, 5 and 11: a stage is complete
only when its required assets exist, pass a defined checkpoint, and receive
approval for downstream use; a passing gate "pins the exact evidence and intended
downstream use"; approval is version specific and the author cannot impersonate
the approver; a stage gate is approved by the client-designated authority and an
agent cannot confer human approval upon itself.

The Engagement context already assembles and validates the canonical stage 0 gate
(cycle 62) from the real ``ClientWorkspace`` (cycle 56), the twelve-kind
``IntakePackage`` (cycle 59), ``ProductionReadyPolicy`` (cycle 60) and
``GateApproverAuthorityPolicy`` (cycle 61). Governance owns the version-specific
``ApprovalRequest`` (cycle 2), ``GateDecision.from_gate`` (cycle 7) and the
``GateLedger`` (cycle 3). Nothing yet records the assembled gate as a passing
``Production Ready`` decision, so stage 0 still cannot close end to end in pure
domain. These tests assert the recording path issues one approved exact-version
request per required asset, records the passing decision against the workspace's
designated approver, and closes the stage 0 dependency for progress, while
refusing a gate whose approver or author is not real.
"""

import unittest
from datetime import date

from redops.contexts.engagement.domain.assemblies import (
    StageZeroGateAssembler,
    StageZeroGateRecorder,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    GateApproverNotAuthorizedError,
    GateAuthorRequiredError,
    NotStageZeroGateError,
)
from redops.contexts.engagement.domain.value_objects import (
    CANONICAL_INTAKE_KINDS,
    ClientAuthority,
    IntakeAsset,
    IntakeAssetKind,
    IntakePackage,
)
from redops.contexts.governance.domain.entities import GateLedger, StageGate
from redops.contexts.governance.domain.errors import (
    GateDecisionError,
    SelfApprovalError,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    ApprovalOutcome,
    AssetVersionRef,
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


def sourced_claim(claim_id: str = "claim-intake-1") -> Claim:
    return Claim(
        claim_id=claim_id,
        tenant_id=TENANT,
        statement="Intake fact recorded with the client",
        provenance=ProvenanceClass.KNOWN,
        citations=frozenset(
            {SourceCitation("source-intake", "sha256:abc", "p.1")}
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


def package(version: int = 1) -> IntakePackage:
    return IntakePackage(
        package_id="intake-3f",
        tenant_id=TENANT,
        assets=tuple(asset(kind, version) for kind in CANONICAL_INTAKE_KINDS),
    )


class StageZeroGateRecorderTests(unittest.TestCase):
    def setUp(self):
        self.recorder = StageZeroGateRecorder()
        self.assembler = StageZeroGateAssembler()
        self.template = stage_zero_to_ten_template()

    def assembled_gate(self, workspace_=None, package_=None, approver=APPROVER, proposed_by=OWNER):
        return self.assembler.assemble(
            template=self.template,
            workspace=workspace_ or workspace(),
            package=package_ or package(),
            approver=approver,
            claims=(sourced_claim(),),
            proposed_by=proposed_by,
        )

    def record(self, gate, ledger, workspace_=None, **overrides):
        return self.recorder.record(
            gate=gate,
            workspace=workspace_ or workspace(),
            ledger=ledger,
            scope=overrides.pop("scope", SCOPE),
            checkpoint_evidence=overrides.pop(
                "checkpoint_evidence", "all twelve stage 0 assets reviewed"
            ),
            rationale=overrides.pop("rationale", "intake complete and owned"),
            assigned_owner=overrides.pop("assigned_owner", OWNER),
            due_on=overrides.pop("due_on", DUE),
            on=overrides.pop("on", ON),
            **overrides,
        )

    def test_records_a_passing_stage_zero_decision_from_the_assembled_gate(self):
        gate = self.assembled_gate()
        ledger = GateLedger(self.template)

        decision = self.record(gate, ledger)

        self.assertEqual(0, decision.stage_number)
        self.assertIs(GateDisposition.APPROVED, decision.disposition)
        self.assertEqual(APPROVER, decision.reviewer)
        self.assertEqual(gate.required_assets, decision.required_assets)
        self.assertIs(decision, ledger.decision_for(0))
        self.assertTrue(ledger.has_passing_decision(0, on=ON))

    def test_the_decision_pins_the_exact_package_version_on_every_asset(self):
        gate = self.assembled_gate(package_=package(version=4))
        ledger = GateLedger(self.template)

        decision = self.record(gate, ledger)

        self.assertEqual(12, len(decision.required_assets))
        self.assertEqual({4}, {ref.version for ref in decision.required_assets})
        self.assertEqual(frozenset(), decision.unapproved_assets())

    def test_one_approved_exact_version_request_per_required_asset(self):
        gate = self.assembled_gate()
        ledger = GateLedger(self.template)

        decision = self.record(gate, ledger)

        self.assertEqual(12, len(decision.asset_approvals))
        for request in decision.asset_approvals:
            self.assertIs(ApprovalOutcome.APPROVED, request.outcome)
            self.assertEqual(SCOPE, request.scope)
            self.assertEqual(APPROVER, request.approver)
            self.assertIn(request.asset, decision.required_assets)
        self.assertEqual(frozenset(), decision.unapproved_assets())

    def test_the_recorded_decision_closes_stage_zero_for_verified_progress(self):
        ledger = GateLedger(self.template)

        self.record(self.assembled_gate(), ledger)

        progress = PipelineProgress.from_ledger(ledger, on=ON)
        self.assertEqual(1, progress.approved_gates)
        self.assertEqual(len(self.template.stages), progress.total_gates)

    def test_an_approver_without_workspace_authority_cannot_record(self):
        gate = self.assembled_gate()
        gate.approver = "stranger"
        ledger = GateLedger(self.template)

        with self.assertRaises(GateApproverNotAuthorizedError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(0))

    def test_a_gate_without_a_designated_approver_cannot_record(self):
        gate = self.assembled_gate()
        gate.approver = None
        ledger = GateLedger(self.template)

        with self.assertRaises(GateApproverNotAuthorizedError):
            self.record(gate, ledger)

    def test_a_gate_without_an_author_cannot_record(self):
        gate = self.assembled_gate(proposed_by=None)
        ledger = GateLedger(self.template)

        with self.assertRaises(GateAuthorRequiredError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(0))

    def test_the_author_cannot_approve_their_own_gate(self):
        gate = self.assembled_gate(approver=OWNER, proposed_by=OWNER)
        ledger = GateLedger(self.template)

        with self.assertRaises(SelfApprovalError):
            self.record(gate, ledger)

    def test_a_non_stage_zero_gate_cannot_be_recorded(self):
        stage_one_versions = {
            kind: 1 for kind in self.template.required_asset_kinds(1)
        }
        gate = StageGate.from_template(self.template, 1, stage_one_versions)
        gate.proposed_by = OWNER
        gate.approver = APPROVER
        ledger = GateLedger(self.template)

        with self.assertRaises(NotStageZeroGateError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(1))

    def test_an_under_declared_gate_cannot_be_forced_through(self):
        gate = StageGate(
            stage_number=0,
            template_version=self.template.version,
            required_assets=frozenset({AssetVersionRef("client-record", 1)}),
            checkpoint="Production Ready",
        )
        gate.proposed_by = OWNER
        gate.approver = APPROVER
        ledger = GateLedger(self.template)

        with self.assertRaises(GateDecisionError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(0))

    def test_recording_does_not_mutate_the_workspace(self):
        root = workspace()

        self.record(self.assembled_gate(workspace_=root), GateLedger(self.template), workspace_=root)

        self.assertEqual(2, len(root.authorities))


if __name__ == "__main__":
    unittest.main()
