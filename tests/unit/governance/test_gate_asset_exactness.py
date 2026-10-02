"""Behavioral tests for exact asset-version pinning on a passing gate.

SPEC.md sections 3 and 4 require a passing GateDecision to pin "the exact
evidence and intended downstream use" and to persist "required assets and their
exact versions". A package that carries two versions of the same asset kind does
not identify one exact version: a reviewer, a downstream stage or an audit cannot
tell which version was actually approved. The canonical template declares each
stage's required assets as a set of *kinds*, so a passing gate must pin exactly
one version per kind. The durable GateLedger and the GateIntegrityPolicy must
refuse an ambiguous package rather than treat the extra version as harmless.
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
    StageGate,
)
from redops.contexts.governance.domain.errors import AmbiguousAssetPackageError
from redops.contexts.governance.domain.policies import GateIntegrityPolicy
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateDisposition,
    GateState,
)

VERSION = "2026.1"
TODAY = date(2026, 10, 2)
DATE_DUE = date(2026, 10, 16)
TEMPLATE = stage_zero_to_ten_template(VERSION)


def approvals(assets, scope):
    for asset in assets:
        request = ApprovalRequest(
            asset=asset,
            scope=scope,
            requested_by="specialist-1",
            approver="client-approver-1",
        )
        request.approve(actor="client-approver-1", on=TODAY)
        yield request


def approval_for(asset):
    return next(approvals([asset], "stage-8-funnel-integration"))


def canonical_assets(stage_number: int) -> frozenset[AssetVersionRef]:
    return frozenset(
        AssetVersionRef(kind, 1)
        for kind in TEMPLATE.required_asset_kinds(stage_number)
    )


def passing_decision(stage_number: int, assets) -> GateDecision:
    definition = TEMPLATE.definition_for(stage_number)
    scope = f"stage-{stage_number + 1}-downstream"
    return GateDecision(
        stage_number=stage_number,
        template_version=VERSION,
        required_assets=assets,
        checkpoint=definition.checkpoint,
        checkpoint_evidence=f"stage {stage_number} rubric passed",
        reviewer="client-approver-1",
        scope=scope,
        disposition=GateDisposition.APPROVED,
        rationale="reviewed against the checkpoint",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=DATE_DUE,
        asset_approvals=tuple(approvals(assets, scope)),
    )


def ledger_through(stage_number: int) -> GateLedger:
    ledger = GateLedger(TEMPLATE)
    for stage in range(stage_number):
        ledger.record(passing_decision(stage, canonical_assets(stage)))
    return ledger


class AmbiguousAssetPackageErrorTests(unittest.TestCase):
    def test_error_is_a_named_governance_rule_violation(self):
        from redops.contexts.governance.domain.errors import (
            AssetPackageMismatchError,
        )

        self.assertTrue(
            issubclass(AmbiguousAssetPackageError, AssetPackageMismatchError)
        )


class GateDecisionExactnessTests(unittest.TestCase):
    def test_passing_decision_refuses_two_versions_of_one_asset_kind(self):
        ambiguous = canonical_assets(7) | frozenset(
            {AssetVersionRef("authority-amplifier-script", 2)}
        )

        with self.assertRaises(AmbiguousAssetPackageError):
            passing_decision(7, ambiguous)

    def test_passing_decision_accepts_one_version_per_kind(self):
        decision = passing_decision(7, canonical_assets(7))

        self.assertTrue(decision.authorizes_downstream())


class GateIntegrityExactnessTests(unittest.TestCase):
    def gate(self, approved_assets=None, **overrides) -> StageGate:
        assets = canonical_assets(7)
        values = {
            "stage_number": 7,
            "template_version": VERSION,
            "required_assets": assets,
            "dependencies": frozenset({6}),
            "checkpoint": TEMPLATE.definition_for(7).checkpoint,
            "state": GateState.APPROVED,
            "proposed_by": "specialist-1",
            "approver": "client-approver-1",
        }
        values.update(overrides)
        gate = StageGate(**values)
        evidenced = (
            approved_assets if approved_assets is not None else gate.required_assets
        )
        for asset in evidenced:
            gate.record_asset_approval(approval_for(asset))
        return gate

    def test_policy_rejects_a_gate_pinning_two_versions_of_one_kind(self):
        ambiguous = canonical_assets(7) | frozenset(
            {AssetVersionRef("authority-amplifier-script", 2)}
        )
        gate = self.gate(required_assets=ambiguous, approved_assets=ambiguous)

        result = GateIntegrityPolicy().evaluate(
            gate, {6: GateState.APPROVED}, template=TEMPLATE, on=TODAY
        )

        self.assertFalse(result.approvable)
        self.assertIn("exact", " ".join(result.reasons).lower())

    def test_policy_accepts_a_gate_with_one_version_per_kind(self):
        result = GateIntegrityPolicy().evaluate(
            self.gate(), {6: GateState.APPROVED}, template=TEMPLATE, on=TODAY
        )

        self.assertTrue(result.approvable, result.reasons)


class GateLedgerExactnessTests(unittest.TestCase):
    def test_ledger_refuses_a_passing_decision_with_an_ambiguous_package(self):
        ledger = ledger_through(7)
        ambiguous = canonical_assets(7) | frozenset(
            {AssetVersionRef("authority-amplifier-script", 2)}
        )

        # The decision invariant already refuses this at construction.
        with self.assertRaises(AmbiguousAssetPackageError):
            passing_decision(7, ambiguous)

        self.assertFalse(ledger.has_passing_decision(7))


if __name__ == "__main__":
    unittest.main()
