"""Behavioral tests for persisted canonical prerequisites on the gate record.

SPEC.md section 4 ("Gate record and production manager view") requires every
stage to persist "template version, required assets and their exact versions,
checkpoint rubric, ... dependencies, blockers ..." and the production view to
answer "which dependency blocks work". The canonical prerequisite graph lives on
``StageDefinition.dependencies`` and the durable ``GateDecision`` is the record
of the stage decision. Before this change a durable decision did not persist the
prerequisites it rested on, so a decision read in isolation could not name the
dependency that blocks dependent work; only the in-memory ``GateLedger``, which
holds the template, could recover the chain. The prerequisites are a property of
the stage for every disposition, not only of a passing decision, so the ledger
must verify them against the template for every decision it records.
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
    StageGate,
)
from redops.contexts.governance.domain.errors import PrerequisiteMismatchError
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


def canonical_assets(stage_number):
    return frozenset(
        AssetVersionRef(kind, 1)
        for kind in TEMPLATE.required_asset_kinds(stage_number)
    )


def decision_for(
    stage_number,
    *,
    disposition=GateDisposition.APPROVED,
    dependencies=None,
    **overrides,
):
    definition = TEMPLATE.definition_for(stage_number)
    assets = canonical_assets(stage_number)
    scope = f"stage-{stage_number + 1}-downstream"
    if dependencies is None:
        dependencies = definition.dependencies
    values = {
        "stage_number": stage_number,
        "template_version": VERSION,
        "required_assets": assets,
        "checkpoint": definition.checkpoint,
        "checkpoint_evidence": f"stage {stage_number} rubric passed",
        "reviewer": "client-approver-1",
        "scope": scope,
        "disposition": disposition,
        "rationale": "reviewed against the canonical checkpoint",
        "decided_on": TODAY,
        "assigned_owner": "production-manager",
        "due_on": DATE_DUE,
        "dependencies": dependencies,
        "asset_approvals": tuple(approvals(assets, scope)),
    }
    values.update(overrides)
    return GateDecision(**values)


def ledger_through(stage_number):
    ledger = GateLedger(TEMPLATE)
    for stage in range(stage_number):
        ledger.record(decision_for(stage))
    return ledger


def stage7_gate():
    versions = {kind: 1 for kind in TEMPLATE.required_asset_kinds(7)}
    gate = StageGate.from_template(TEMPLATE, 7, versions)
    gate.state = GateState.APPROVED
    gate.proposed_by = "specialist-1"
    gate.approver = "client-approver-1"
    for request in approvals(gate.required_assets, "stage-8-funnel-integration"):
        gate.record_asset_approval(request)
    return gate


class GateDecisionPrerequisitePersistenceTests(unittest.TestCase):
    def test_decision_persists_the_canonical_prerequisites_for_its_stage(self):
        decision = decision_for(7)

        self.assertEqual(frozenset({6}), decision.dependencies)

    def test_stage_zero_decision_persists_no_prerequisites(self):
        decision = decision_for(0)

        self.assertEqual(frozenset(), decision.dependencies)

    def test_non_passing_decision_also_persists_the_prerequisites(self):
        for disposition in (
            GateDisposition.BLOCKED,
            GateDisposition.CHANGES_REQUIRED,
            GateDisposition.SUPERSEDED,
        ):
            with self.subTest(disposition=disposition):
                decision = decision_for(
                    7,
                    disposition=disposition,
                    asset_approvals=(),
                )

                self.assertEqual(frozenset({6}), decision.dependencies)

    def test_factory_persists_the_gates_canonical_prerequisites(self):
        decision = GateDecision.from_gate(
            stage7_gate(),
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

        self.assertEqual(frozenset({6}), decision.dependencies)


class GateLedgerPrerequisiteRecordTests(unittest.TestCase):
    def test_ledger_refuses_a_decision_that_omits_a_canonical_prerequisite(self):
        ledger = ledger_through(7)

        with self.assertRaises(PrerequisiteMismatchError):
            ledger.record(decision_for(7, dependencies=frozenset()))

        self.assertIsNone(ledger.decision_for(7))

    def test_ledger_refuses_a_decision_naming_a_foreign_prerequisite(self):
        ledger = ledger_through(7)

        with self.assertRaises(PrerequisiteMismatchError):
            ledger.record(decision_for(7, dependencies=frozenset({5})))

        self.assertIsNone(ledger.decision_for(7))

    def test_ledger_refuses_an_extra_prerequisite(self):
        ledger = ledger_through(7)

        with self.assertRaises(PrerequisiteMismatchError):
            ledger.record(decision_for(7, dependencies=frozenset({5, 6})))

        self.assertIsNone(ledger.decision_for(7))

    def test_every_disposition_must_carry_the_canonical_prerequisites(self):
        for disposition in (
            GateDisposition.BLOCKED,
            GateDisposition.CHANGES_REQUIRED,
            GateDisposition.WAIVED,
            GateDisposition.SUPERSEDED,
        ):
            with self.subTest(disposition=disposition):
                ledger = ledger_through(7)
                values = {"dependencies": frozenset()}
                if disposition is GateDisposition.WAIVED:
                    from redops.contexts.governance.domain.value_objects import Waiver

                    values["waiver"] = Waiver(
                        reason="video delayed by vendor",
                        risk_owner="production-manager",
                        review_trigger="vendor delivery",
                        downstream_effects=frozenset(
                            {"stage-8-funnel-integration"}
                        ),
                    )
                    values["scope"] = "stage-8-funnel-integration"
                else:
                    values["asset_approvals"] = ()

                with self.assertRaises(PrerequisiteMismatchError):
                    ledger.record(
                        decision_for(7, disposition=disposition, **values)
                    )

                self.assertIsNone(ledger.decision_for(7))

    def test_ledger_records_a_decision_with_the_canonical_prerequisites(self):
        ledger = ledger_through(7)

        ledger.record(
            decision_for(7, disposition=GateDisposition.BLOCKED, asset_approvals=())
        )

        recorded = ledger.decision_for(7)
        self.assertIsNotNone(recorded)
        self.assertEqual(frozenset({6}), recorded.dependencies)
        self.assertFalse(ledger.has_passing_decision(7, on=TODAY))

    def test_recorded_decision_names_the_dependency_read_in_isolation(self):
        ledger = ledger_through(7)
        ledger.record(
            decision_for(7, disposition=GateDisposition.BLOCKED, asset_approvals=())
        )

        self.assertEqual(frozenset({6}), ledger.decision_for(7).dependencies)


if __name__ == "__main__":
    unittest.main()
