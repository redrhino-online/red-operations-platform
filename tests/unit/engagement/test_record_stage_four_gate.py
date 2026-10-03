"""Behavioral tests for the stage 4 "IP Architecture Locked" gate path.

Rules under test come from SPEC.md sections 3, 4, 5 and 11 and the reference
model canon (SPEC.md section 12.3 maps stage 4 "Package IP" to canon files 09 and
10). A stage is complete only when its required assets exist, pass a defined
checkpoint, and receive approval for downstream use; a passing gate "pins the
exact evidence and intended downstream use"; a failed or expired prerequisite
blocks dependent authorization until resolved; a stage gate is approved by the
client-designated authority and an agent cannot confer human approval upon
itself; every output has an owner and a source.

Cycle 75 added the Commercial ``SignaturePackage`` bridge that projects the single
reviewed stage 4 ``SignatureSolution`` onto the twelve canonical stage 4 asset
kinds as exact ``StageAssetVersion`` evidence, so a canonical stage 4 gate can now
be assembled. This cycle wires the stage 4 "IP Architecture Locked" gate end to
end, mirroring the stage 3 path: a pure Engagement assembler validates the
reviewed package against the workspace tenant and binds the client-designated
approver; a recorder issues one exact-version approval per kind and writes the
durable ``GateDecision``; an application use case chains them and closes the stage
4 ``StageRun``. Stage 4 depends on stage 3, so the ledger must already hold
passing stage 0 through stage 3 decisions. The stage 4 checkpoint turns on the
coherence and continuity of the reviewed transformation, which ``SignatureSolution``
already enforces at construction, so unlike stage 1 there is no separate
sourced-claim policy at this gate. These tests never invent a named client
approver or a concrete authority role.
"""

import unittest
from datetime import date

from redops.contexts.commercial.domain.value_objects import SignaturePackage
from redops.contexts.engagement.application.commands import (
    RecordStageFourGateCommand,
)
from redops.contexts.engagement.application.handlers import (
    RecordStageFourGateHandler,
)
from redops.contexts.engagement.domain.assemblies import (
    StageFourGateAssembler,
    StageFourGateRecorder,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    GateApproverNotAuthorizedError,
    GateAuthorRequiredError,
    NotStageFourGateError,
    StageOwnerNotAuthorizedError,
    StageRunNotCompletableError,
    StageRunNotStageFourError,
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
from redops.contexts.method.domain.entities import SignatureSolution
from redops.contexts.method.domain.transformations import (
    ThirteenTransformations,
    Transformation,
    TransformationScope,
)
from redops.contexts.method.domain.value_objects import (
    SignatureStep,
    TransformationPhase,
)

ON = date(2026, 10, 3)
DUE = date(2026, 10, 17)
TENANT = "client-3f"
OTHER_TENANT = "client-other"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE_FOUR = "stage-5-offer"
CORRELATION = "corr-stage-4"


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


def step(
    step_id: str,
    name: str,
    starting_state: str,
    final_state: str,
    tenant_id: str = TENANT,
) -> SignatureStep:
    return SignatureStep(
        step_id=step_id,
        tenant_id=tenant_id,
        name=name,
        starting_state=starting_state,
        final_state=final_state,
        inputs=(f"{name} inputs",),
        actions=(f"{name} actions",),
        outputs=(f"{name} outputs",),
    )


def nine_step_phases(tenant_id: str = TENANT) -> tuple[TransformationPhase, ...]:
    return (
        TransformationPhase(
            phase_id="phase-1",
            tenant_id=tenant_id,
            name="Diagnose and Position",
            steps=(
                step("step-1", "Diagnose", "chaotic", "diagnosed", tenant_id),
                step("step-2", "Position", "diagnosed", "positioned", tenant_id),
                step("step-3", "Model", "positioned", "modeled", tenant_id),
            ),
        ),
        TransformationPhase(
            phase_id="phase-2",
            tenant_id=tenant_id,
            name="Package and Productize",
            steps=(
                step("step-4", "Package IP", "modeled", "packaged", tenant_id),
                step("step-5", "Productize", "packaged", "productized", tenant_id),
                step("step-6", "Message", "productized", "messaged", tenant_id),
            ),
        ),
        TransformationPhase(
            phase_id="phase-3",
            tenant_id=tenant_id,
            name="Produce and Launch",
            steps=(
                step("step-7", "Produce", "messaged", "produced", tenant_id),
                step("step-8", "Integrate", "produced", "integrated", tenant_id),
                step("step-9", "Launch", "integrated", "launched", tenant_id),
            ),
        ),
    )


def solution(tenant_id: str = TENANT) -> SignatureSolution:
    return SignatureSolution(
        solution_id="solution-3f",
        tenant_id=tenant_id,
        transformation_map="from chaotic delivery to a launched campaign",
        process_inventory=("diagnose", "position", "model", "package"),
        phases=nine_step_phases(tenant_id),
        starting_state="chaotic",
        final_state="launched",
        narrative=(
            "the client moves from unpredictable work to a repeatable growth "
            "system"
        ),
        visual="asset://transformations/3f-map.png",
    )


def transformations(sol: SignatureSolution) -> ThirteenTransformations:
    return ThirteenTransformations(
        transformations_id="transformations-3f",
        tenant_id=sol.tenant_id,
        million_dollar_message="from chaotic delivery to a launched campaign",
        solution=sol,
        overall=Transformation(
            transformation_id="transformations-3f-overall",
            tenant_id=sol.tenant_id,
            scope=TransformationScope.OVERALL,
            scope_id=sol.solution_id,
            title="from chaotic delivery to a launched campaign",
            from_state=sol.starting_state,
            to_state=sol.final_state,
        ),
        phase_transformations=tuple(
            Transformation(
                transformation_id=f"transformations-3f-{phase.phase_id}",
                tenant_id=sol.tenant_id,
                scope=TransformationScope.PHASE,
                scope_id=phase.phase_id,
                title=phase.name,
                from_state=phase.steps[0].starting_state,
                to_state=phase.steps[-1].final_state,
            )
            for phase in sol.phases
        ),
        step_transformations=tuple(
            Transformation(
                transformation_id=f"transformations-3f-{step.step_id}",
                tenant_id=sol.tenant_id,
                scope=TransformationScope.STEP,
                scope_id=step.step_id,
                title=step.name,
                from_state=step.starting_state,
                to_state=step.final_state,
            )
            for step in sol.steps
        ),
    )


def package(*, tenant_id: str = TENANT, **overrides) -> SignaturePackage:
    sol = overrides.get("solution", solution(tenant_id))
    values = {
        "package_id": "signature-3f",
        "tenant_id": tenant_id,
        "solution": sol,
        "solution_version": 1,
        "transformations": transformations(sol),
        "transformations_version": 1,
    }
    values.update(overrides)
    return SignaturePackage(**values)


def working_stage_run(stage_number: int = 4, **overrides) -> StageRun:
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


def seed_through_stage_three(ledger: GateLedger, template, *, on: date = ON) -> None:
    """Record passing stages 0 through 3 so the stage 4 prerequisite is met."""

    for stage_number in (0, 1, 2, 3):
        _seed_passing(ledger, template, stage_number, on=on, scope="seed")


class StageFourGateAssemblerTests(unittest.TestCase):
    def setUp(self):
        self.assembler = StageFourGateAssembler()
        self.template = stage_zero_to_ten_template()

    def assemble(self, *, workspace_=None, package_=None, approver=APPROVER, **overrides):
        return self.assembler.assemble(
            template=overrides.pop("template", self.template),
            workspace=workspace_ or workspace(),
            package=package_ or package(),
            approver=approver,
            **overrides,
        )

    def test_a_reviewed_signature_package_assembles_the_canonical_stage_four_gate(self):
        gate = self.assemble()

        self.assertEqual(4, gate.stage_number)
        self.assertEqual(self.template.version, gate.template_version)
        self.assertEqual("IP Architecture Locked", gate.checkpoint)
        self.assertEqual(frozenset({3}), gate.dependencies)
        self.assertEqual(APPROVER, gate.approver)
        self.assertEqual(
            self.template.required_asset_kinds(4),
            {ref.asset_id for ref in gate.required_assets},
        )
        self.assertEqual(13, len(gate.required_assets))

    def test_the_gate_pins_the_exact_version_the_reviewed_solution_carries(self):
        gate = self.assemble(
            package_=package(solution_version=5, transformations_version=5)
        )

        versions = {ref.asset_id: ref.version for ref in gate.required_assets}
        self.assertEqual(13, len(versions))
        for kind, version in versions.items():
            self.assertEqual(5, version, msg=kind)

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
        self.assertEqual("solution-3f", box.solution.solution_id)


class StageFourGateRecorderTests(unittest.TestCase):
    def setUp(self):
        self.recorder = StageFourGateRecorder()
        self.assembler = StageFourGateAssembler()
        self.template = stage_zero_to_ten_template()

    def seeded_ledger(self) -> GateLedger:
        ledger = GateLedger(self.template)
        seed_through_stage_three(ledger, self.template)
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
            scope=overrides.pop("scope", SCOPE_FOUR),
            checkpoint_evidence=overrides.pop(
                "checkpoint_evidence", "all twelve stage 4 kinds reviewed"
            ),
            rationale=overrides.pop("rationale", "transformation is coherent"),
            assigned_owner=overrides.pop("assigned_owner", OWNER),
            due_on=overrides.pop("due_on", DUE),
            on=overrides.pop("on", ON),
            **overrides,
        )

    def test_records_a_passing_stage_four_decision_from_the_assembled_gate(self):
        ledger = self.seeded_ledger()

        decision = self.record(self.assembled_gate(), ledger)

        self.assertEqual(4, decision.stage_number)
        self.assertIs(GateDisposition.APPROVED, decision.disposition)
        self.assertEqual("IP Architecture Locked", decision.checkpoint)
        self.assertEqual(frozenset({3}), decision.dependencies)
        self.assertEqual(APPROVER, decision.reviewer)
        self.assertIs(decision, ledger.decision_for(4))
        self.assertTrue(ledger.has_passing_decision(4, on=ON))

    def test_one_approved_exact_version_request_per_required_asset(self):
        ledger = self.seeded_ledger()

        decision = self.record(self.assembled_gate(), ledger)

        self.assertEqual(13, len(decision.asset_approvals))
        for request in decision.asset_approvals:
            self.assertEqual(SCOPE_FOUR, request.scope)
            self.assertEqual(APPROVER, request.approver)
            self.assertIn(request.asset, decision.required_assets)
        self.assertEqual(frozenset(), decision.unapproved_assets())

    def test_a_non_stage_four_gate_cannot_be_recorded(self):
        kinds = self.template.required_asset_kinds(3)
        gate = StageGate.from_template(self.template, 3, {kind: 1 for kind in kinds})
        gate.proposed_by = OWNER
        gate.approver = APPROVER
        ledger = self.seeded_ledger()

        with self.assertRaises(NotStageFourGateError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(4))

    def test_an_approver_without_workspace_authority_cannot_record(self):
        gate = self.assembled_gate()
        gate.approver = "stranger"
        ledger = self.seeded_ledger()

        with self.assertRaises(GateApproverNotAuthorizedError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(4))

    def test_a_gate_without_an_author_cannot_record(self):
        gate = self.assembled_gate(proposed_by=None)
        ledger = self.seeded_ledger()

        with self.assertRaises(GateAuthorRequiredError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(4))

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


class RecordStageFourGateHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = RecordStageFourGateHandler()
        self.template = stage_zero_to_ten_template()

    def ledger(self) -> GateLedger:
        ledger = GateLedger(self.template)
        seed_through_stage_three(ledger, self.template)
        return ledger

    def command(self, *, workspace_=None, package_=None, stage_run_=None, **overrides):
        values = {
            "template": self.template,
            "workspace": workspace_ or workspace(),
            "package": package_ if package_ is not None else package(),
            "stage_run": stage_run_ if stage_run_ is not None else working_stage_run(),
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE_FOUR,
            "checkpoint_evidence": "all twelve stage 4 kinds reviewed",
            "rationale": "transformation is coherent",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        values.update(overrides)
        return RecordStageFourGateCommand(**values)

    def test_records_a_passing_stage_four_decision_and_closes_the_run(self):
        ledger = self.ledger()
        run = working_stage_run()

        decision = self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        self.assertEqual(4, decision.stage_number)
        self.assertIs(decision, ledger.decision_for(4))
        self.assertTrue(run.is_complete)
        self.assertIs(decision, run.accepted_decision)
        self.assertEqual(ON, run.exited_at)

    def test_verified_progress_counts_stages_zero_through_four(self):
        ledger = self.ledger()
        run = working_stage_run()

        self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        progress = PipelineProgress.from_ledger(ledger, on=ON)
        self.assertEqual(5, progress.approved_gates)
        self.assertTrue(run.is_complete)

    def test_a_run_for_another_stage_cannot_be_closed(self):
        ledger = self.ledger()

        with self.assertRaises(StageRunNotStageFourError):
            self.handler.handle(
                self.command(stage_run_=working_stage_run(stage_number=5)),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(4))

    def test_a_run_for_another_template_version_cannot_be_closed(self):
        ledger = self.ledger()

        with self.assertRaises(StageRunNotStageFourError):
            self.handler.handle(
                self.command(
                    stage_run_=working_stage_run(template_version="2025.9")
                ),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(4))

    def test_a_not_completable_run_does_not_record_a_decision(self):
        ledger = self.ledger()
        run = StageRun(
            engagement="ws-3f",
            stage_number=4,
            template_version=self.template.version,
            assigned_owner=OWNER,
        )

        with self.assertRaises(StageRunNotCompletableError):
            self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        self.assertIsNone(ledger.decision_for(4))
        self.assertFalse(run.is_complete)

    def test_stage_four_cannot_pass_while_stage_three_is_unapproved(self):
        ledger = GateLedger(self.template)
        _seed_passing(ledger, self.template, 0, on=ON, scope="seed-stage-0")
        _seed_passing(ledger, self.template, 1, on=ON, scope="seed-stage-1")
        _seed_passing(ledger, self.template, 2, on=ON, scope="seed-stage-2")

        with self.assertRaises(GateDecisionError):
            self.handler.handle(self.command(), ledger=ledger)

        self.assertIsNone(ledger.decision_for(4))

    def test_the_use_case_does_not_mutate_the_workspace_or_package(self):
        root = workspace()
        box = package()
        ledger = self.ledger()

        self.handler.handle(
            self.command(workspace_=root, package_=box), ledger=ledger
        )

        self.assertEqual(2, len(root.authorities))
        self.assertEqual("solution-3f", box.solution.solution_id)


if __name__ == "__main__":
    unittest.main()
