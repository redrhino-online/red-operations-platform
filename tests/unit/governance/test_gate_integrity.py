"""Behavioral tests for stage 0-10 gate integrity (pure domain, Governance context).

Rules under test come from SPEC.md sections 3 and 4:
- Stage completion requires gate acceptance, not merely activity.
- Passing a gate pins the exact required asset versions and downstream use.
- A failed or unapproved prerequisite blocks dependent authorization.
- A waiver is a scoped human decision; it never makes an absent asset appear present.
- An author cannot impersonate the approver; approval is version specific.
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import ApprovalRequest, StageGate
from redops.contexts.governance.domain.policies import GateIntegrityPolicy
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateState,
    Waiver,
)

TODAY = date(2026, 10, 2)
SCRIPT_V1 = AssetVersionRef("authority-amplifier-script", 1)
VIDEO_V1 = AssetVersionRef("authority-amplifier-video", 1)


def approval_for(asset):
    request = ApprovalRequest(
        asset=asset,
        scope="stage-8-funnel-integration",
        requested_by="specialist-1",
        approver="client-approver-1",
    )
    request.approve(actor="client-approver-1", on=TODAY)
    return request


class GateIntegrityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = GateIntegrityPolicy()

    def gate(self, approved_assets=None, **overrides):
        values = {
            "stage_number": 7,
            "template_version": "2026.1",
            "required_assets": frozenset({SCRIPT_V1, VIDEO_V1}),
            "dependencies": frozenset({6}),
            "state": GateState.IN_REVIEW,
            "proposed_by": "specialist-1",
            "approver": "client-approver-1",
        }
        values.update(overrides)
        gate = StageGate(**values)
        for asset in approved_assets if approved_assets is not None else gate.required_assets:
            gate.record_asset_approval(approval_for(asset))
        return gate

    def test_activity_without_exact_asset_version_cannot_be_approved(self):
        gate = self.gate(
            approved_assets=frozenset({SCRIPT_V1}),
            state=GateState.WORKING,
        )

        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, on=TODAY,
            scope="stage-8-funnel-integration",
        )

        self.assertFalse(result.approvable)
        self.assertIn("authority-amplifier-video@1", " ".join(result.reasons))
        self.assertFalse(gate.authorizes_downstream(TODAY, "stage-8-funnel-integration"))

    def test_unapproved_dependency_blocks_approval(self):
        gate = self.gate()

        result = self.policy.evaluate(
            gate, {6: GateState.IN_REVIEW}, on=TODAY,
            scope="stage-8-funnel-integration",
        )

        self.assertFalse(result.approvable)
        self.assertIn("6", " ".join(result.reasons))
        self.assertFalse(gate.authorizes_downstream(TODAY, "stage-8-funnel-integration"))

    def test_waiver_does_not_substitute_for_a_missing_asset(self):
        waiver = Waiver(
            reason="video delayed by vendor",
            risk_owner="production-manager",
            review_trigger="vendor delivery",
        )
        gate = self.gate(
            approved_assets=frozenset({SCRIPT_V1}),
            state=GateState.WAIVED,
            waiver=waiver,
        )

        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, on=TODAY,
            scope="stage-8-funnel-integration",
        )

        self.assertFalse(result.approvable)
        self.assertFalse(gate.authorizes_downstream(TODAY, "stage-8-funnel-integration"))

    def test_author_cannot_approve_own_proposal(self):
        gate = self.gate(proposed_by="same-person", approver="same-person")

        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, on=TODAY,
            scope="stage-8-funnel-integration",
        )

        self.assertFalse(result.approvable)
        self.assertIn("own proposal", " ".join(result.reasons))

    def test_approval_requires_a_designated_approver(self):
        gate = self.gate(approver=None)

        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, on=TODAY,
            scope="stage-8-funnel-integration",
        )

        self.assertFalse(result.approvable)

    def test_complete_gate_with_all_dependencies_approves_and_authorizes(self):
        gate = self.gate(state=GateState.APPROVED)

        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, on=TODAY,
            scope="stage-8-funnel-integration",
        )

        self.assertTrue(result.approvable)
        self.assertTrue(gate.authorizes_downstream(TODAY, "stage-8-funnel-integration"))

    def test_superseded_gate_never_authorizes_downstream(self):
        gate = self.gate(state=GateState.SUPERSEDED)

        self.assertFalse(gate.authorizes_downstream(TODAY, "stage-8-funnel-integration"))

    def test_waiver_requires_a_named_risk_owner(self):
        with self.assertRaises(ValueError):
            Waiver(reason="delay", risk_owner="", review_trigger="review")


if __name__ == "__main__":
    unittest.main()
