"""Behavioral tests for verified pipeline progress (pure domain, Governance).

Rules under test come from SPEC.md section 4:

- "Count activity separately from gate completion. Display progress as approved
  gates and verified post launch milestones, never as tasks checked off."
- "Stage completion requires gate acceptance, not merely activity."

The value reports progress only from passing GateDecisions recorded in the
durable GateLedger plus caller-supplied verified post-launch milestones.
Activity, blocked, changes-required and waived states never add to verified
progress because they do not authorize downstream work.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateDisposition,
    PipelineProgress,
)

VERSION = "2026.1"
TODAY = date(2026, 10, 2)
DATE_DUE = date(2026, 10, 16)


def canonical_assets(stage_number: int) -> frozenset[AssetVersionRef]:
    kinds = stage_zero_to_ten_template(VERSION).required_asset_kinds(stage_number)
    return frozenset(AssetVersionRef(kind, 1) for kind in kinds)


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


def decision(stage_number: int, disposition: GateDisposition) -> GateDecision:
    definition = stage_zero_to_ten_template(VERSION).definition_for(stage_number)
    assets = canonical_assets(stage_number)
    scope = f"stage-{stage_number + 1}-downstream"
    return GateDecision(
        stage_number=stage_number,
        template_version=VERSION,
        required_assets=assets,
        checkpoint=definition.checkpoint if definition else "unknown",
        checkpoint_evidence="rubric result",
        reviewer="client-approver-1",
        scope=scope,
        disposition=disposition,
        rationale="recorded for progress reporting",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=DATE_DUE,
        asset_approvals=tuple(approvals(assets, scope)),
    )


def ledger_through(stage_number: int) -> GateLedger:
    ledger = GateLedger(stage_zero_to_ten_template(VERSION))
    for stage in range(stage_number):
        ledger.record(decision(stage, GateDisposition.APPROVED))
    return ledger


class PipelineProgressDerivationTests(unittest.TestCase):
    def test_empty_pipeline_reports_no_verified_progress(self):
        progress = PipelineProgress.from_ledger(
            GateLedger(stage_zero_to_ten_template(VERSION)), on=TODAY
        )

        self.assertEqual(0, progress.approved_gates)
        self.assertEqual(0, progress.verified_progress)
        self.assertEqual(
            len(stage_zero_to_ten_template(VERSION).stages),
            progress.total_gates,
        )

    def test_an_approved_gate_adds_to_verified_progress(self):
        progress = PipelineProgress.from_ledger(ledger_through(1), on=TODAY)

        self.assertEqual(1, progress.approved_gates)
        self.assertEqual(1, progress.verified_progress)
        self.assertEqual(
            len(stage_zero_to_ten_template(VERSION).stages) - 1,
            progress.gates_remaining,
        )

    def test_activity_is_counted_separately_and_never_adds_progress(self):
        progress = PipelineProgress.from_ledger(
            ledger_through(2),
            on=TODAY,
            activity_entries=17,
        )

        self.assertEqual(2, progress.verified_progress)
        self.assertEqual(2, progress.approved_gates)
        self.assertEqual(17, progress.activity_entries)

    def test_blocked_and_changes_required_do_not_count_as_approved_gates(self):
        for disposition in (
            GateDisposition.BLOCKED,
            GateDisposition.CHANGES_REQUIRED,
            GateDisposition.SUPERSEDED,
        ):
            with self.subTest(disposition=disposition):
                ledger = GateLedger(stage_zero_to_ten_template(VERSION))
                ledger.record(decision(0, disposition))

                progress = PipelineProgress.from_ledger(ledger, on=TODAY)

                self.assertEqual(0, progress.approved_gates)
                self.assertEqual(0, progress.verified_progress)

    def test_a_later_non_passing_decision_revokes_the_approved_gate(self):
        ledger = GateLedger(stage_zero_to_ten_template(VERSION))
        ledger.record(decision(0, GateDisposition.APPROVED))
        ledger.record(decision(0, GateDisposition.CHANGES_REQUIRED))

        progress = PipelineProgress.from_ledger(ledger, on=TODAY)

        self.assertEqual(0, progress.approved_gates)
        self.assertEqual(0, progress.verified_progress)

    def test_verified_post_launch_milestones_add_to_progress_not_gates(self):
        progress = PipelineProgress.from_ledger(
            ledger_through(11),
            on=TODAY,
            verified_post_launch_milestones=2,
        )

        self.assertEqual(11, progress.approved_gates)
        self.assertEqual(2, progress.verified_post_launch_milestones)
        self.assertEqual(13, progress.verified_progress)


class PipelineProgressInvariantTests(unittest.TestCase):
    def test_progress_rejects_negative_inputs(self):
        for override in (
            {"approved_gates": -1},
            {"total_gates": -1},
            {"verified_post_launch_milestones": -1},
            {"activity_entries": -1},
        ):
            with self.subTest(override=override):
                values = {
                    "approved_gates": 0,
                    "total_gates": 11,
                    "verified_post_launch_milestones": 0,
                    "activity_entries": 0,
                }
                values.update(override)
                with self.assertRaises(ValueError):
                    PipelineProgress(**values)

    def test_approved_gates_cannot_exceed_total_gates(self):
        with self.assertRaises(ValueError):
            PipelineProgress(approved_gates=12, total_gates=11)

    def test_progress_is_immutable(self):
        progress = PipelineProgress(approved_gates=1, total_gates=11)

        with self.assertRaises(FrozenInstanceError):
            progress.approved_gates = 2


if __name__ == "__main__":
    unittest.main()
