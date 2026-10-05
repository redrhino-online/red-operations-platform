"""Behavioral tests for the stage 8 "Funnel Complete" gate path.

Rules under test come from SPEC.md sections 3, 4, 5 and 11 and the reference
model canon (SPEC.md section 12.3 maps stage 8 "Integrate" to canon files 13, 14,
21 and 22). A stage is complete only when its required assets exist, pass a
defined checkpoint, and receive approval for downstream use; a passing gate "pins
the exact evidence and intended downstream use"; the "Funnel Complete" checkpoint
requires "a test prospect completes capture, engagement and conversion handoffs
with reliable records and ownership"; a failed or expired prerequisite blocks
dependent authorization until resolved; a stage gate is approved by the
client-designated authority and an agent cannot confer human approval upon
itself; every output has an owner and a source.

Cycle 83 added the Execution ``FunnelIntegrationPackage`` bridge that projects the
reviewed stage 8 ``FunnelIntegration`` onto the fourteen canonical stage 8 asset
kinds as exact ``StageAssetVersion`` evidence, so a canonical stage 8 gate can now
be assembled. This cycle wires the stage 8 "Funnel Complete" gate end to end,
mirroring the stage 7 path: a pure Engagement assembler validates the reviewed
package against the workspace tenant and binds the client-designated approver; a
recorder issues one exact-version approval per kind and writes the durable
``GateDecision``; an application use case chains them and closes the stage 8
``StageRun``. Stage 8 depends on stage 7, so the ledger must already hold passing
stage 0 through stage 7 decisions. These tests never invent a named client
approver or a concrete authority role.
"""

import unittest
from datetime import date

from redops.contexts.engagement.application.commands import (
    RecordStageEightGateCommand,
)
from redops.contexts.engagement.application.handlers import (
    RecordStageEightGateHandler,
)
from redops.contexts.engagement.domain.assemblies import (
    StageEightGateAssembler,
    StageEightGateRecorder,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    GateApproverNotAuthorizedError,
    GateAuthorRequiredError,
    NotStageEightGateError,
    StageOwnerNotAuthorizedError,
    StageRunNotCompletableError,
    StageRunNotStageEightError,
    TenantBoundaryError,
)
from redops.contexts.engagement.domain.value_objects import ClientAuthority
from redops.contexts.execution.domain.entities import FunnelIntegration
from redops.contexts.execution.domain.value_objects import (
    CANONICAL_FUNNEL_KINDS,
    HANDOFF_ORDER,
    ProspectPathDryRun,
    FunnelIntegrationPackage,
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

from ..commercial.fixtures import (
    approved_method,
    campaign_message,
    delivery_specification,
    offer_version,
)
from ..execution.fixtures import (
    TENANT,
    complete_funnel,
    funnel_assets,
    handoff,
    swimlane_moves,
    swimlanes_plan,
)
from ..method.fixtures import signature_solution
from ..production.fixtures import (
    TODAY,
    USE,
    authority_amplifier,
    known_claim,
    visual_package,
)

ON = date(2026, 10, 3)
DUE = date(2026, 10, 17)
OTHER_TENANT = "client-other"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE_EIGHT = "stage-9-launch-qa"
CORRELATION = "corr-stage-8"


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


def other_tenant_package(**overrides) -> FunnelIntegrationPackage:
    values = {
        "package_id": "funnel-package-other",
        "tenant_id": OTHER_TENANT,
        "funnel": other_tenant_complete_funnel(),
        "funnel_version": 1,
        "swimlanes": swimlanes_plan(
            funnel=other_tenant_complete_funnel(),
            tenant_id=OTHER_TENANT,
            moves=swimlane_moves(tenant_id=OTHER_TENANT),
        ),
        "swimlanes_version": 1,
    }
    values.update(overrides)
    return FunnelIntegrationPackage(**values)


def working_stage_run(stage_number: int = 8, **overrides) -> StageRun:
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


def seed_through_stage_seven(ledger: GateLedger, template, *, on: date = ON) -> None:
    """Record passing stages 0 through 7 so the stage 8 prerequisite is met."""

    for stage_number in (0, 1, 2, 3, 4, 5, 6, 7):
        _seed_passing(ledger, template, stage_number, on=on, scope="seed")


class StageEightGateAssemblerTests(unittest.TestCase):
    def setUp(self):
        self.assembler = StageEightGateAssembler()
        self.template = stage_zero_to_ten_template()

    def assemble(self, *, workspace_=None, package_=None, approver=APPROVER, **overrides):
        return self.assembler.assemble(
            template=overrides.pop("template", self.template),
            workspace=workspace_ or workspace(),
            package=package_ or package(),
            approver=approver,
            **overrides,
        )

    def test_a_reviewed_funnel_package_assembles_the_canonical_stage_eight_gate(self):
        gate = self.assemble()

        self.assertEqual(8, gate.stage_number)
        self.assertEqual(self.template.version, gate.template_version)
        self.assertEqual("Funnel Complete", gate.checkpoint)
        self.assertEqual(frozenset({7}), gate.dependencies)
        self.assertEqual(APPROVER, gate.approver)
        self.assertEqual(
            self.template.required_asset_kinds(8),
            {ref.asset_id for ref in gate.required_assets},
        )
        self.assertEqual(14, len(gate.required_assets))
        self.assertEqual(
            frozenset(CANONICAL_FUNNEL_KINDS),
            {ref.asset_id for ref in gate.required_assets},
        )

    def test_the_gate_pins_the_exact_version_the_reviewed_funnel_carries(self):
        gate = self.assemble(
            package_=package(funnel_version=5, swimlanes_version=2)
        )

        versions = {ref.asset_id: ref.version for ref in gate.required_assets}
        self.assertEqual(14, len(versions))
        for kind, version in versions.items():
            expected = 2 if kind == "swimlanes-plan" else 5
            self.assertEqual(expected, version, msg=kind)

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
        self.assertEqual("funnel-3f", box.funnel.integration_id)


class StageEightGateRecorderTests(unittest.TestCase):
    def setUp(self):
        self.recorder = StageEightGateRecorder()
        self.assembler = StageEightGateAssembler()
        self.template = stage_zero_to_ten_template()

    def seeded_ledger(self) -> GateLedger:
        ledger = GateLedger(self.template)
        seed_through_stage_seven(ledger, self.template)
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
            scope=overrides.pop("scope", SCOPE_EIGHT),
            checkpoint_evidence=overrides.pop(
                "checkpoint_evidence", "all fourteen stage 8 kinds reviewed"
            ),
            rationale=overrides.pop(
                "rationale", "the prospect path completed capture, engagement and conversion handoffs"
            ),
            assigned_owner=overrides.pop("assigned_owner", OWNER),
            due_on=overrides.pop("due_on", DUE),
            on=overrides.pop("on", ON),
            **overrides,
        )

    def test_records_a_passing_stage_eight_decision_from_the_assembled_gate(self):
        ledger = self.seeded_ledger()

        decision = self.record(self.assembled_gate(), ledger)

        self.assertEqual(8, decision.stage_number)
        self.assertIs(GateDisposition.APPROVED, decision.disposition)
        self.assertEqual("Funnel Complete", decision.checkpoint)
        self.assertEqual(frozenset({7}), decision.dependencies)
        self.assertEqual(APPROVER, decision.reviewer)
        self.assertIs(decision, ledger.decision_for(8))
        self.assertTrue(ledger.has_passing_decision(8, on=ON))

    def test_one_approved_exact_version_request_per_required_asset(self):
        ledger = self.seeded_ledger()

        decision = self.record(self.assembled_gate(), ledger)

        self.assertEqual(14, len(decision.asset_approvals))
        for request in decision.asset_approvals:
            self.assertEqual(SCOPE_EIGHT, request.scope)
            self.assertEqual(APPROVER, request.approver)
            self.assertIn(request.asset, decision.required_assets)
        self.assertEqual(frozenset(), decision.unapproved_assets())

    def test_a_non_stage_eight_gate_cannot_be_recorded(self):
        kinds = self.template.required_asset_kinds(7)
        gate = StageGate.from_template(self.template, 7, {kind: 1 for kind in kinds})
        gate.proposed_by = OWNER
        gate.approver = APPROVER
        ledger = self.seeded_ledger()

        with self.assertRaises(NotStageEightGateError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(8))

    def test_an_approver_without_workspace_authority_cannot_record(self):
        gate = self.assembled_gate()
        gate.approver = "stranger"
        ledger = self.seeded_ledger()

        with self.assertRaises(GateApproverNotAuthorizedError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(8))

    def test_a_gate_without_an_author_cannot_record(self):
        gate = self.assembled_gate(proposed_by=None)
        ledger = self.seeded_ledger()

        with self.assertRaises(GateAuthorRequiredError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(8))

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


class RecordStageEightGateHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = RecordStageEightGateHandler()
        self.template = stage_zero_to_ten_template()

    def ledger(self) -> GateLedger:
        ledger = GateLedger(self.template)
        seed_through_stage_seven(ledger, self.template)
        return ledger

    def command(self, *, workspace_=None, package_=None, stage_run_=None, **overrides):
        values = {
            "template": self.template,
            "workspace": workspace_ or workspace(),
            "package": package_ if package_ is not None else package(),
            "stage_run": stage_run_ if stage_run_ is not None else working_stage_run(),
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE_EIGHT,
            "checkpoint_evidence": "all fourteen stage 8 kinds reviewed",
            "rationale": "the prospect path completed capture, engagement and conversion handoffs",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        values.update(overrides)
        return RecordStageEightGateCommand(**values)

    def test_records_a_passing_stage_eight_decision_and_closes_the_run(self):
        ledger = self.ledger()
        run = working_stage_run()

        decision = self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        self.assertEqual(8, decision.stage_number)
        self.assertIs(decision, ledger.decision_for(8))
        self.assertTrue(run.is_complete)
        self.assertIs(decision, run.accepted_decision)
        self.assertEqual(ON, run.exited_at)

    def test_verified_progress_counts_stages_zero_through_eight(self):
        ledger = self.ledger()
        run = working_stage_run()

        self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        progress = PipelineProgress.from_ledger(ledger, on=ON)
        self.assertEqual(9, progress.approved_gates)
        self.assertTrue(run.is_complete)

    def test_a_run_for_another_stage_cannot_be_closed(self):
        ledger = self.ledger()

        with self.assertRaises(StageRunNotStageEightError):
            self.handler.handle(
                self.command(stage_run_=working_stage_run(stage_number=9)),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(8))

    def test_a_run_for_another_template_version_cannot_be_closed(self):
        ledger = self.ledger()

        with self.assertRaises(StageRunNotStageEightError):
            self.handler.handle(
                self.command(
                    stage_run_=working_stage_run(template_version="2025.9")
                ),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(8))

    def test_a_not_completable_run_does_not_record_a_decision(self):
        ledger = self.ledger()
        run = StageRun(
            engagement="ws-3f",
            stage_number=8,
            template_version=self.template.version,
            assigned_owner=OWNER,
        )

        with self.assertRaises(StageRunNotCompletableError):
            self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        self.assertIsNone(ledger.decision_for(8))
        self.assertFalse(run.is_complete)

    def test_stage_eight_cannot_pass_while_stage_seven_is_unapproved(self):
        ledger = GateLedger(self.template)
        for stage_number in (0, 1, 2, 3, 4, 5, 6):
            _seed_passing(ledger, self.template, stage_number, on=ON, scope="seed")

        with self.assertRaises(GateDecisionError):
            self.handler.handle(self.command(), ledger=ledger)

        self.assertIsNone(ledger.decision_for(8))

    def test_the_use_case_does_not_mutate_the_workspace_or_package(self):
        root = workspace()
        box = package()
        ledger = self.ledger()

        self.handler.handle(
            self.command(workspace_=root, package_=box), ledger=ledger
        )

        self.assertEqual(2, len(root.authorities))
        self.assertEqual("funnel-3f", box.funnel.integration_id)


if __name__ == "__main__":
    unittest.main()
