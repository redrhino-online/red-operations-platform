"""Behavioral tests tying a passing gate's assets to version-specific approvals.

Rules under test come from SPEC.md sections 3, 4 and 11:

- "Passing a gate pins the exact evidence and intended downstream use."
- "Approval is version specific" and "Author cannot impersonate approver"
  (section 11 acceptance scenarios).
- The GateDecision aggregate pins "the required asset versions, the checkpoint
  evidence, the reviewer, the scope, disposition" (section 3 aggregate table).

A passing gate decision must not be recordable from a self-declared approved
asset set alone. Every pinned asset version must be covered by a durable
ApprovalRequest that is approved for that exact version and the decision's
intended downstream scope, is not expired at decision time, and names a
designated approver distinct from the requester. Without this, a failing or
forged gate could be represented as approved downstream evidence.
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
    StageGate,
)
from redops.contexts.governance.domain.errors import UnapprovedAssetError
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateDisposition,
    GateState,
)

VERSION = "2026.1"
TODAY = date(2026, 10, 2)
DATE_DUE = date(2026, 10, 16)
SCOPE = "stage-8-funnel-integration"
SCRIPT_V1 = AssetVersionRef("authority-amplifier-script", 1)
SCRIPT_V2 = AssetVersionRef("authority-amplifier-script", 2)
VIDEO_V1 = AssetVersionRef("authority-amplifier-video", 1)
ASSETS = frozenset({SCRIPT_V1, VIDEO_V1})
TEMPLATE = stage_zero_to_ten_template(VERSION)
STAGE7_ASSETS = frozenset(
    AssetVersionRef(kind, 1) for kind in TEMPLATE.required_asset_kinds(7)
)


def approved(asset, *, scope=SCOPE, on=TODAY, expires_on=None):
    request = ApprovalRequest(
        asset=asset,
        scope=scope,
        requested_by="specialist-1",
        approver="client-approver-1",
        expires_on=expires_on,
    )
    request.approve(actor="client-approver-1", on=on)
    return request


def decision(asset_approvals=(), **overrides):
    values = {
        "stage_number": 7,
        "template_version": VERSION,
        "required_assets": ASSETS,
        "checkpoint": "Authority Amplifier Approved",
        "checkpoint_evidence": "authority-amplifier-approved-rubric passed",
        "reviewer": "client-approver-1",
        "scope": SCOPE,
        "disposition": GateDisposition.APPROVED,
        "rationale": "script and final creative reviewed with the client",
        "decided_on": TODAY,
        "assigned_owner": "production-manager",
        "due_on": DATE_DUE,
        "asset_approvals": tuple(asset_approvals),
    }
    values.update(overrides)
    return GateDecision(**values)


def ledger_through(stage_number):
    ledger = GateLedger(TEMPLATE)
    for stage in range(stage_number):
        stage_assets = frozenset(
            AssetVersionRef(kind, 1)
            for kind in TEMPLATE.required_asset_kinds(stage)
        )
        scope = f"stage-{stage + 1}-downstream"
        ledger.record(
            GateDecision(
                stage_number=stage,
                template_version=VERSION,
                required_assets=stage_assets,
                checkpoint=TEMPLATE.definition_for(stage).checkpoint,
                checkpoint_evidence=f"stage {stage} rubric passed",
                reviewer="client-approver-1",
                scope=scope,
                disposition=GateDisposition.APPROVED,
                rationale="reviewed against the checkpoint",
                decided_on=TODAY,
                assigned_owner="production-manager",
                due_on=DATE_DUE,
                asset_approvals=tuple(
                    approved(asset, scope=scope) for asset in stage_assets
                ),
            )
        )
    return ledger


def approvable_gate():
    versions = {kind: 1 for kind in TEMPLATE.required_asset_kinds(7)}
    gate = StageGate.from_template(TEMPLATE, 7, versions)
    gate.state = GateState.APPROVED
    gate.approved_assets = gate.required_assets
    gate.proposed_by = "specialist-1"
    gate.approver = "client-approver-1"
    return gate


class PerAssetApprovalTests(unittest.TestCase):
    def test_passing_decision_is_refused_without_recorded_per_asset_approvals(self):
        with self.assertRaises(UnapprovedAssetError):
            decision()

    def test_passing_decision_is_refused_with_a_partial_approval_package(self):
        with self.assertRaises(UnapprovedAssetError):
            decision([approved(SCRIPT_V1)])

    def test_passing_decision_is_accepted_with_one_approval_per_pinned_asset(self):
        record = decision([approved(SCRIPT_V1), approved(VIDEO_V1)])

        self.assertTrue(record.is_passing)
        self.assertTrue(record.authorizes_downstream())
        self.assertEqual(frozenset(), record.unapproved_assets())

    def test_approval_for_a_different_version_does_not_cover_the_pinned_asset(self):
        with self.assertRaises(UnapprovedAssetError):
            decision([approved(SCRIPT_V2), approved(VIDEO_V1)])

    def test_approval_for_a_different_scope_does_not_cover(self):
        with self.assertRaises(UnapprovedAssetError):
            decision(
                [
                    approved(SCRIPT_V1, scope="some-other-use"),
                    approved(VIDEO_V1),
                ]
            )

    def test_expired_approval_does_not_cover_the_decision(self):
        with self.assertRaises(UnapprovedAssetError):
            decision(
                [
                    approved(
                        SCRIPT_V1,
                        on=date(2026, 9, 30),
                        expires_on=date(2026, 10, 1),
                    ),
                    approved(VIDEO_V1),
                ]
            )

    def test_unapproved_assets_names_the_uncovered_version(self):
        with self.assertRaises(UnapprovedAssetError) as caught:
            decision([approved(SCRIPT_V1)])
        self.assertIn("authority-amplifier-video@1", str(caught.exception))

    def test_non_passing_decision_does_not_require_asset_approvals(self):
        blocked = decision(disposition=GateDisposition.BLOCKED, asset_approvals=())

        self.assertFalse(blocked.authorizes_downstream())


class FactoryAssetApprovalTests(unittest.TestCase):
    def test_factory_requires_asset_approvals_for_a_passing_decision(self):
        with self.assertRaises(UnapprovedAssetError):
            GateDecision.from_gate(
                approvable_gate(),
                ledger=ledger_through(7),
                reviewer="client-approver-1",
                scope=SCOPE,
                checkpoint_evidence="rubric passed",
                disposition=GateDisposition.APPROVED,
                rationale="client approved the exact script and creative",
                on=TODAY,
                assigned_owner="production-manager",
                due_on=DATE_DUE,
            )

    def test_factory_records_a_passing_decision_with_asset_approvals(self):
        record = GateDecision.from_gate(
            approvable_gate(),
            ledger=ledger_through(7),
            reviewer="client-approver-1",
            scope=SCOPE,
            checkpoint_evidence="rubric passed",
            disposition=GateDisposition.APPROVED,
            rationale="client approved the exact script and creative",
            on=TODAY,
            assigned_owner="production-manager",
            due_on=DATE_DUE,
            asset_approvals=tuple(approved(asset) for asset in STAGE7_ASSETS),
        )

        self.assertTrue(record.authorizes_downstream())
        self.assertEqual(frozenset(), record.unapproved_assets())


if __name__ == "__main__":
    unittest.main()
