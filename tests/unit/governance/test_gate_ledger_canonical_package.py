"""Behavioral tests for canonical gate packages on every ledger disposition.

SPEC.md section 4: "For every stage, persist template version, required assets
and their exact versions, checkpoint rubric, ... gate state ...". The durable
``GateDecision`` is that record, and the canonical 0-10 template is the only
source of a stage's required asset package and checkpoint. The ``GateLedger``
already refuses a *passing* decision that diverges from the template; a
BLOCKED, CHANGES_REQUIRED, WAIVED or SUPERSEDED decision could previously pin a
non-canonical package or the wrong checkpoint, so the production manager view
could show what should exist for one stage while the durable record named a
different set. The canonical package and checkpoint are properties of the
stage, not of a passing disposition, so the ledger must enforce them for every
decision it records.
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
)
from redops.contexts.governance.domain.errors import (
    AssetPackageMismatchError,
    CheckpointMismatchError,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateDisposition,
    Waiver,
)

VERSION = "2026.1"
TODAY = date(2026, 10, 2)
DATE_DUE = date(2026, 10, 16)
STAGE = 7
TEMPLATE = stage_zero_to_ten_template(VERSION)
SCOPE = "stage-8-funnel-integration"
NON_PASSING = (
    GateDisposition.BLOCKED,
    GateDisposition.CHANGES_REQUIRED,
    GateDisposition.SUPERSEDED,
)


def canonical_assets(stage_number: int = STAGE) -> frozenset[AssetVersionRef]:
    return frozenset(
        AssetVersionRef(kind, 1)
        for kind in TEMPLATE.required_asset_kinds(stage_number)
    )


def canonical_decision(stage_number: int = STAGE) -> GateDecision:
    assets = canonical_assets(stage_number)
    scope = f"stage-{stage_number + 1}-downstream"
    requests = []
    for asset in assets:
        request = ApprovalRequest(
            asset=asset,
            scope=scope,
            requested_by="specialist-1",
            approver="client-approver-1",
        )
        request.approve(actor="client-approver-1", on=TODAY)
        requests.append(request)
    definition = TEMPLATE.definition_for(stage_number)
    return GateDecision(
        stage_number=stage_number,
        template_version=VERSION,
        required_assets=assets,
        checkpoint=definition.checkpoint,
        checkpoint_evidence="rubric passed",
        reviewer="client-approver-1",
        scope=scope,
        disposition=GateDisposition.APPROVED,
        rationale="reviewed against the canonical checkpoint",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=DATE_DUE,
        asset_approvals=tuple(requests),
    )


def non_passing_decision(
    disposition: GateDisposition,
    *,
    assets: frozenset[AssetVersionRef] | None = None,
    checkpoint: str | None = None,
) -> GateDecision:
    definition = TEMPLATE.definition_for(STAGE)
    values = {
        "stage_number": STAGE,
        "template_version": VERSION,
        "required_assets": canonical_assets() if assets is None else assets,
        "checkpoint": definition.checkpoint if checkpoint is None else checkpoint,
        "checkpoint_evidence": "disposition recorded against the stage package",
        "reviewer": "client-approver-1",
        "scope": SCOPE,
        "disposition": disposition,
        "rationale": "recording the stage state for the production manager view",
        "decided_on": TODAY,
        "assigned_owner": "production-manager",
        "due_on": DATE_DUE,
    }
    if disposition is GateDisposition.WAIVED:
        values["waiver"] = Waiver(
            reason="video delayed by vendor",
            risk_owner="production-manager",
            review_trigger="vendor delivery",
            downstream_effects=frozenset({SCOPE}),
        )
    return GateDecision(**values)


def ledger_through(stage_number: int = STAGE) -> GateLedger:
    ledger = GateLedger(TEMPLATE)
    for stage in range(stage_number):
        ledger.record(canonical_decision(stage))
    return ledger


class GateLedgerCanonicalPackageTests(unittest.TestCase):
    def test_every_disposition_refuses_a_non_canonical_asset_kind(self):
        for disposition in (*NON_PASSING, GateDisposition.WAIVED):
            with self.subTest(disposition=disposition):
                ledger = ledger_through()
                foreign = frozenset({AssetVersionRef("made-up-asset", 1)})

                with self.assertRaises(AssetPackageMismatchError):
                    ledger.record(
                        non_passing_decision(disposition, assets=foreign)
                    )

                self.assertIsNone(ledger.decision_for(STAGE))

    def test_every_disposition_refuses_a_package_missing_a_canonical_kind(self):
        for disposition in (*NON_PASSING, GateDisposition.WAIVED):
            with self.subTest(disposition=disposition):
                ledger = ledger_through()
                partial = frozenset(
                    {AssetVersionRef("authority-amplifier-script", 1)}
                )

                with self.assertRaises(AssetPackageMismatchError):
                    ledger.record(
                        non_passing_decision(disposition, assets=partial)
                    )

                self.assertIsNone(ledger.decision_for(STAGE))

    def test_every_disposition_refuses_a_non_canonical_checkpoint(self):
        for disposition in (*NON_PASSING, GateDisposition.WAIVED):
            with self.subTest(disposition=disposition):
                ledger = ledger_through()

                with self.assertRaises(CheckpointMismatchError):
                    ledger.record(
                        non_passing_decision(
                            disposition, checkpoint="Some Other Rubric"
                        )
                    )

                self.assertIsNone(ledger.decision_for(STAGE))

    def test_a_non_passing_decision_matching_the_template_is_recorded(self):
        for disposition in NON_PASSING:
            with self.subTest(disposition=disposition):
                ledger = ledger_through()

                ledger.record(non_passing_decision(disposition))

                recorded = ledger.decision_for(STAGE)
                self.assertIsNotNone(recorded)
                self.assertEqual(canonical_assets(), recorded.required_assets)
                self.assertFalse(ledger.has_passing_decision(STAGE, on=TODAY))


if __name__ == "__main__":
    unittest.main()
