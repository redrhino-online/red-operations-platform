"""Behavioral tests for the stage 9 "Launch Approved" gate path.

Rules under test come from SPEC.md sections 3, 4, 5 and 11 and the reference
model canon (SPEC.md section 12.3 maps stage 9 "QA" to canon files 01, 08, 21, 22
and 24). A stage is complete only when its required assets exist, pass a defined
checkpoint, and receive approval for downstream use; a passing gate "pins the
exact evidence and intended downstream use"; the "Launch Approved" checkpoint
requires "all critical path checks pass, exceptions have owners, and the
designated human authorizes traffic"; a failed or expired prerequisite blocks
dependent authorization until resolved; a stage gate is approved by the
client-designated authority and an agent cannot confer human approval upon
itself; every output has an owner and a source. Stage 9 shows Ready for Traffic,
not live or completed.

Cycle 85 added the Execution ``LaunchQAPackage`` bridge that projects the reviewed
stage 9 ``LaunchQA`` onto the sixteen canonical stage 9 asset kinds as exact
``StageAssetVersion`` evidence, so a canonical stage 9 gate can now be assembled.
This cycle wires the stage 9 "Launch Approved" gate end to end, mirroring the
stage 8 path: a pure Engagement assembler validates the reviewed package against
the workspace tenant and binds the client-designated approver; a recorder issues
one exact-version approval per kind and writes the durable ``GateDecision``; an
application use case chains them and closes the stage 9 ``StageRun``. Stage 9
depends on stage 8, so the ledger must already hold passing stage 0 through stage
8 decisions. These tests never invent a named client approver or a concrete
authority role.
"""

import unittest
from datetime import date

from redops.contexts.engagement.application.commands import (
    RecordStageNineGateCommand,
)
from redops.contexts.engagement.application.handlers import (
    RecordStageNineGateHandler,
)
from redops.contexts.engagement.domain.assemblies import (
    StageNineGateAssembler,
    StageNineGateRecorder,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    GateApproverNotAuthorizedError,
    GateAuthorRequiredError,
    NotStageNineGateError,
    StageOwnerNotAuthorizedError,
    StageRunNotCompletableError,
    StageRunNotStageNineError,
    TenantBoundaryError,
)
from redops.contexts.engagement.domain.value_objects import ClientAuthority
from redops.contexts.execution.domain.entities import LaunchQA
from redops.contexts.execution.domain.value_objects import (
    CANONICAL_LAUNCH_KINDS,
    LaunchQAPackage,
)
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

from ..execution.fixtures import (
    TENANT,
    authorization,
    compliance_package,
    launch_checks,
    ready_for_traffic,
)
from ..execution.test_funnel_integration_package import (
    other_tenant_complete_funnel,
)

ON = date(2026, 10, 3)
DUE = date(2026, 10, 17)
OTHER_TENANT = "client-other"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE_NINE = "stage-10-launch"
CORRELATION = "corr-stage-9"


def other_tenant_ready_qa() -> LaunchQA:
    return LaunchQA(
        qa_id="qa-other",
        tenant_id=OTHER_TENANT,
        funnel=other_tenant_complete_funnel(),
        owner="qa-owner",
        designated_authority="client-authority",
        checks=launch_checks(),
        compliance=compliance_package(tenant_id=OTHER_TENANT),
    ).authorize_traffic(authorization=authorization())


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


def package(**overrides) -> LaunchQAPackage:
    values = {
        "package_id": "launch-package-3f",
        "tenant_id": TENANT,
        "qa": ready_for_traffic(),
        "qa_version": 1,
    }
    values.update(overrides)
    return LaunchQAPackage(**values)


def other_tenant_package(**overrides) -> LaunchQAPackage:
    values = {
        "package_id": "launch-package-other",
        "tenant_id": OTHER_TENANT,
        "qa": other_tenant_ready_qa(),
        "qa_version": 1,
    }
    values.update(overrides)
    return LaunchQAPackage(**values)


def working_stage_run(stage_number: int = 9, **overrides) -> StageRun:
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


def seed_through_stage_eight(ledger: GateLedger, template, *, on: date = ON) -> None:
    """Record passing stages 0 through 8 so the stage 9 prerequisite is met."""

    for stage_number in (0, 1, 2, 3, 4, 5, 6, 7, 8):
        _seed_passing(ledger, template, stage_number, on=on, scope="seed")


class StageNineGateAssemblerTests(unittest.TestCase):
    def setUp(self):
        self.assembler = StageNineGateAssembler()
        self.template = stage_zero_to_ten_template()

    def assemble(self, *, workspace_=None, package_=None, approver=APPROVER, **overrides):
        return self.assembler.assemble(
            template=overrides.pop("template", self.template),
            workspace=workspace_ or workspace(),
            package=package_ or package(),
            approver=approver,
            **overrides,
        )

    def test_a_reviewed_launch_qa_package_assembles_the_canonical_stage_nine_gate(self):
        gate = self.assemble()

        self.assertEqual(9, gate.stage_number)
        self.assertEqual(self.template.version, gate.template_version)
        self.assertEqual("Launch Approved", gate.checkpoint)
        self.assertEqual(frozenset({8}), gate.dependencies)
        self.assertEqual(APPROVER, gate.approver)
        self.assertEqual(
            self.template.required_asset_kinds(9),
            {ref.asset_id for ref in gate.required_assets},
        )
        self.assertEqual(16, len(gate.required_assets))
        self.assertEqual(
            frozenset(CANONICAL_LAUNCH_KINDS),
            {ref.asset_id for ref in gate.required_assets},
        )

    def test_the_gate_pins_the_exact_version_the_reviewed_qa_carries(self):
        gate = self.assemble(package_=package(qa_version=5))

        versions = {ref.asset_id: ref.version for ref in gate.required_assets}
        self.assertEqual(16, len(versions))
        for kind, version in versions.items():
            self.assertEqual(5, version, msg=kind)

    def test_the_assembler_records_the_author_distinct_from_the_approver(self):
        gate = self.assemble(proposed_by=OWNER)

        self.assertEqual(OWNER, gate.proposed_by)
        self.assertNotEqual(gate.approver, gate.proposed_by)

    def test_a_cross_tenant_package_cannot_assemble_a_gate(self):
        with self.assertRaises(TenantBoundaryError):
            self.assemble(package_=other_tenant_package())

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
        self.assertEqual("qa-3f", box.qa.qa_id)


class StageNineGateRecorderTests(unittest.TestCase):
    def setUp(self):
        self.recorder = StageNineGateRecorder()
        self.assembler = StageNineGateAssembler()
        self.template = stage_zero_to_ten_template()

    def seeded_ledger(self) -> GateLedger:
        ledger = GateLedger(self.template)
        seed_through_stage_eight(ledger, self.template)
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
            scope=overrides.pop("scope", SCOPE_NINE),
            checkpoint_evidence=overrides.pop(
                "checkpoint_evidence", "all sixteen stage 9 kinds reviewed"
            ),
            rationale=overrides.pop(
                "rationale", "every critical path check passed and the client authority authorized traffic"
            ),
            assigned_owner=overrides.pop("assigned_owner", OWNER),
            due_on=overrides.pop("due_on", DUE),
            on=overrides.pop("on", ON),
            **overrides,
        )

    def test_records_a_passing_stage_nine_decision_from_the_assembled_gate(self):
        ledger = self.seeded_ledger()

        decision = self.record(self.assembled_gate(), ledger)

        self.assertEqual(9, decision.stage_number)
        self.assertIs(GateDisposition.APPROVED, decision.disposition)
        self.assertEqual("Launch Approved", decision.checkpoint)
        self.assertEqual(frozenset({8}), decision.dependencies)
        self.assertEqual(APPROVER, decision.reviewer)
        self.assertIs(decision, ledger.decision_for(9))
        self.assertTrue(ledger.has_passing_decision(9, on=ON))

    def test_one_approved_exact_version_request_per_required_asset(self):
        ledger = self.seeded_ledger()

        decision = self.record(self.assembled_gate(), ledger)

        self.assertEqual(16, len(decision.asset_approvals))
        for request in decision.asset_approvals:
            self.assertEqual(SCOPE_NINE, request.scope)
            self.assertEqual(APPROVER, request.approver)
            self.assertIn(request.asset, decision.required_assets)
        self.assertEqual(frozenset(), decision.unapproved_assets())

    def test_a_non_stage_nine_gate_cannot_be_recorded(self):
        kinds = self.template.required_asset_kinds(8)
        gate = StageGate.from_template(self.template, 8, {kind: 1 for kind in kinds})
        gate.proposed_by = OWNER
        gate.approver = APPROVER
        ledger = self.seeded_ledger()

        with self.assertRaises(NotStageNineGateError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(9))

    def test_an_approver_without_workspace_authority_cannot_record(self):
        gate = self.assembled_gate()
        gate.approver = "stranger"
        ledger = self.seeded_ledger()

        with self.assertRaises(GateApproverNotAuthorizedError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(9))

    def test_a_gate_without_an_author_cannot_record(self):
        gate = self.assembled_gate(proposed_by=None)
        ledger = self.seeded_ledger()

        with self.assertRaises(GateAuthorRequiredError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(9))

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


class RecordStageNineGateHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = RecordStageNineGateHandler()
        self.template = stage_zero_to_ten_template()

    def ledger(self) -> GateLedger:
        ledger = GateLedger(self.template)
        seed_through_stage_eight(ledger, self.template)
        return ledger

    def command(self, *, workspace_=None, package_=None, stage_run_=None, **overrides):
        values = {
            "template": self.template,
            "workspace": workspace_ or workspace(),
            "package": package_ if package_ is not None else package(),
            "stage_run": stage_run_ if stage_run_ is not None else working_stage_run(),
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE_NINE,
            "checkpoint_evidence": "all sixteen stage 9 kinds reviewed",
            "rationale": "every critical path check passed and the client authority authorized traffic",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        values.update(overrides)
        return RecordStageNineGateCommand(**values)

    def test_records_a_passing_stage_nine_decision_and_closes_the_run(self):
        ledger = self.ledger()
        run = working_stage_run()

        decision = self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        self.assertEqual(9, decision.stage_number)
        self.assertIs(decision, ledger.decision_for(9))
        self.assertTrue(run.is_complete)
        self.assertIs(decision, run.accepted_decision)
        self.assertEqual(ON, run.exited_at)

    def test_verified_progress_counts_stages_zero_through_nine(self):
        ledger = self.ledger()
        run = working_stage_run()

        self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        progress = PipelineProgress.from_ledger(ledger, on=ON)
        self.assertEqual(10, progress.approved_gates)
        self.assertTrue(run.is_complete)

    def test_a_run_for_another_stage_cannot_be_closed(self):
        ledger = self.ledger()

        with self.assertRaises(StageRunNotStageNineError):
            self.handler.handle(
                self.command(stage_run_=working_stage_run(stage_number=8)),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(9))

    def test_a_run_for_another_template_version_cannot_be_closed(self):
        ledger = self.ledger()

        with self.assertRaises(StageRunNotStageNineError):
            self.handler.handle(
                self.command(
                    stage_run_=working_stage_run(template_version="2025.9")
                ),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(9))

    def test_a_not_completable_run_does_not_record_a_decision(self):
        ledger = self.ledger()
        run = StageRun(
            engagement="ws-3f",
            stage_number=9,
            template_version=self.template.version,
            assigned_owner=OWNER,
        )

        with self.assertRaises(StageRunNotCompletableError):
            self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        self.assertIsNone(ledger.decision_for(9))
        self.assertFalse(run.is_complete)

    def test_stage_nine_cannot_pass_while_stage_eight_is_unapproved(self):
        ledger = GateLedger(self.template)
        for stage_number in (0, 1, 2, 3, 4, 5, 6, 7):
            _seed_passing(ledger, self.template, stage_number, on=ON, scope="seed")

        with self.assertRaises(GateDecisionError):
            self.handler.handle(self.command(), ledger=ledger)

        self.assertIsNone(ledger.decision_for(9))

    def test_the_use_case_does_not_mutate_the_workspace_or_package(self):
        root = workspace()
        box = package()
        ledger = self.ledger()

        self.handler.handle(
            self.command(workspace_=root, package_=box), ledger=ledger
        )

        self.assertEqual(2, len(root.authorities))
        self.assertEqual("qa-3f", box.qa.qa_id)


if __name__ == "__main__":
    unittest.main()
