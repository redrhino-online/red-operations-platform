"""Behavioral tests for the canonical checkpoint rubric on the gate record.

SPEC.md section 4 ("Gate record and production manager view") requires every
stage to persist the checkpoint rubric alongside the template version, the exact
asset versions, the approver and the dependencies. The canonical rubric lives on
``StageDefinition.checkpoint``, so a gate must derive it from the template rather
than declare it, and a passing decision must name the same rubric or it is
refused. Without this, an application boundary could self-declare a checkpoint
that differs from the template and still pass the gate.
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import (
    GateDecision,
    GateLedger,
    StageGate,
)
from redops.contexts.governance.domain.errors import (
    CheckpointMismatchError,
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
DATE_DUE = date(2026, 10, 16)
TEMPLATE = stage_zero_to_ten_template(VERSION)


def versions_for(stage_number, version=1):
    return {
        kind: version for kind in TEMPLATE.required_asset_kinds(stage_number)
    }


def canonical_passing(stage_number, version=VERSION, checkpoint=None):
    template = stage_zero_to_ten_template(version)
    if checkpoint is None:
        checkpoint = template.definition_for(stage_number).checkpoint
    return GateDecision(
        stage_number=stage_number,
        template_version=version,
        required_assets=frozenset(
            AssetVersionRef(kind, 1)
            for kind in template.required_asset_kinds(stage_number)
        ),
        checkpoint=checkpoint,
        checkpoint_evidence=f"stage {stage_number} rubric passed",
        reviewer="client-approver-1",
        scope=f"stage-{stage_number + 1}-downstream",
        disposition=GateDisposition.APPROVED,
        rationale="reviewed against the canonical checkpoint",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=DATE_DUE,
    )


def ledger_through(stage_number):
    ledger = GateLedger(TEMPLATE)
    for stage in range(stage_number):
        ledger.record(canonical_passing(stage))
    return ledger


def approvable_gate(stage_number=7, **overrides):
    gate = StageGate.from_template(TEMPLATE, stage_number, versions_for(stage_number))
    gate.state = GateState.APPROVED
    gate.approved_assets = gate.required_assets
    gate.proposed_by = "specialist-1"
    gate.approver = "client-approver-1"
    for name, value in overrides.items():
        setattr(gate, name, value)
    return gate


class StageGateCheckpointTests(unittest.TestCase):
    def test_factory_pins_the_canonical_checkpoint_rubric(self):
        self.assertEqual(
            "Authority Amplifier Approved",
            StageGate.from_template(TEMPLATE, 7, versions_for(7)).checkpoint,
        )
        self.assertEqual(
            "Diagnostic Model Approved",
            StageGate.from_template(TEMPLATE, 3, versions_for(3)).checkpoint,
        )

    def test_factory_checkpoint_matches_every_stage_definition(self):
        for definition in TEMPLATE.stages:
            with self.subTest(stage=definition.stage_number):
                gate = StageGate.from_template(
                    TEMPLATE, definition.stage_number, versions_for(definition.stage_number)
                )
                self.assertEqual(definition.checkpoint, gate.checkpoint)

    def test_policy_rejects_a_self_declared_checkpoint(self):
        gate = approvable_gate(checkpoint="Totally Made Up Rubric")

        result = GateIntegrityPolicy().evaluate(
            gate, {6: GateState.APPROVED}, template=TEMPLATE
        )

        self.assertFalse(result.approvable)
        self.assertIn("checkpoint", " ".join(result.reasons))

    def test_policy_accepts_the_canonical_checkpoint(self):
        gate = approvable_gate()

        result = GateIntegrityPolicy().evaluate(
            gate, {6: GateState.APPROVED}, template=TEMPLATE
        )

        self.assertTrue(result.approvable, result.reasons)


class GateDecisionCheckpointTests(unittest.TestCase):
    def test_passing_decision_requires_a_checkpoint_rubric(self):
        with self.assertRaises(GateDecisionError):
            canonical_passing(0, checkpoint="")

    def test_factory_persists_the_canonical_checkpoint_from_the_gate(self):
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

        self.assertEqual("Authority Amplifier Approved", decision.checkpoint)
        self.assertEqual(gate.checkpoint, decision.checkpoint)

    def test_factory_refuses_a_gate_with_a_self_declared_checkpoint(self):
        gate = approvable_gate(checkpoint="Totally Made Up Rubric")

        with self.assertRaises(GateDecisionError):
            GateDecision.from_gate(
                gate,
                ledger=ledger_through(7),
                reviewer="client-approver-1",
                scope="stage-8-funnel-integration",
                checkpoint_evidence="rubric passed",
                disposition=GateDisposition.APPROVED,
                rationale="checkpoint not from the template",
                on=TODAY,
                assigned_owner="production-manager",
                due_on=DATE_DUE,
            )


class GateLedgerCheckpointTests(unittest.TestCase):
    def test_refuses_a_passing_decision_whose_checkpoint_differs(self):
        ledger = GateLedger(TEMPLATE)

        with self.assertRaises(CheckpointMismatchError):
            ledger.record(canonical_passing(0, checkpoint="Not The Stage 0 Rubric"))

        self.assertFalse(ledger.has_passing_decision(0))

    def test_records_a_passing_decision_with_the_canonical_checkpoint(self):
        ledger = GateLedger(TEMPLATE)

        ledger.record(canonical_passing(0))

        self.assertTrue(ledger.has_passing_decision(0))
        self.assertEqual(
            "Production Ready", ledger.decision_for(0).checkpoint
        )


if __name__ == "__main__":
    unittest.main()
