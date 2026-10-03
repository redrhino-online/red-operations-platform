"""Behavioral tests for the stage 2 "Currency Locked" gate path.

Rules under test come from SPEC.md sections 3, 4, 5 and 11 and the reference
model canon (SPEC.md section 12.3 maps stage 2 "Position" to canon files 04, 05
and 06). A stage is complete only when its required assets exist, pass a defined
checkpoint, and receive approval for downstream use; a passing gate "pins the
exact evidence and intended downstream use"; a failed or expired prerequisite
blocks dependent authorization until resolved; a stage gate is approved by the
client-designated authority and an agent cannot confer human approval upon
itself; every output has an owner and a source.

Cycle 71 added the Commercial ``CurrencyPackage`` bridge that projects the four
reviewed stage 2 values onto the ten canonical stage 2 asset kinds as exact
``StageAssetVersion`` evidence, so a canonical stage 2 gate can now be assembled.
This cycle wires the stage 2 "Currency Locked" gate end to end, mirroring the
stage 1 path: a pure Engagement assembler validates the reviewed package with
``GateApproverAuthorityPolicy``, pins the canonical stage 2 gate via
``StageGate.from_assets`` and binds the client-designated approver; a recorder
issues one exact-version approval per kind and writes the durable
``GateDecision``; an application use case chains them and closes the stage 2
``StageRun``. Stage 2 depends on stage 1, so the ledger must already hold a
passing stage 1 decision (and therefore stage 0). The stage 2 checkpoint turns on
the primary currency's internal specificity, which ``PrimaryCurrency`` already
enforces at construction, so unlike stage 1 there is no separate sourced-claim
policy at this gate. These tests never invent a named client approver or a
concrete authority role.
"""

import unittest
from datetime import date

from redops.contexts.commercial.domain.value_objects import (
    CurrencyInventory,
    CurrencyPackage,
    MillionDollarMessage,
    PositioningDecision,
)
from redops.contexts.engagement.application.commands import (
    RecordStageTwoGateCommand,
)
from redops.contexts.engagement.application.handlers import (
    RecordStageTwoGateHandler,
)
from redops.contexts.engagement.domain.assemblies import (
    StageTwoGateAssembler,
    StageTwoGateRecorder,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    GateApproverNotAuthorizedError,
    GateAuthorRequiredError,
    NotStageTwoGateError,
    StageOwnerNotAuthorizedError,
    StageRunNotCompletableError,
    StageRunNotStageTwoError,
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
from redops.contexts.method.domain.value_objects import PrimaryCurrency

ON = date(2026, 10, 3)
DUE = date(2026, 10, 17)
TENANT = "client-3f"
OTHER_TENANT = "client-other"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE_TWO = "stage-3-model"
CORRELATION = "corr-stage-2"


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


def inventory(*, tenant_id: str = TENANT) -> CurrencyInventory:
    return CurrencyInventory(
        inventory_id="currency-inventory-3f",
        tenant_id=tenant_id,
        category="business consulting",
        currencies_to_increase=("leads", "sales", "profit"),
        currencies_to_decrease=("ad spend", "cancellations"),
    )


def positioning(*, tenant_id: str = TENANT) -> PositioningDecision:
    return PositioningDecision(
        decision_id="positioning-3f",
        tenant_id=tenant_id,
        core_problem="unpredictable qualified demand",
        transformation_statement="a predictable pipeline that runs without the owner",
        horizon="90 days",
        qualifications=("runs a service firm with delivery capacity",),
        disqualifications=("no delivery capacity and no budget",),
    )


def primary_currency(*, tenant_id: str = TENANT) -> PrimaryCurrency:
    return PrimaryCurrency(
        tenant_id=tenant_id,
        currency="qualified referrals",
        audience="owner-operators of two to five person service firms",
        current_measure="4 qualified referrals per month",
        desired_measure="12 qualified referrals per month",
        mechanism="referral partner network",
    )


def million_dollar_message(*, tenant_id: str = TENANT) -> MillionDollarMessage:
    return MillionDollarMessage(
        message_id="mdm-3f",
        tenant_id=tenant_id,
        avatar="owner-operators of two to five person service firms",
        currency="qualified referrals",
        metric="12 qualified referrals per month",
        timeline="90 days",
        pain="feast and famine pipeline",
        message=(
            "I help owner-operators of small service firms reach twelve "
            "qualified referrals a month in ninety days without relying on "
            "referral luck, so their pipeline stops deciding their payroll"
        ),
    )


def package(*, tenant_id: str = TENANT, **overrides) -> CurrencyPackage:
    values = {
        "package_id": "currency-3f",
        "tenant_id": tenant_id,
        "inventory": inventory(tenant_id=tenant_id),
        "inventory_version": 1,
        "positioning": positioning(tenant_id=tenant_id),
        "positioning_version": 1,
        "primary_currency": primary_currency(tenant_id=tenant_id),
        "primary_currency_version": 1,
        "million_dollar_message": million_dollar_message(tenant_id=tenant_id),
        "million_dollar_message_version": 1,
    }
    values.update(overrides)
    return CurrencyPackage(**values)


def working_stage_run(stage_number: int = 2, **overrides) -> StageRun:
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


def seed_stage_zero_and_one(ledger: GateLedger, template, *, on: date = ON) -> None:
    """Record passing stage 0 and stage 1 decisions so the stage 2 prerequisite is met."""

    _seed_passing(ledger, template, 0, on=on, scope="seed-stage-0")
    _seed_passing(ledger, template, 1, on=on, scope="seed-stage-1")


class StageTwoGateAssemblerTests(unittest.TestCase):
    def setUp(self):
        self.assembler = StageTwoGateAssembler()
        self.template = stage_zero_to_ten_template()

    def assemble(self, *, workspace_=None, package_=None, approver=APPROVER, **overrides):
        return self.assembler.assemble(
            template=overrides.pop("template", self.template),
            workspace=workspace_ or workspace(),
            package=package_ or package(),
            approver=approver,
            **overrides,
        )

    def test_a_reviewed_currency_package_assembles_the_canonical_stage_two_gate(self):
        gate = self.assemble()

        self.assertEqual(2, gate.stage_number)
        self.assertEqual(self.template.version, gate.template_version)
        self.assertEqual("Currency Locked", gate.checkpoint)
        self.assertEqual(frozenset({1}), gate.dependencies)
        self.assertEqual(APPROVER, gate.approver)
        self.assertEqual(
            self.template.required_asset_kinds(2),
            {ref.asset_id for ref in gate.required_assets},
        )
        self.assertEqual(10, len(gate.required_assets))

    def test_the_gate_pins_the_exact_version_each_reviewed_asset_carries(self):
        gate = self.assemble(
            package_=package(
                inventory_version=2,
                positioning_version=3,
                primary_currency_version=4,
                million_dollar_message_version=5,
            )
        )

        versions = {ref.asset_id: ref.version for ref in gate.required_assets}
        self.assertEqual(2, versions["category"])
        self.assertEqual(2, versions["currency-inventory"])
        self.assertEqual(4, versions["primary-currency"])
        self.assertEqual(4, versions["current-measures"])
        self.assertEqual(4, versions["desired-measures"])
        self.assertEqual(3, versions["horizon"])
        self.assertEqual(3, versions["qualifications"])
        self.assertEqual(3, versions["transformation-statement"])
        self.assertEqual(3, versions["core-problem"])
        self.assertEqual(5, versions["million-dollar-message"])

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
        self.assertEqual("business consulting", box.inventory.category)


class StageTwoGateRecorderTests(unittest.TestCase):
    def setUp(self):
        self.recorder = StageTwoGateRecorder()
        self.assembler = StageTwoGateAssembler()
        self.template = stage_zero_to_ten_template()

    def seeded_ledger(self) -> GateLedger:
        ledger = GateLedger(self.template)
        seed_stage_zero_and_one(ledger, self.template)
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
            scope=overrides.pop("scope", SCOPE_TWO),
            checkpoint_evidence=overrides.pop(
                "checkpoint_evidence", "all ten stage 2 assets reviewed"
            ),
            rationale=overrides.pop("rationale", "currency complete and specific"),
            assigned_owner=overrides.pop("assigned_owner", OWNER),
            due_on=overrides.pop("due_on", DUE),
            on=overrides.pop("on", ON),
            **overrides,
        )

    def test_records_a_passing_stage_two_decision_from_the_assembled_gate(self):
        ledger = self.seeded_ledger()

        decision = self.record(self.assembled_gate(), ledger)

        self.assertEqual(2, decision.stage_number)
        self.assertIs(GateDisposition.APPROVED, decision.disposition)
        self.assertEqual("Currency Locked", decision.checkpoint)
        self.assertEqual(frozenset({1}), decision.dependencies)
        self.assertEqual(APPROVER, decision.reviewer)
        self.assertIs(decision, ledger.decision_for(2))
        self.assertTrue(ledger.has_passing_decision(2, on=ON))

    def test_one_approved_exact_version_request_per_required_asset(self):
        ledger = self.seeded_ledger()

        decision = self.record(self.assembled_gate(), ledger)

        self.assertEqual(10, len(decision.asset_approvals))
        for request in decision.asset_approvals:
            self.assertEqual(SCOPE_TWO, request.scope)
            self.assertEqual(APPROVER, request.approver)
            self.assertIn(request.asset, decision.required_assets)
        self.assertEqual(frozenset(), decision.unapproved_assets())

    def test_a_non_stage_two_gate_cannot_be_recorded(self):
        kinds = self.template.required_asset_kinds(1)
        gate = StageGate.from_template(self.template, 1, {kind: 1 for kind in kinds})
        gate.proposed_by = OWNER
        gate.approver = APPROVER
        ledger = self.seeded_ledger()

        with self.assertRaises(NotStageTwoGateError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(2))

    def test_an_approver_without_workspace_authority_cannot_record(self):
        gate = self.assembled_gate()
        gate.approver = "stranger"
        ledger = self.seeded_ledger()

        with self.assertRaises(GateApproverNotAuthorizedError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(2))

    def test_a_gate_without_an_author_cannot_record(self):
        gate = self.assembled_gate(proposed_by=None)
        ledger = self.seeded_ledger()

        with self.assertRaises(GateAuthorRequiredError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(2))

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


class RecordStageTwoGateHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = RecordStageTwoGateHandler()
        self.template = stage_zero_to_ten_template()

    def ledger(self) -> GateLedger:
        ledger = GateLedger(self.template)
        seed_stage_zero_and_one(ledger, self.template)
        return ledger

    def command(self, *, workspace_=None, package_=None, stage_run_=None, **overrides):
        values = {
            "template": self.template,
            "workspace": workspace_ or workspace(),
            "package": package_ if package_ is not None else package(),
            "stage_run": stage_run_ if stage_run_ is not None else working_stage_run(),
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE_TWO,
            "checkpoint_evidence": "all ten stage 2 assets reviewed",
            "rationale": "currency complete and specific",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        values.update(overrides)
        return RecordStageTwoGateCommand(**values)

    def test_records_a_passing_stage_two_decision_and_closes_the_run(self):
        ledger = self.ledger()
        run = working_stage_run()

        decision = self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        self.assertEqual(2, decision.stage_number)
        self.assertIs(decision, ledger.decision_for(2))
        self.assertTrue(run.is_complete)
        self.assertIs(decision, run.accepted_decision)
        self.assertEqual(ON, run.exited_at)

    def test_verified_progress_counts_stages_zero_one_and_two(self):
        ledger = self.ledger()
        run = working_stage_run()

        self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        progress = PipelineProgress.from_ledger(ledger, on=ON)
        self.assertEqual(3, progress.approved_gates)
        self.assertTrue(run.is_complete)

    def test_a_run_for_another_stage_cannot_be_closed(self):
        ledger = self.ledger()

        with self.assertRaises(StageRunNotStageTwoError):
            self.handler.handle(
                self.command(stage_run_=working_stage_run(stage_number=3)),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(2))

    def test_a_run_for_another_template_version_cannot_be_closed(self):
        ledger = self.ledger()

        with self.assertRaises(StageRunNotStageTwoError):
            self.handler.handle(
                self.command(
                    stage_run_=working_stage_run(template_version="2025.9")
                ),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(2))

    def test_a_not_completable_run_does_not_record_a_decision(self):
        ledger = self.ledger()
        run = StageRun(
            engagement="ws-3f",
            stage_number=2,
            template_version=self.template.version,
            assigned_owner=OWNER,
        )

        with self.assertRaises(StageRunNotCompletableError):
            self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        self.assertIsNone(ledger.decision_for(2))
        self.assertFalse(run.is_complete)

    def test_stage_two_cannot_pass_while_stage_one_is_unapproved(self):
        ledger = GateLedger(self.template)
        _seed_passing(ledger, self.template, 0, on=ON, scope="seed-stage-0")

        with self.assertRaises(GateDecisionError):
            self.handler.handle(self.command(), ledger=ledger)

        self.assertIsNone(ledger.decision_for(2))

    def test_the_use_case_does_not_mutate_the_workspace_or_package(self):
        root = workspace()
        box = package()
        ledger = self.ledger()

        self.handler.handle(
            self.command(workspace_=root, package_=box), ledger=ledger
        )

        self.assertEqual(2, len(root.authorities))
        self.assertEqual("business consulting", box.inventory.category)


if __name__ == "__main__":
    unittest.main()
