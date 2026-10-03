"""Behavioral tests for the stage 3 "Diagnostic Model Approved" gate path.

Rules under test come from SPEC.md sections 3, 4, 5 and 11 and the reference
model canon (SPEC.md section 12.3 maps stage 3 "Model" to canon files 07 and 08).
A stage is complete only when its required assets exist, pass a defined
checkpoint, and receive approval for downstream use; a passing gate "pins the
exact evidence and intended downstream use"; a failed or expired prerequisite
blocks dependent authorization until resolved; a stage gate is approved by the
client-designated authority and an agent cannot confer human approval upon
itself; every output has an owner and a source.

Cycle 71 added the Commercial ``DiagnosticPackage`` bridge that projects the
single reviewed stage 3 ``DiagnosticModel`` onto the ten canonical stage 3 asset
kinds as exact ``StageAssetVersion`` evidence, so a canonical stage 3 gate can
now be assembled. This cycle wires the stage 3 "Diagnostic Model Approved" gate
end to end, mirroring the stage 1 and 2 paths: a pure Engagement assembler
validates the reviewed package against the workspace tenant and binds the
client-designated approver; a recorder issues one exact-version approval per kind
and writes the durable ``GateDecision``; an application use case chains them and
closes the stage 3 ``StageRun``. Stage 3 depends on stage 2, so the ledger must
already hold passing stage 0, stage 1 and stage 2 decisions. The stage 3
checkpoint turns on adjacent-level observable distinguishability, which
``DiagnosticModel`` already enforces at construction, so unlike stage 1 there is
no separate sourced-claim policy at this gate. These tests never invent a named
client approver or a concrete authority role.
"""

import unittest
from datetime import date

from redops.contexts.commercial.domain.value_objects import DiagnosticPackage
from redops.contexts.engagement.application.commands import (
    RecordStageThreeGateCommand,
)
from redops.contexts.engagement.application.handlers import (
    RecordStageThreeGateHandler,
)
from redops.contexts.engagement.domain.assemblies import (
    StageThreeGateAssembler,
    StageThreeGateRecorder,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    GateApproverNotAuthorizedError,
    GateAuthorRequiredError,
    NotStageThreeGateError,
    StageOwnerNotAuthorizedError,
    StageRunNotCompletableError,
    StageRunNotStageThreeError,
    TenantBoundaryError,
)
from redops.contexts.engagement.domain.value_objects import ClientAuthority
from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
    StageGate,
    StageRun,
)
from redops.contexts.governance.domain.errors import (
    GateDecisionError,
    SelfApprovalError,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    GateDisposition,
    GateState,
    PipelineProgress,
)
from redops.contexts.method.domain.entities import DiagnosticModel
from redops.contexts.method.domain.value_objects import ProfitPyramidLevel

ON = date(2026, 10, 3)
DUE = date(2026, 10, 17)
TENANT = "client-3f"
OTHER_TENANT = "client-other"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE_THREE = "stage-4-method"
CORRELATION = "corr-stage-3"


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


def level(level_id: str, name: str, measure: str, tenant_id: str = TENANT):
    return ProfitPyramidLevel(
        level_id=level_id,
        tenant_id=tenant_id,
        name=name,
        observable_measures=(measure,),
        symptoms=(f"{name} symptoms",),
        behaviors=(f"{name} behaviors",),
        problems=(f"{name} problems",),
    )


def model(*, tenant_id: str = TENANT) -> DiagnosticModel:
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


def package(*, tenant_id: str = TENANT, **overrides) -> DiagnosticPackage:
    values = {
        "package_id": "diagnostic-3f",
        "tenant_id": tenant_id,
        "model": model(tenant_id=tenant_id),
        "model_version": 1,
    }
    values.update(overrides)
    return DiagnosticPackage(**values)


def working_stage_run(stage_number: int = 3, **overrides) -> StageRun:
    values = {
        "engagement": "ws-3f",
        "stage_number": stage_number,
        "template_version": stage_zero_to_ten_template().version,
        "assigned_owner": OWNER,
    }
    values.update(overrides)
    run = StageRun(**values)
    run.start(
        actor=OWNER,
        reason="stage work began",
        on=ON,
        correlation_id=CORRELATION,
    )
    return run


def _seed_passing(
    ledger: GateLedger,
    template,
    stage_number: int,
    *,
    on: date = ON,
    scope: str = "seed",
) -> None:
    kinds = template.required_asset_kinds(stage_number)
    gate = StageGate.from_template(
        template, stage_number, {kind: 1 for kind in kinds}
    )
    gate.approver = APPROVER
    gate.proposed_by = OWNER
    for asset in sorted(gate.required_assets, key=str):
        request = ApprovalRequest(
            asset=asset,
            scope=scope,
            requested_by=OWNER,
            approver=APPROVER,
        )
        request.approve(actor=APPROVER, on=on, rationale="prerequisite evidenced")
        gate.record_asset_approval(request)
    gate.state = GateState.APPROVED
    decision = GateDecision.from_gate(
        gate,
        ledger=ledger,
        reviewer=APPROVER,
        scope=scope,
        checkpoint_evidence="prerequisite reviewed",
        disposition=GateDisposition.APPROVED,
        rationale="prerequisite complete and owned",
        on=on,
        assigned_owner=OWNER,
        due_on=DUE,
    )
    ledger.record(decision)


def seed_through_stage_two(ledger: GateLedger, template, *, on: date = ON) -> None:
    """Record passing stages 0, 1 and 2 so the stage 3 prerequisite is met."""

    for stage_number in (0, 1, 2):
        _seed_passing(ledger, template, stage_number, on=on, scope="seed")


class StageThreeGateAssemblerTests(unittest.TestCase):
    def setUp(self):
        self.assembler = StageThreeGateAssembler()
        self.template = stage_zero_to_ten_template()

    def assemble(self, *, workspace_=None, package_=None, approver=APPROVER, **overrides):
        return self.assembler.assemble(
            template=overrides.pop("template", self.template),
            workspace=workspace_ or workspace(),
            package=package_ or package(),
            approver=approver,
            **overrides,
        )

    def test_a_reviewed_diagnostic_package_assembles_the_canonical_stage_three_gate(self):
        gate = self.assemble()

        self.assertEqual(3, gate.stage_number)
        self.assertEqual(self.template.version, gate.template_version)
        self.assertEqual("Diagnostic Model Approved", gate.checkpoint)
        self.assertEqual(frozenset({2}), gate.dependencies)
        self.assertEqual(APPROVER, gate.approver)
        self.assertEqual(
            self.template.required_asset_kinds(3),
            {ref.asset_id for ref in gate.required_assets},
        )
        self.assertEqual(10, len(gate.required_assets))

    def test_the_gate_pins_the_exact_version_the_reviewed_model_carries(self):
        gate = self.assemble(package_=package(model_version=4))

        versions = {ref.asset_id: ref.version for ref in gate.required_assets}
        self.assertEqual(10, len(versions))
        for kind, version in versions.items():
            self.assertEqual(4, version, msg=kind)

    def test_the_assembler_records_the_author_distinct_from_the_approver(self):
        gate = self.assemble(proposed_by=OWNER)

        self.assertEqual(OWNER, gate.proposed_by)
        self.assertNotEqual(gate.approver, gate.proposed_by)

    def test_a_cross_tenant_package_cannot_assemble_a_gate(self):
        foreign = package(tenant_id=OTHER_TENANT)

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
        self.assertEqual("Growth Pyramid", box.model.name)


class StageThreeGateRecorderTests(unittest.TestCase):
    def setUp(self):
        self.recorder = StageThreeGateRecorder()
        self.assembler = StageThreeGateAssembler()
        self.template = stage_zero_to_ten_template()

    def seeded_ledger(self) -> GateLedger:
        ledger = GateLedger(self.template)
        seed_through_stage_two(ledger, self.template)
        return ledger

    def assembled_gate(self, approver=APPROVER, proposed_by=OWNER):
        return self.assembler.assemble(
            template=self.template,
            workspace=workspace(),
            package=package(),
            approver=approver,
            proposed_by=proposed_by,
        )

    def record(self, gate, ledger, **overrides):
        return self.recorder.record(
            gate=gate,
            workspace=overrides.pop("workspace_", workspace()),
            ledger=ledger,
            scope=overrides.pop("scope", SCOPE_THREE),
            checkpoint_evidence=overrides.pop(
                "checkpoint_evidence", "all ten stage 3 kinds reviewed"
            ),
            rationale=overrides.pop("rationale", "levels are observably distinct"),
            assigned_owner=overrides.pop("assigned_owner", OWNER),
            due_on=overrides.pop("due_on", DUE),
            on=overrides.pop("on", ON),
            **overrides,
        )

    def test_records_a_passing_stage_three_decision_from_the_assembled_gate(self):
        ledger = self.seeded_ledger()

        decision = self.record(self.assembled_gate(), ledger)

        self.assertEqual(3, decision.stage_number)
        self.assertIs(GateDisposition.APPROVED, decision.disposition)
        self.assertEqual("Diagnostic Model Approved", decision.checkpoint)
        self.assertEqual(frozenset({2}), decision.dependencies)
        self.assertEqual(APPROVER, decision.reviewer)
        self.assertIs(decision, ledger.decision_for(3))
        self.assertTrue(ledger.has_passing_decision(3, on=ON))

    def test_one_approved_exact_version_request_per_required_asset(self):
        ledger = self.seeded_ledger()

        decision = self.record(self.assembled_gate(), ledger)

        self.assertEqual(10, len(decision.asset_approvals))
        for request in decision.asset_approvals:
            self.assertEqual(SCOPE_THREE, request.scope)
            self.assertEqual(APPROVER, request.approver)
            self.assertIn(request.asset, decision.required_assets)
        self.assertEqual(frozenset(), decision.unapproved_assets())

    def test_a_non_stage_three_gate_cannot_be_recorded(self):
        kinds = self.template.required_asset_kinds(2)
        gate = StageGate.from_template(self.template, 2, {kind: 1 for kind in kinds})
        gate.proposed_by = OWNER
        gate.approver = APPROVER
        ledger = self.seeded_ledger()

        with self.assertRaises(NotStageThreeGateError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(3))

    def test_an_approver_without_workspace_authority_cannot_record(self):
        gate = self.assembled_gate()
        gate.approver = "stranger"
        ledger = self.seeded_ledger()

        with self.assertRaises(GateApproverNotAuthorizedError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(3))

    def test_a_gate_without_an_author_cannot_record(self):
        gate = self.assembled_gate(proposed_by=None)
        ledger = self.seeded_ledger()

        with self.assertRaises(GateAuthorRequiredError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(3))

    def test_the_author_cannot_approve_their_own_gate(self):
        gate = self.assembled_gate(approver=OWNER, proposed_by=OWNER)
        ledger = self.seeded_ledger()

        with self.assertRaises(SelfApprovalError):
            self.record(gate, ledger)

    def test_the_assigned_owner_must_hold_workspace_authority(self):
        gate = self.assembled_gate()
        ledger = self.seeded_ledger()

        with self.assertRaises(StageOwnerNotAuthorizedError):
            self.record(gate, ledger, assigned_owner="stranger")

    def test_recording_does_not_mutate_the_workspace(self):
        root = workspace()
        ledger = self.seeded_ledger()

        self.record(self.assembled_gate(), ledger, workspace_=root)

        self.assertEqual(2, len(root.authorities))


class RecordStageThreeGateHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = RecordStageThreeGateHandler()
        self.template = stage_zero_to_ten_template()

    def ledger(self) -> GateLedger:
        ledger = GateLedger(self.template)
        seed_through_stage_two(ledger, self.template)
        return ledger

    def command(self, *, workspace_=None, package_=None, stage_run_=None, **overrides):
        values = {
            "template": self.template,
            "workspace": workspace_ or workspace(),
            "package": package_ if package_ is not None else package(),
            "stage_run": stage_run_ if stage_run_ is not None else working_stage_run(),
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE_THREE,
            "checkpoint_evidence": "all ten stage 3 kinds reviewed",
            "rationale": "levels are observably distinct",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        values.update(overrides)
        return RecordStageThreeGateCommand(**values)

    def test_records_a_passing_stage_three_decision_and_closes_the_run(self):
        ledger = self.ledger()
        run = working_stage_run()

        decision = self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        self.assertEqual(3, decision.stage_number)
        self.assertIs(decision, ledger.decision_for(3))
        self.assertTrue(run.is_complete)
        self.assertIs(decision, run.accepted_decision)
        self.assertEqual(ON, run.exited_at)

    def test_verified_progress_counts_stages_zero_through_three(self):
        ledger = self.ledger()
        run = working_stage_run()

        self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        progress = PipelineProgress.from_ledger(ledger, on=ON)
        self.assertEqual(4, progress.approved_gates)
        self.assertTrue(run.is_complete)

    def test_a_run_for_another_stage_cannot_be_closed(self):
        ledger = self.ledger()

        with self.assertRaises(StageRunNotStageThreeError):
            self.handler.handle(
                self.command(stage_run_=working_stage_run(stage_number=4)),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(3))

    def test_a_run_for_another_template_version_cannot_be_closed(self):
        ledger = self.ledger()

        with self.assertRaises(StageRunNotStageThreeError):
            self.handler.handle(
                self.command(
                    stage_run_=working_stage_run(template_version="2025.9")
                ),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(3))

    def test_a_not_completable_run_does_not_record_a_decision(self):
        ledger = self.ledger()
        run = StageRun(
            engagement="ws-3f",
            stage_number=3,
            template_version=self.template.version,
            assigned_owner=OWNER,
        )

        with self.assertRaises(StageRunNotCompletableError):
            self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        self.assertIsNone(ledger.decision_for(3))
        self.assertFalse(run.is_complete)

    def test_stage_three_cannot_pass_while_stage_two_is_unapproved(self):
        ledger = GateLedger(self.template)
        _seed_passing(ledger, self.template, 0, on=ON, scope="seed-stage-0")
        _seed_passing(ledger, self.template, 1, on=ON, scope="seed-stage-1")

        with self.assertRaises(GateDecisionError):
            self.handler.handle(self.command(), ledger=ledger)

        self.assertIsNone(ledger.decision_for(3))

    def test_the_use_case_does_not_mutate_the_workspace_or_package(self):
        root = workspace()
        box = package()
        ledger = self.ledger()

        self.handler.handle(
            self.command(workspace_=root, package_=box), ledger=ledger
        )

        self.assertEqual(2, len(root.authorities))
        self.assertEqual("Growth Pyramid", box.model.name)


if __name__ == "__main__":
    unittest.main()
