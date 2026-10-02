"""Behavioral tests for approval-evidenced gate assets (pure domain, Governance).

Rules under test come from SPEC.md sections 3 and 4:

- "Passing a gate pins the exact evidence and intended downstream use."
- A stage is complete only when its required assets pass the gate; "a failed or
  expired prerequisite blocks dependent authorization until resolved."
- The GateDecision aggregate pins "the required asset versions" (section 3).

``StageGate.approved_assets`` must instead be derived from recorded,
version-specific approvals for the intended downstream scope that are unexpired
at the evaluation instant, so the gate, ``GateIntegrityPolicy`` and the durable
``GateDecision`` all apply the same version, scope and expiry rule.
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
    StageGate,
)
from redops.contexts.governance.domain.errors import (
    AssetPackageMismatchError,
    GateDecisionError,
)
from redops.contexts.governance.domain.policies import GateIntegrityPolicy
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateDisposition,
    GateState,
)

VERSION = "2026.1"
TODAY = date(2026, 10, 2)
DUE = date(2026, 10, 16)
TEMPLATE = stage_zero_to_ten_template(VERSION)
SCRIPT_V1 = AssetVersionRef("authority-amplifier-script", 1)
SCRIPT_V2 = AssetVersionRef("authority-amplifier-script", 2)
VIDEO_V1 = AssetVersionRef("authority-amplifier-video", 1)


def request_for(asset, *, approved=True):
    request = ApprovalRequest(
        asset=asset,
        scope="stage-8-funnel-integration",
        requested_by="specialist-1",
        approver="client-approver-1",
    )
    if approved:
        request.approve(actor="client-approver-1", on=TODAY)
    return request


def approval_for(asset, scope):
    request = ApprovalRequest(
        asset=asset,
        scope=scope,
        requested_by="specialist-1",
        approver="client-approver-1",
    )
    request.approve(actor="client-approver-1", on=TODAY)
    return request


def passing_decision_for(stage_number):
    kinds = TEMPLATE.required_asset_kinds(stage_number)
    scope = f"stage-{stage_number + 1}-downstream"
    return GateDecision(
        stage_number=stage_number,
        template_version=VERSION,
        required_assets=frozenset(AssetVersionRef(kind, 1) for kind in kinds),
        checkpoint=TEMPLATE.definition_for(stage_number).checkpoint,
        checkpoint_evidence=f"stage {stage_number} rubric passed",
        reviewer="client-approver-1",
        scope=scope,
        disposition=GateDisposition.APPROVED,
        rationale="reviewed against the checkpoint",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=DUE,
        dependencies=TEMPLATE.dependencies_of(stage_number),
        asset_approvals=tuple(
            approval_for(AssetVersionRef(kind, 1), scope) for kind in kinds
        ),
    )


def ledger_through(stage_number):
    ledger = GateLedger(TEMPLATE)
    for stage in range(stage_number):
        ledger.record(passing_decision_for(stage))
    return ledger


def gate_with_required(*assets) -> StageGate:
    gate = StageGate.from_template(
        TEMPLATE, 7, {kind: 1 for kind in TEMPLATE.required_asset_kinds(7)}
    )
    gate.required_assets = frozenset(assets)
    gate.state = GateState.APPROVED
    gate.proposed_by = "specialist-1"
    gate.approver = "client-approver-1"
    return gate


class GateAssetEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.policy = GateIntegrityPolicy()

    def test_gate_with_no_recorded_approval_does_not_evidence_the_asset(self):
        gate = gate_with_required(SCRIPT_V1)

        self.assertFalse(gate.authorizes_downstream(TODAY, "stage-8-funnel-integration"))
        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, TEMPLATE, on=TODAY,
            scope="stage-8-funnel-integration",
        )
        self.assertFalse(result.approvable)
        self.assertIn("authority-amplifier-script@1", " ".join(result.reasons))

    def test_recorded_exact_version_approval_evidences_the_asset(self):
        gate = gate_with_required(SCRIPT_V1)
        gate.record_asset_approval(request_for(SCRIPT_V1))

        self.assertEqual(frozenset({SCRIPT_V1}), gate.approved_assets(TODAY, "stage-8-funnel-integration"))
        self.assertTrue(gate.authorizes_downstream(TODAY, "stage-8-funnel-integration"))
        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, on=TODAY,
            scope="stage-8-funnel-integration",
        )
        self.assertTrue(result.approvable, result.reasons)

    def test_approval_for_another_version_does_not_evidence_the_pinned_asset(self):
        gate = gate_with_required(SCRIPT_V1)

        with self.assertRaises(AssetPackageMismatchError):
            gate.record_asset_approval(request_for(SCRIPT_V2))

        self.assertEqual(frozenset(), gate.approved_assets(TODAY, "stage-8-funnel-integration"))
        self.assertFalse(gate.authorizes_downstream(TODAY, "stage-8-funnel-integration"))

    def test_pending_request_does_not_evidence_the_asset(self):
        gate = gate_with_required(SCRIPT_V1)
        gate.record_asset_approval(request_for(SCRIPT_V1, approved=False))

        self.assertEqual(frozenset(), gate.approved_assets(TODAY, "stage-8-funnel-integration"))

    def test_recording_an_approval_for_an_asset_outside_the_package_is_rejected(self):
        gate = gate_with_required(SCRIPT_V1)

        with self.assertRaises(AssetPackageMismatchError):
            gate.record_asset_approval(request_for(VIDEO_V1))

    def test_a_partial_approval_package_leaves_the_other_asset_missing(self):
        gate = gate_with_required(SCRIPT_V1, VIDEO_V1)
        gate.record_asset_approval(request_for(SCRIPT_V1))

        self.assertEqual(frozenset({VIDEO_V1}), gate.missing_assets(TODAY, "stage-8-funnel-integration"))


class GateDecisionEvidenceUnificationTests(unittest.TestCase):
    """A passing decision pins the gate's recorded approvals, not a substitute.

    SPEC.md sections 3 and 4 require a passing gate to pin "the exact evidence
    and intended downstream use". The factory must therefore record the very
    ``ApprovalRequest``s the gate stored and the integrity policy evaluated, so
    the durable decision and the gate cannot diverge.
    """

    def stage7_gate(self, scope):
        kinds = TEMPLATE.required_asset_kinds(7)
        gate = StageGate.from_template(
            TEMPLATE, 7, {kind: 1 for kind in kinds}
        )
        gate.state = GateState.APPROVED
        gate.proposed_by = "specialist-1"
        gate.approver = "client-approver-1"
        for asset in gate.required_assets:
            gate.record_asset_approval(approval_for(asset, scope))
        return gate

    def decision_kwargs(self, scope):
        return dict(
            ledger=ledger_through(7),
            reviewer="client-approver-1",
            scope=scope,
            checkpoint_evidence="authority-amplifier-approved-rubric passed",
            disposition=GateDisposition.APPROVED,
            rationale="client approved the exact script and creative",
            on=TODAY,
            assigned_owner="production-manager",
            due_on=DUE,
        )

    def test_factory_pins_exactly_the_gates_recorded_approvals(self):
        scope = "stage-8-funnel-integration"
        gate = self.stage7_gate(scope)

        decision = GateDecision.from_gate(
            gate, **self.decision_kwargs(scope)
        )

        self.assertEqual(gate.asset_approvals, decision.asset_approvals)
        self.assertTrue(decision.authorizes_downstream())

    def test_factory_refuses_gate_evidence_that_does_not_cover_the_scope(self):
        gate = self.stage7_gate("some-other-use")

        with self.assertRaises(GateDecisionError):
            GateDecision.from_gate(
                gate, **self.decision_kwargs("stage-8-funnel-integration")
            )


class GateApprovalExpiryTests(unittest.TestCase):
    """An expired approval must not evidence a gate asset at evaluation.

    SPEC.md section 4: "a failed or expired prerequisite blocks dependent
    authorization until resolved"; section 11: approval is version specific.
    The gate's evidenced asset set and ``GateIntegrityPolicy`` must agree with
    the durable ``GateDecision``, which already refuses an expired approval
    through ``ApprovalRequest.authorizes``.
    """

    def setUp(self):
        self.policy = GateIntegrityPolicy()

    def stage7_gate(self, *, approved_on, expires_on):
        kinds = TEMPLATE.required_asset_kinds(7)
        gate = StageGate.from_template(
            TEMPLATE, 7, {kind: 1 for kind in kinds}
        )
        gate.state = GateState.APPROVED
        gate.proposed_by = "specialist-1"
        gate.approver = "client-approver-1"
        for asset in gate.required_assets:
            request = ApprovalRequest(
                asset=asset,
                scope="stage-8-funnel-integration",
                requested_by="specialist-1",
                approver="client-approver-1",
                expires_on=expires_on,
            )
            request.approve(actor="client-approver-1", on=approved_on)
            gate.record_asset_approval(request)
        return gate

    def decision_kwargs(self):
        return dict(
            ledger=ledger_through(7),
            reviewer="client-approver-1",
            scope="stage-8-funnel-integration",
            checkpoint_evidence="authority-amplifier-approved-rubric passed",
            disposition=GateDisposition.APPROVED,
            rationale="client approved the exact script and creative",
            on=TODAY,
            assigned_owner="production-manager",
            due_on=DUE,
        )

    def test_expired_approval_does_not_evidence_a_gate_asset_at_evaluation(self):
        gate = self.stage7_gate(
            approved_on=date(2026, 9, 30), expires_on=date(2026, 10, 1)
        )

        self.assertFalse(gate.authorizes_downstream(TODAY, "stage-8-funnel-integration"))
        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, TEMPLATE, on=TODAY,
            scope="stage-8-funnel-integration",
        )
        self.assertFalse(result.approvable)
        self.assertIn(
            "authority-amplifier-script@1", " ".join(result.reasons)
        )

    def test_unexpired_approval_evidences_the_gate_asset(self):
        gate = self.stage7_gate(
            approved_on=TODAY, expires_on=date(2026, 12, 31)
        )

        self.assertTrue(gate.authorizes_downstream(TODAY, "stage-8-funnel-integration"))
        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, TEMPLATE, on=TODAY,
            scope="stage-8-funnel-integration",
        )
        self.assertTrue(result.approvable, result.reasons)

    def test_factory_refuses_a_passing_decision_after_the_approval_expires(self):
        gate = self.stage7_gate(
            approved_on=date(2026, 9, 30), expires_on=date(2026, 10, 1)
        )

        with self.assertRaises(GateDecisionError):
            GateDecision.from_gate(gate, **self.decision_kwargs())


class GateApprovalScopeTests(unittest.TestCase):
    """An approval for another intended scope must not evidence a gate asset.

    SPEC.md sections 3, 4 and 11: a passing gate pins "the exact evidence and
    intended downstream use", and approval is version and scope specific. The
    gate's evidenced set and ``GateIntegrityPolicy`` must agree with the durable
    ``GateDecision`` about scope, not only about version and expiry.
    """

    def setUp(self):
        self.policy = GateIntegrityPolicy()

    def stage7_gate(self, scope):
        kinds = TEMPLATE.required_asset_kinds(7)
        gate = StageGate.from_template(
            TEMPLATE, 7, {kind: 1 for kind in kinds}
        )
        gate.state = GateState.APPROVED
        gate.proposed_by = "specialist-1"
        gate.approver = "client-approver-1"
        for asset in gate.required_assets:
            gate.record_asset_approval(approval_for(asset, scope))
        return gate

    def test_approval_for_another_scope_does_not_evidence_the_asset(self):
        intended = "stage-8-funnel-integration"
        gate = self.stage7_gate("some-other-use")

        self.assertEqual(frozenset(), gate.approved_assets(TODAY, intended))
        self.assertFalse(gate.authorizes_downstream(TODAY, intended))
        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, TEMPLATE, on=TODAY, scope=intended
        )
        self.assertFalse(result.approvable)
        self.assertIn(
            "authority-amplifier-script@1", " ".join(result.reasons)
        )

    def test_approval_for_the_intended_scope_evidences_the_asset(self):
        intended = "stage-8-funnel-integration"
        gate = self.stage7_gate(intended)

        self.assertEqual(
            gate.required_assets, gate.approved_assets(TODAY, intended)
        )
        self.assertTrue(gate.authorizes_downstream(TODAY, intended))
        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, TEMPLATE, on=TODAY, scope=intended
        )
        self.assertTrue(result.approvable, result.reasons)


if __name__ == "__main__":
    unittest.main()
