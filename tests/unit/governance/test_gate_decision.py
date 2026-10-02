"""Behavioral tests for the GateDecision aggregate (pure domain, Governance).

Rules under test come from SPEC.md sections 3, 4 and 11:
- A GateDecision records the stage, the pinned required asset versions, the
  checkpoint evidence, the reviewer, the intended downstream scope and the
  disposition.
- Passing a gate pins the exact evidence and intended downstream use.
- A non-passing disposition never authorizes downstream work.
- A waiver is a scoped human decision with a named risk owner; it never makes an
  absent asset appear present.
- An approval is recorded only for a gate that is actually approvable, so a
  failing or unsafe gate cannot be coerced into approval.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
    StageGate,
)
from redops.contexts.governance.domain.errors import GateDecisionError
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateDisposition,
    GateState,
    Waiver,
)

TODAY = date(2026, 10, 2)
DATE_DUE = date(2026, 10, 16)
SCRIPT_V1 = AssetVersionRef("authority-amplifier-script", 1)
VIDEO_V1 = AssetVersionRef("authority-amplifier-video", 1)
TEMPLATE = stage_zero_to_ten_template("2026.1")


def asset_approvals(assets, scope):
    for asset in assets:
        request = ApprovalRequest(
            asset=asset,
            scope=scope,
            requested_by="specialist-1",
            approver="client-approver-1",
        )
        request.approve(actor="client-approver-1", on=TODAY)
        yield request


def approvable_gate(evidenced: bool = True, **overrides) -> StageGate:
    versions = {kind: 1 for kind in TEMPLATE.required_asset_kinds(7)}
    gate = StageGate.from_template(TEMPLATE, 7, versions)
    gate.state = GateState.APPROVED
    gate.proposed_by = "specialist-1"
    gate.approver = "client-approver-1"
    if evidenced:
        for request in asset_approvals(gate.required_assets, "stage-8-funnel-integration"):
            gate.record_asset_approval(request)
    for name, value in overrides.items():
        setattr(gate, name, value)
    return gate


def passing_decision_for(stage_number: int) -> GateDecision:
    assets = frozenset(
        AssetVersionRef(kind, 1)
        for kind in TEMPLATE.required_asset_kinds(stage_number)
    )
    scope = f"stage-{stage_number + 1}-downstream"
    return GateDecision(
        stage_number=stage_number,
        template_version=TEMPLATE.version,
        required_assets=assets,
        checkpoint=TEMPLATE.definition_for(stage_number).checkpoint,
        checkpoint_evidence=f"stage {stage_number} rubric passed",
        reviewer="client-approver-1",
        scope=scope,
        disposition=GateDisposition.APPROVED,
        rationale="reviewed against the checkpoint",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=DATE_DUE,
        asset_approvals=tuple(asset_approvals(assets, scope)),
    )


def ledger_through(stage_number: int) -> GateLedger:
    """Record passing decisions for stages 0..stage_number-1, in order."""
    ledger = GateLedger(TEMPLATE)
    for stage in range(stage_number):
        ledger.record(passing_decision_for(stage))
    return ledger


def passing_decision(**overrides) -> GateDecision:
    values = {
        "stage_number": 7,
        "template_version": "2026.1",
        "required_assets": frozenset({SCRIPT_V1, VIDEO_V1}),
        "checkpoint": "Authority Amplifier Approved",
        "checkpoint_evidence": "authority-amplifier-approved-rubric passed",
        "reviewer": "client-approver-1",
        "scope": "stage-8-funnel-integration",
        "disposition": GateDisposition.APPROVED,
        "rationale": "script and final creative reviewed with the client",
        "decided_on": TODAY,
        "assigned_owner": "production-manager",
        "due_on": DATE_DUE,
        "next_action": "release stage 8 work",
    }
    values.update(overrides)
    values.setdefault(
        "asset_approvals",
        tuple(asset_approvals(values["required_assets"], values["scope"]))
        if values["scope"] and values["required_assets"]
        else (),
    )
    return GateDecision(**values)


class GateDecisionRecordTests(unittest.TestCase):
    def test_passing_decision_pins_exact_assets_scope_and_reviewer(self):
        decision = passing_decision()

        self.assertEqual(7, decision.stage_number)
        self.assertEqual("2026.1", decision.template_version)
        self.assertEqual(frozenset({SCRIPT_V1, VIDEO_V1}), decision.required_assets)
        self.assertEqual("stage-8-funnel-integration", decision.scope)
        self.assertEqual("client-approver-1", decision.reviewer)
        self.assertIs(GateDisposition.APPROVED, decision.disposition)

    def test_passing_decision_authorizes_downstream_and_records_why(self):
        decision = passing_decision()

        self.assertTrue(decision.is_passing)
        self.assertTrue(decision.authorizes_downstream())
        self.assertEqual("release stage 8 work", decision.next_action)
        self.assertTrue(decision.rationale)

    def test_gate_decision_is_immutable(self):
        decision = passing_decision()

        with self.assertRaises(FrozenInstanceError):
            decision.disposition = GateDisposition.BLOCKED


class GateDecisionAccountabilityTests(unittest.TestCase):
    """SPEC.md section 4 gate record: for every stage persist the assigned work
    owner and due date, so the production view can answer who is accountable and
    when the next approval is due. A decision that omits either is rejected
    rather than silently recorded as complete."""

    def test_decision_records_the_assigned_owner_and_due_date(self):
        decision = passing_decision()

        self.assertEqual("production-manager", decision.assigned_owner)
        self.assertEqual(DATE_DUE, decision.due_on)

    def test_decision_requires_an_assigned_work_owner(self):
        for override in ({"assigned_owner": ""}, {"assigned_owner": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(GateDecisionError):
                    passing_decision(**override)

    def test_decision_requires_a_due_date(self):
        with self.assertRaises(GateDecisionError):
            passing_decision(due_on=None)

    def test_factory_records_the_assigned_owner_and_due_date(self):
        gate = approvable_gate()

        decision = GateDecision.from_gate(
            gate,
            ledger=ledger_through(7),
            reviewer="client-approver-1",
            scope="stage-8-funnel-integration",
            checkpoint_evidence="rubric passed",
            disposition=GateDisposition.APPROVED,
            rationale="client approved the exact script and creative",
            on=TODAY,
            assigned_owner="production-manager",
            due_on=DATE_DUE,
        )

        self.assertEqual("production-manager", decision.assigned_owner)
        self.assertEqual(DATE_DUE, decision.due_on)


class GateDecisionInvariantTests(unittest.TestCase):
    def test_passing_decision_requires_the_intended_downstream_scope(self):
        with self.assertRaises(GateDecisionError):
            passing_decision(scope="")

    def test_passing_decision_requires_checkpoint_evidence(self):
        with self.assertRaises(GateDecisionError):
            passing_decision(checkpoint_evidence="")

    def test_passing_decision_requires_pinned_assets(self):
        with self.assertRaises(GateDecisionError):
            passing_decision(required_assets=frozenset())

    def test_passing_decision_requires_a_reviewer(self):
        with self.assertRaises(GateDecisionError):
            passing_decision(reviewer="")

    def test_non_passing_disposition_never_authorizes_downstream(self):
        for disposition in (
            GateDisposition.CHANGES_REQUIRED,
            GateDisposition.BLOCKED,
            GateDisposition.SUPERSEDED,
        ):
            decision = passing_decision(disposition=disposition)
            self.assertFalse(decision.is_passing)
            self.assertFalse(decision.authorizes_downstream())

    def test_waived_decision_requires_a_risk_owner(self):
        with self.assertRaises(GateDecisionError):
            passing_decision(disposition=GateDisposition.WAIVED)

    def test_waived_decision_never_authorizes_downstream(self):
        waiver = Waiver(
            reason="video delayed by vendor",
            risk_owner="production-manager",
            review_trigger="vendor delivery",
            downstream_effects=frozenset({"stage-8-funnel-integration"}),
        )
        decision = passing_decision(
            disposition=GateDisposition.WAIVED,
            scope="stage-8-funnel-integration",
            waiver=waiver,
        )

        self.assertFalse(decision.is_passing)
        self.assertFalse(decision.authorizes_downstream())


class WaiverScopeTests(unittest.TestCase):
    """SPEC.md section 4: a waiver is a scoped human decision with a reason, risk
    owner, expiry or review trigger, and downstream effects. A waiver without a
    recorded impact surface is a blanket bypass and must be refused, so a waiver
    cannot silently release unrelated dependent work."""

    def scoped_waiver(self, **overrides) -> Waiver:
        values = {
            "reason": "video delayed by vendor",
            "risk_owner": "production-manager",
            "review_trigger": "vendor delivery",
            "downstream_effects": frozenset({"stage-8-funnel-integration"}),
        }
        values.update(overrides)
        return Waiver(**values)

    def test_waiver_records_the_downstream_effects_it_is_scoped_to(self):
        waiver = self.scoped_waiver()

        self.assertEqual(
            frozenset({"stage-8-funnel-integration"}),
            waiver.downstream_effects,
        )

    def test_waiver_requires_at_least_one_downstream_effect(self):
        with self.assertRaises(ValueError):
            self.scoped_waiver(downstream_effects=frozenset())

    def test_waiver_rejects_a_blank_downstream_effect(self):
        with self.assertRaises(ValueError):
            self.scoped_waiver(downstream_effects=frozenset({"   "}))

    def test_waived_decision_preserves_the_scoped_effects(self):
        waiver = self.scoped_waiver()

        decision = passing_decision(
            disposition=GateDisposition.WAIVED,
            scope="stage-8-funnel-integration",
            waiver=waiver,
        )

        self.assertIs(waiver, decision.waiver)
        self.assertEqual(
            frozenset({"stage-8-funnel-integration"}),
            decision.waiver.downstream_effects,
        )


class WaiverDecisionScopeTests(unittest.TestCase):
    """SPEC.md section 4: a waiver is a *scoped* human decision. A waived gate
    decision must name the intended downstream scope it waives for, and the
    waiver cannot claim a downstream effect broader than that scope, otherwise it
    would release dependent work the gate never decided to release."""

    def bounded_waiver(self, effects, **overrides) -> Waiver:
        values = {
            "reason": "video delayed by vendor",
            "risk_owner": "production-manager",
            "review_trigger": "vendor delivery",
            "downstream_effects": frozenset(effects),
        }
        values.update(overrides)
        return Waiver(**values)

    def test_waived_decision_requires_an_intended_downstream_scope(self):
        waiver = self.bounded_waiver({"stage-8-funnel-integration"})

        for scope in ("", "   "):
            with self.subTest(scope=scope):
                with self.assertRaises(GateDecisionError):
                    passing_decision(
                        disposition=GateDisposition.WAIVED,
                        scope=scope,
                        required_assets=frozenset(),
                        waiver=waiver,
                    )

    def test_waiver_effect_within_the_decision_scope_is_accepted(self):
        waiver = self.bounded_waiver({"stage-8-funnel-integration"})

        decision = passing_decision(
            disposition=GateDisposition.WAIVED,
            scope="stage-8-funnel-integration",
            waiver=waiver,
        )

        self.assertEqual(
            frozenset({"stage-8-funnel-integration"}),
            decision.waiver.downstream_effects,
        )

    def test_waiver_effect_broader_than_the_decision_scope_is_refused(self):
        waiver = self.bounded_waiver({"stage-9-launch-qa"})

        with self.assertRaises(GateDecisionError):
            passing_decision(
                disposition=GateDisposition.WAIVED,
                scope="stage-8-funnel-integration",
                waiver=waiver,
            )

    def test_waiver_effect_outside_the_decision_scope_is_refused(self):
        waiver = self.bounded_waiver(
            {"stage-8-funnel-integration", "stage-10-performance"}
        )

        with self.assertRaises(GateDecisionError):
            passing_decision(
                disposition=GateDisposition.WAIVED,
                scope="stage-8-funnel-integration",
                waiver=waiver,
            )


class GateDecisionFromGateTests(unittest.TestCase):
    def test_factory_pins_the_gates_exact_required_assets(self):
        gate = approvable_gate()

        decision = GateDecision.from_gate(
            gate,
            ledger=ledger_through(7),
            reviewer="client-approver-1",
            scope="stage-8-funnel-integration",
            checkpoint_evidence="rubric passed",
            disposition=GateDisposition.APPROVED,
            rationale="client approved the exact script and creative",
            on=TODAY,
            assigned_owner="production-manager",
            due_on=DATE_DUE,
        )

        self.assertEqual(gate.required_assets, decision.required_assets)
        self.assertEqual(gate.stage_number, decision.stage_number)
        self.assertTrue(decision.authorizes_downstream())

    def test_cannot_record_approval_for_a_gate_with_missing_assets(self):
        gate = approvable_gate(
            evidenced=False,
            state=GateState.IN_REVIEW,
        )

        with self.assertRaises(GateDecisionError):
            GateDecision.from_gate(
                gate,
                ledger=ledger_through(7),
                reviewer="client-approver-1",
                scope="stage-8-funnel-integration",
                checkpoint_evidence="rubric passed",
                disposition=GateDisposition.APPROVED,
                rationale="premature",
                on=TODAY,
                assigned_owner="production-manager",
                due_on=DATE_DUE,
            )

    def test_cannot_record_approval_while_the_ledger_lacks_the_prerequisite(self):
        gate = approvable_gate()
        ledger = ledger_through(6)

        with self.assertRaises(GateDecisionError):
            GateDecision.from_gate(
                gate,
                ledger=ledger,
                reviewer="client-approver-1",
                scope="stage-8-funnel-integration",
                checkpoint_evidence="rubric passed",
                disposition=GateDisposition.APPROVED,
                rationale="dependency not done",
                on=TODAY,
                assigned_owner="production-manager",
                due_on=DATE_DUE,
            )
        self.assertFalse(ledger.has_passing_decision(6, on=TODAY))

    def test_cannot_record_approval_by_an_actor_without_the_designated_authority(self):
        gate = approvable_gate()

        with self.assertRaises(GateDecisionError):
            GateDecision.from_gate(
                gate,
                ledger=ledger_through(7),
                reviewer="specialist-1",
                scope="stage-8-funnel-integration",
                checkpoint_evidence="rubric passed",
                disposition=GateDisposition.APPROVED,
                rationale="self approval attempt",
                on=TODAY,
                assigned_owner="production-manager",
                due_on=DATE_DUE,
            )
        self.assertEqual("client-approver-1", gate.approver)

    def test_factory_records_a_blocked_disposition_without_authorizing(self):
        gate = approvable_gate(state=GateState.BLOCKED)

        decision = GateDecision.from_gate(
            gate,
            ledger=GateLedger(TEMPLATE),
            reviewer="governance-manager",
            scope="stage-8-funnel-integration",
            checkpoint_evidence="dependency failed",
            disposition=GateDisposition.BLOCKED,
            rationale="upstream method change",
            on=TODAY,
            assigned_owner="production-manager",
            due_on=DATE_DUE,
        )

        self.assertFalse(decision.authorizes_downstream())


if __name__ == "__main__":
    unittest.main()
