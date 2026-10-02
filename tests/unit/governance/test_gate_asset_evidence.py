"""Behavioral tests for approval-evidenced gate assets (pure domain, Governance).

Rules under test come from SPEC.md sections 3 and 4:

- "Passing a gate pins the exact evidence and intended downstream use."
- A stage is complete only when its required assets pass the gate; "a failed or
  expired prerequisite blocks dependent authorization until resolved."
- The GateDecision aggregate pins "the required asset versions" (section 3).

``StageGate.approved_assets`` was a self-managed set that GateIntegrityPolicy
consulted, so a gate could declare its own asset package approved with no durable
``ApprovalRequest`` behind it, and the gate the policy evaluated could diverge
from the evidence the durable decision pinned. A gate's approved set must instead
be derived from recorded, version-specific approvals. Scope and expiry exactness
remain validated at decision time by ``GateDecision``.
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import ApprovalRequest, StageGate
from redops.contexts.governance.domain.errors import AssetPackageMismatchError
from redops.contexts.governance.domain.policies import GateIntegrityPolicy
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateState,
)

VERSION = "2026.1"
TODAY = date(2026, 10, 2)
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

    def test_gate_does_not_accept_a_directly_assigned_approved_asset_set(self):
        gate = gate_with_required(SCRIPT_V1)

        with self.assertRaises(AttributeError):
            gate.approved_assets = frozenset({SCRIPT_V1})

    def test_gate_with_no_recorded_approval_does_not_evidence_the_asset(self):
        gate = gate_with_required(SCRIPT_V1)

        self.assertFalse(gate.authorizes_downstream())
        result = self.policy.evaluate(gate, {6: GateState.APPROVED}, TEMPLATE)
        self.assertFalse(result.approvable)
        self.assertIn("authority-amplifier-script@1", " ".join(result.reasons))

    def test_recorded_exact_version_approval_evidences_the_asset(self):
        gate = gate_with_required(SCRIPT_V1)
        gate.record_asset_approval(request_for(SCRIPT_V1))

        self.assertEqual(frozenset({SCRIPT_V1}), gate.approved_assets)
        self.assertTrue(gate.authorizes_downstream())
        result = self.policy.evaluate(gate, {6: GateState.APPROVED})
        self.assertTrue(result.approvable, result.reasons)

    def test_approval_for_another_version_does_not_evidence_the_pinned_asset(self):
        gate = gate_with_required(SCRIPT_V1)

        with self.assertRaises(AssetPackageMismatchError):
            gate.record_asset_approval(request_for(SCRIPT_V2))

        self.assertEqual(frozenset(), gate.approved_assets)
        self.assertFalse(gate.authorizes_downstream())

    def test_pending_request_does_not_evidence_the_asset(self):
        gate = gate_with_required(SCRIPT_V1)
        gate.record_asset_approval(request_for(SCRIPT_V1, approved=False))

        self.assertEqual(frozenset(), gate.approved_assets)

    def test_recording_an_approval_for_an_asset_outside_the_package_is_rejected(self):
        gate = gate_with_required(SCRIPT_V1)

        with self.assertRaises(AssetPackageMismatchError):
            gate.record_asset_approval(request_for(VIDEO_V1))

    def test_a_partial_approval_package_leaves_the_other_asset_missing(self):
        gate = gate_with_required(SCRIPT_V1, VIDEO_V1)
        gate.record_asset_approval(request_for(SCRIPT_V1))

        self.assertEqual(frozenset({VIDEO_V1}), gate.missing_assets())


if __name__ == "__main__":
    unittest.main()
