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

from redops.contexts.governance.domain.entities import GateDecision, StageGate
from redops.contexts.governance.domain.errors import GateDecisionError
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateDisposition,
    GateState,
    Waiver,
)

TODAY = date(2026, 10, 2)
SCRIPT_V1 = AssetVersionRef("authority-amplifier-script", 1)
VIDEO_V1 = AssetVersionRef("authority-amplifier-video", 1)


def approvable_gate(**overrides) -> StageGate:
    values = {
        "stage_number": 7,
        "template_version": "2026.1",
        "required_assets": frozenset({SCRIPT_V1, VIDEO_V1}),
        "dependencies": frozenset({6}),
        "approved_assets": frozenset({SCRIPT_V1, VIDEO_V1}),
        "state": GateState.APPROVED,
        "proposed_by": "specialist-1",
        "approver": "client-approver-1",
    }
    values.update(overrides)
    return StageGate(**values)


def passing_decision(**overrides) -> GateDecision:
    values = {
        "stage_number": 7,
        "template_version": "2026.1",
        "required_assets": frozenset({SCRIPT_V1, VIDEO_V1}),
        "checkpoint_evidence": "authority-amplifier-approved-rubric passed",
        "reviewer": "client-approver-1",
        "scope": "stage-8-funnel-integration",
        "disposition": GateDisposition.APPROVED,
        "rationale": "script and final creative reviewed with the client",
        "decided_on": TODAY,
        "next_action": "release stage 8 work",
    }
    values.update(overrides)
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
        )
        decision = passing_decision(
            disposition=GateDisposition.WAIVED,
            scope="stage-8-funnel-integration",
            waiver=waiver,
        )

        self.assertFalse(decision.is_passing)
        self.assertFalse(decision.authorizes_downstream())


class GateDecisionFromGateTests(unittest.TestCase):
    def test_factory_pins_the_gates_exact_required_assets(self):
        gate = approvable_gate()

        decision = GateDecision.from_gate(
            gate,
            reviewer="client-approver-1",
            scope="stage-8-funnel-integration",
            checkpoint_evidence="rubric passed",
            disposition=GateDisposition.APPROVED,
            rationale="client approved the exact script and creative",
            on=TODAY,
            dependency_states={6: GateState.APPROVED},
        )

        self.assertEqual(gate.required_assets, decision.required_assets)
        self.assertEqual(gate.stage_number, decision.stage_number)
        self.assertTrue(decision.authorizes_downstream())

    def test_cannot_record_approval_for_a_gate_with_missing_assets(self):
        gate = approvable_gate(
            approved_assets=frozenset({SCRIPT_V1}),
            state=GateState.IN_REVIEW,
        )

        with self.assertRaises(GateDecisionError):
            GateDecision.from_gate(
                gate,
                reviewer="client-approver-1",
                scope="stage-8-funnel-integration",
                checkpoint_evidence="rubric passed",
                disposition=GateDisposition.APPROVED,
                rationale="premature",
                on=TODAY,
                dependency_states={6: GateState.APPROVED},
            )

    def test_cannot_record_approval_over_an_unapproved_dependency(self):
        gate = approvable_gate()

        with self.assertRaises(GateDecisionError):
            GateDecision.from_gate(
                gate,
                reviewer="client-approver-1",
                scope="stage-8-funnel-integration",
                checkpoint_evidence="rubric passed",
                disposition=GateDisposition.APPROVED,
                rationale="dependency not done",
                on=TODAY,
                dependency_states={6: GateState.IN_REVIEW},
            )

    def test_cannot_record_approval_by_an_actor_without_the_designated_authority(self):
        gate = approvable_gate()

        with self.assertRaises(GateDecisionError):
            GateDecision.from_gate(
                gate,
                reviewer="specialist-1",
                scope="stage-8-funnel-integration",
                checkpoint_evidence="rubric passed",
                disposition=GateDisposition.APPROVED,
                rationale="self approval attempt",
                on=TODAY,
                dependency_states={6: GateState.APPROVED},
            )
        self.assertEqual("client-approver-1", gate.approver)

    def test_factory_records_a_blocked_disposition_without_authorizing(self):
        gate = approvable_gate(state=GateState.BLOCKED)

        decision = GateDecision.from_gate(
            gate,
            reviewer="governance-manager",
            scope="stage-8-funnel-integration",
            checkpoint_evidence="dependency failed",
            disposition=GateDisposition.BLOCKED,
            rationale="upstream method change",
            on=TODAY,
        )

        self.assertFalse(decision.authorizes_downstream())


if __name__ == "__main__":
    unittest.main()
