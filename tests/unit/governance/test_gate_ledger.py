"""Behavioral tests for the GateLedger aggregate (pure domain, Governance).

Rules under test come from SPEC.md section 4: the 0-10 pipeline is a gated
dependency graph, "a failed or expired prerequisite blocks dependent
authorization until resolved", and completion requires gate acceptance rather
than activity. The durable GateDecision is the only proof of a completed stage,
so the ledger derives prerequisite state from recorded decisions instead of a
caller-supplied dependency map. A passing decision for a stage whose prerequisite
has no passing decision is refused (SPEC.md section 11: launch is blocked on a
failed customer path).
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import (
    GateDecision,
    GateLedger,
    StageGate,
)
from redops.contexts.governance.domain.errors import (
    AssetPackageMismatchError,
    GateDecisionError,
    GateLedgerError,
    UnsatisfiedPrerequisiteError,
    UnknownStageError,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateDisposition,
    GateState,
)

VERSION = "2026.1"
TODAY = date(2026, 10, 2)
DATE_DUE = date(2026, 10, 16)


def canonical_assets(stage_number: int, version: str = VERSION) -> frozenset[AssetVersionRef]:
    template = stage_zero_to_ten_template(version)
    kinds = template.required_asset_kinds(stage_number)
    if not kinds:
        return frozenset({AssetVersionRef(f"stage-{stage_number}-asset", 1)})
    return frozenset(AssetVersionRef(kind, 1) for kind in kinds)


def passing(stage_number: int, version: str = VERSION) -> GateDecision:
    return GateDecision(
        stage_number=stage_number,
        template_version=version,
        required_assets=canonical_assets(stage_number, version),
        checkpoint_evidence=f"stage {stage_number} rubric passed",
        reviewer="client-approver-1",
        scope=f"stage-{stage_number + 1}-downstream",
        disposition=GateDisposition.APPROVED,
        rationale="reviewed against the checkpoint",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=DATE_DUE,
    )


def blocked(stage_number: int, version: str = VERSION) -> GateDecision:
    return GateDecision(
        stage_number=stage_number,
        template_version=version,
        required_assets=canonical_assets(stage_number, version),
        checkpoint_evidence="checkpoint failed",
        reviewer="client-approver-1",
        scope=f"stage-{stage_number + 1}-downstream",
        disposition=GateDisposition.BLOCKED,
        rationale="prerequisite incomplete",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=DATE_DUE,
    )


def approvable_gate(template, stage_number: int) -> StageGate:
    versions = {
        kind: 1 for kind in template.required_asset_kinds(stage_number)
    }
    gate = StageGate.from_template(template, stage_number, versions)
    gate.state = GateState.APPROVED
    gate.approved_assets = gate.required_assets
    gate.proposed_by = "specialist-1"
    gate.approver = "client-approver-1"
    return gate


class GateLedgerPrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.template = stage_zero_to_ten_template(VERSION)
        self.ledger = GateLedger(self.template)

    def test_records_a_passing_decision_for_a_stage_with_no_prerequisites(self):
        self.ledger.record(passing(0))

        self.assertTrue(self.ledger.has_passing_decision(0))
        self.assertEqual(passing(0), self.ledger.decision_for(0))

    def test_refuses_a_passing_decision_whose_prerequisite_is_absent(self):
        with self.assertRaises(UnsatisfiedPrerequisiteError):
            self.ledger.record(passing(1))

        self.assertFalse(self.ledger.has_passing_decision(1))
        self.assertIsNone(self.ledger.decision_for(1))

    def test_records_a_passing_decision_once_its_prerequisite_passes(self):
        self.ledger.record(passing(0))
        self.ledger.record(passing(1))

        self.assertTrue(self.ledger.has_passing_decision(1))

    def test_a_blocked_prerequisite_does_not_authorize_the_dependent_stage(self):
        self.ledger.record(blocked(0))

        with self.assertRaises(UnsatisfiedPrerequisiteError):
            self.ledger.record(passing(1))

    def test_a_later_non_passing_decision_revokes_the_passing_state(self):
        self.ledger.record(passing(0))
        self.ledger.record(blocked(0))

        self.assertFalse(self.ledger.has_passing_decision(0))
        with self.assertRaises(UnsatisfiedPrerequisiteError):
            self.ledger.record(passing(1))

    def test_record_refuses_a_decision_for_another_template_version(self):
        with self.assertRaises(GateLedgerError):
            self.ledger.record(passing(0, version="2025.9"))

    def test_record_refuses_a_stage_absent_from_the_template(self):
        with self.assertRaises(UnknownStageError):
            self.ledger.record(passing(99))

    def test_refuses_a_passing_decision_that_omits_a_canonical_asset_kind(self):
        under_declared = GateDecision(
            stage_number=0,
            template_version=VERSION,
            required_assets=frozenset({AssetVersionRef("client-record", 1)}),
            checkpoint_evidence="partial package",
            reviewer="client-approver-1",
            scope="stage-1-downstream",
            disposition=GateDisposition.APPROVED,
            rationale="self-declared smaller package",
            decided_on=TODAY,
            assigned_owner="production-manager",
            due_on=DATE_DUE,
        )

        with self.assertRaises(AssetPackageMismatchError):
            self.ledger.record(under_declared)

        self.assertFalse(self.ledger.has_passing_decision(0))

    def test_refuses_a_passing_decision_with_a_non_canonical_asset_kind(self):
        substituted = GateDecision(
            stage_number=0,
            template_version=VERSION,
            required_assets=canonical_assets(0)
            | frozenset({AssetVersionRef("made-up-asset", 1)}),
            checkpoint_evidence="substituted package",
            reviewer="client-approver-1",
            scope="stage-1-downstream",
            disposition=GateDisposition.APPROVED,
            rationale="self-declared substituted package",
            decided_on=TODAY,
            assigned_owner="production-manager",
            due_on=DATE_DUE,
        )

        with self.assertRaises(AssetPackageMismatchError):
            self.ledger.record(substituted)

        self.assertFalse(self.ledger.has_passing_decision(0))

    def test_records_a_passing_decision_whose_kinds_match_the_template(self):
        self.ledger.record(passing(0))

        self.assertTrue(self.ledger.has_passing_decision(0))


class GateLedgerDerivedStateTests(unittest.TestCase):
    def setUp(self):
        self.template = stage_zero_to_ten_template(VERSION)
        self.ledger = GateLedger(self.template)

    def test_dependency_states_are_derived_from_recorded_decisions(self):
        self.ledger.record(passing(0))

        states = self.ledger.dependency_states()

        self.assertIs(GateState.APPROVED, states[0])
        self.assertIs(GateState.NOT_STARTED, states[1])

    def test_dependency_states_reflect_a_non_passing_disposition(self):
        self.ledger.record(blocked(0))

        self.assertIs(GateState.BLOCKED, self.ledger.dependency_states()[0])

    def test_decision_history_is_append_only_and_immutable(self):
        self.ledger.record(passing(0))
        self.ledger.record(blocked(0))

        self.assertEqual(2, len(self.ledger.decisions_for(0)))
        self.assertIsInstance(self.ledger.decisions_for(0), tuple)

    def test_derived_states_drive_gate_integrity_and_ledger_recording(self):
        gate = approvable_gate(self.template, 1)

        with self.assertRaises(GateDecisionError):
            GateDecision.from_gate(
                gate,
                ledger=self.ledger,
                reviewer="client-approver-1",
                scope="stage-2-downstream",
                checkpoint_evidence="avatar rubric passed",
                disposition=GateDisposition.APPROVED,
                rationale="avatar locked",
                on=TODAY,
                assigned_owner="production-manager",
                due_on=DATE_DUE,
            )

        self.ledger.record(passing(0))
        decision = GateDecision.from_gate(
            gate,
            ledger=self.ledger,
            reviewer="client-approver-1",
            scope="stage-2-downstream",
            checkpoint_evidence="avatar rubric passed",
            disposition=GateDisposition.APPROVED,
            rationale="avatar locked",
            on=TODAY,
            assigned_owner="production-manager",
            due_on=DATE_DUE,
        )
        self.ledger.record(decision)

        self.assertTrue(self.ledger.has_passing_decision(1))


if __name__ == "__main__":
    unittest.main()
