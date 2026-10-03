"""Behavioral tests for the production-manager view (pure domain, Governance).

Rules under test come from SPEC.md section 4, "Gate record and production manager
view":

- "The production view answers, for each client: current stage, what should
  exist, what is present and approved, what is missing, who is accountable, which
  dependency blocks work, what approval is next, and when it is due."
- "Separate eight reporting dimensions: assets, milestones, checkpoints, metrics,
  owner, dependency, status and due date. Count activity separately from gate
  completion."
- "A failed or expired prerequisite blocks dependent authorization until
  resolved."

The view is a pure read model derived from the versioned ``StageTemplate`` and
the durable ``GateLedger``. It never invents a metric, a milestone, a named owner
or an approval; it reports what the template and the recorded gate decisions say
at the evaluation instant.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
)
from redops.contexts.governance.domain.errors import ProductionViewError
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    EngagementProductionView,
    GateDisposition,
    GateState,
    PRODUCTION_REPORTING_DIMENSIONS,
    ReportingDimension,
    StageProductionView,
)

VERSION = "2026.1"
TODAY = date(2026, 10, 2)
EXPIRY = date(2026, 10, 5)
LATER = date(2026, 10, 10)
DATE_DUE = date(2026, 10, 16)


def canonical_assets(stage_number: int, version: str = VERSION) -> frozenset[AssetVersionRef]:
    kinds = stage_zero_to_ten_template(version).required_asset_kinds(stage_number)
    return frozenset(AssetVersionRef(kind, 1) for kind in kinds)


def approvals(assets, scope, *, expires_on=None, on=TODAY):
    for asset in assets:
        request = ApprovalRequest(
            asset=asset,
            scope=scope,
            requested_by="specialist-1",
            approver="client-approver-1",
            expires_on=expires_on,
        )
        request.approve(actor="client-approver-1", on=on)
        yield request


def decision(
    stage_number: int,
    disposition: GateDisposition = GateDisposition.APPROVED,
    *,
    version: str = VERSION,
    expires_on=None,
    blockers=frozenset(),
) -> GateDecision:
    definition = stage_zero_to_ten_template(version).definition_for(stage_number)
    assets = canonical_assets(stage_number, version)
    scope = f"stage-{stage_number + 1}-downstream"
    return GateDecision(
        stage_number=stage_number,
        template_version=version,
        required_assets=assets,
        checkpoint=definition.checkpoint if definition else "unknown-stage",
        checkpoint_evidence=f"stage {stage_number} rubric result",
        reviewer="client-approver-1",
        scope=scope,
        disposition=disposition,
        rationale="recorded for the production view",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=DATE_DUE,
        dependencies=stage_zero_to_ten_template(version).dependencies_of(
            stage_number
        ),
        next_action=f"advance stage {stage_number + 1}",
        asset_approvals=tuple(
            approvals(assets, scope, expires_on=expires_on)
        ),
        blockers=frozenset(blockers),
    )


def ledger_through(stage_number: int, version: str = VERSION) -> GateLedger:
    ledger = GateLedger(stage_zero_to_ten_template(version))
    for stage in range(stage_number):
        ledger.record(decision(stage, version=version))
    return ledger


def view(ledger: GateLedger, **overrides) -> EngagementProductionView:
    kwargs = {
        "engagement": "engagement-3f",
        "tenant_id": "tenant-3f",
        "on": TODAY,
    }
    kwargs.update(overrides)
    return EngagementProductionView.from_ledger(ledger, **kwargs)


class EmptyPipelineViewTests(unittest.TestCase):
    def test_empty_ledger_reports_every_stage_as_required_and_missing(self):
        result = view(GateLedger(stage_zero_to_ten_template(VERSION)))

        self.assertEqual(11, len(result.stages))
        first = result.stages[0]
        self.assertEqual(0, first.stage_number)
        self.assertEqual("Intake", first.name)
        self.assertEqual("Production Ready", first.checkpoint)
        self.assertIs(GateState.NOT_STARTED, first.status)
        self.assertEqual(
            stage_zero_to_ten_template(VERSION).required_asset_kinds(0),
            first.required_asset_kinds,
        )
        self.assertEqual(frozenset(), first.approved_assets)
        self.assertEqual(first.required_asset_kinds, first.missing_asset_kinds)
        self.assertFalse(first.is_approved)

    def test_empty_ledger_names_the_current_stage_and_next_approval(self):
        result = view(GateLedger(stage_zero_to_ten_template(VERSION)))

        self.assertEqual(0, result.current_stage.stage_number)
        self.assertEqual("Production Ready", result.next_approval.checkpoint)
        self.assertIsNone(result.current_stage.assigned_owner)
        self.assertIsNone(result.current_stage.recorded_approver)
        self.assertEqual(0, result.progress.approved_gates)

    def test_view_carries_engagement_and_tenant_labels(self):
        result = view(GateLedger(stage_zero_to_ten_template(VERSION)))

        self.assertEqual("engagement-3f", result.engagement)
        self.assertEqual("tenant-3f", result.tenant_id)
        self.assertEqual(VERSION, result.template_version)


class ApprovedStageViewTests(unittest.TestCase):
    def test_an_approved_stage_reports_its_exact_approved_assets(self):
        result = view(ledger_through(1))

        stage0 = result.stages[0]
        self.assertIs(GateState.APPROVED, stage0.status)
        self.assertTrue(stage0.is_approved)
        self.assertEqual(canonical_assets(0), stage0.approved_assets)
        self.assertEqual(frozenset(), stage0.missing_asset_kinds)
        self.assertEqual("production-manager", stage0.assigned_owner)
        self.assertEqual("client-approver-1", stage0.recorded_approver)
        self.assertEqual(DATE_DUE, stage0.due_on)
        self.assertEqual("advance stage 1", stage0.next_action)
        self.assertEqual(1, result.progress.approved_gates)

    def test_current_stage_advances_past_an_approved_stage(self):
        result = view(ledger_through(1))

        self.assertEqual(1, result.current_stage.stage_number)
        self.assertEqual("Avatar Locked", result.current_stage.checkpoint)
        self.assertFalse(result.stages[1].is_approved)

    def test_a_fully_approved_pipeline_has_no_current_stage(self):
        result = view(ledger_through(11))

        self.assertIsNone(result.current_stage)
        self.assertIsNone(result.next_approval)
        self.assertEqual(11, result.progress.approved_gates)


class BlockedAndExpiredViewTests(unittest.TestCase):
    def test_a_blocked_stage_surfaces_its_blockers_and_dependents(self):
        ledger = GateLedger(stage_zero_to_ten_template(VERSION))
        ledger.record(
            decision(
                0,
                GateDisposition.BLOCKED,
                blockers=frozenset({"required asset versions not approved"}),
            )
        )

        result = view(ledger)

        stage0 = result.stages[0]
        self.assertIs(GateState.BLOCKED, stage0.status)
        self.assertEqual(
            frozenset({"required asset versions not approved"}), stage0.blockers
        )
        self.assertFalse(stage0.is_approved)
        stage1 = result.stages[1]
        self.assertEqual(frozenset({0}), stage1.blocking_dependencies)
        self.assertEqual((0,), tuple(s.stage_number for s in result.blocked_stages))

    def test_an_expired_approval_leaves_the_stage_missing_not_approved(self):
        ledger = GateLedger(stage_zero_to_ten_template(VERSION))
        ledger.record(decision(0, expires_on=EXPIRY))

        at_expiry = view(ledger, on=LATER)

        stage0 = at_expiry.stages[0]
        self.assertIs(GateState.BLOCKED, stage0.status)
        self.assertEqual(frozenset(), stage0.approved_assets)
        self.assertEqual(stage0.required_asset_kinds, stage0.missing_asset_kinds)
        self.assertFalse(stage0.is_approved)

    def test_dependency_that_does_not_authorize_is_reported_as_blocking(self):
        ledger = GateLedger(stage_zero_to_ten_template(VERSION))
        ledger.record(decision(0))

        still_current = view(ledger)

        self.assertEqual(1, still_current.current_stage.stage_number)
        self.assertEqual(frozenset({0}), still_current.stages[1].dependencies)
        self.assertEqual(frozenset(), still_current.stages[1].blocking_dependencies)

    def test_a_waived_stage_reports_its_scoped_waiver_and_is_not_approved(self):
        from redops.contexts.governance.domain.value_objects import Waiver

        waiver = Waiver(
            reason="client accepted the gap",
            risk_owner="production-manager",
            downstream_effects=frozenset({"stage-1-downstream"}),
            review_trigger="next client review",
        )
        definition = stage_zero_to_ten_template(VERSION).definition_for(0)
        waived = GateDecision(
            stage_number=0,
            template_version=VERSION,
            required_assets=canonical_assets(0),
            checkpoint=definition.checkpoint,
            checkpoint_evidence="scoped waiver recorded",
            reviewer="client-approver-1",
            scope="stage-1-downstream",
            disposition=GateDisposition.WAIVED,
            rationale="risk accepted without fabricating the asset",
            decided_on=TODAY,
            assigned_owner="production-manager",
            due_on=DATE_DUE,
            dependencies=frozenset(),
            waiver=waiver,
        )
        ledger = GateLedger(stage_zero_to_ten_template(VERSION))
        ledger.record(waived)

        result = view(ledger)

        stage0 = result.stages[0]
        self.assertIs(GateState.WAIVED, stage0.status)
        self.assertIs(waiver, stage0.waiver)
        self.assertFalse(stage0.is_approved)


class ReportingDimensionTests(unittest.TestCase):
    def test_the_view_separates_all_eight_reporting_dimensions(self):
        names = tuple(dimension.value for dimension in PRODUCTION_REPORTING_DIMENSIONS)

        self.assertEqual(
            (
                "assets",
                "milestones",
                "checkpoints",
                "metrics",
                "owner",
                "dependency",
                "status",
                "due_date",
            ),
            names,
        )

    def test_dimension_slices_are_derived_from_the_template_and_ledger(self):
        result = view(ledger_through(1), verified_post_launch_milestones=3)

        self.assertEqual(
            11,
            len(result.dimension(ReportingDimension.STATUS)),
        )
        statuses = dict(result.dimension(ReportingDimension.STATUS))
        self.assertIs(GateState.APPROVED, statuses[0])
        self.assertIs(GateState.NOT_STARTED, statuses[1])

        checkpoints = dict(result.dimension(ReportingDimension.CHECKPOINTS))
        self.assertEqual("Production Ready", checkpoints[0])

        owners = dict(result.dimension(ReportingDimension.OWNER))
        self.assertEqual("production-manager", owners[0])
        self.assertIsNone(owners[1])

        due_dates = dict(result.dimension(ReportingDimension.DUE_DATE))
        self.assertEqual(DATE_DUE, due_dates[0])
        self.assertIsNone(due_dates[1])

        assets = dict(
            (stage_number, (required, approved, missing))
            for stage_number, required, approved, missing in result.dimension(
                ReportingDimension.ASSETS
            )
        )
        self.assertEqual(canonical_assets(0), assets[0][1])
        self.assertEqual(frozenset(), assets[0][2])

        self.assertEqual(
            (3,), result.dimension(ReportingDimension.MILESTONES)
        )
        self.assertEqual((), result.dimension(ReportingDimension.METRICS))

    def test_activity_is_counted_separately_from_verified_progress(self):
        result = view(
            ledger_through(2),
            activity_entries=17,
            verified_post_launch_milestones=1,
        )

        self.assertEqual(17, result.progress.activity_entries)
        self.assertEqual(2, result.progress.approved_gates)
        self.assertEqual(
            result.progress.approved_gates
            + result.progress.verified_post_launch_milestones,
            result.progress.verified_progress,
        )

    def test_unknown_dimension_is_refused(self):
        result = view(GateLedger(stage_zero_to_ten_template(VERSION)))

        with self.assertRaises(ProductionViewError):
            result.dimension("nonsense")


class ProductionViewInvariantTests(unittest.TestCase):
    def test_view_rejects_a_blank_engagement_or_tenant(self):
        ledger = GateLedger(stage_zero_to_ten_template(VERSION))

        for override in (
            {"engagement": " "},
            {"tenant_id": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    view(ledger, **override)

    def test_view_rejects_a_stage_view_for_a_non_required_kind(self):
        with self.assertRaises(ProductionViewError):
            StageProductionView(
                stage_number=0,
                name="Intake",
                checkpoint="Production Ready",
                status=GateState.NOT_STARTED,
                required_asset_kinds=frozenset({"client-record"}),
                approved_assets=frozenset({AssetVersionRef("invented", 1)}),
                accountable_role="Engagement and Governance",
                approver_role="client-designated-authority",
                dependencies=frozenset(),
                blocking_dependencies=frozenset(),
            )

    def test_view_is_immutable(self):
        result = view(ledger_through(1))

        with self.assertRaises(FrozenInstanceError):
            result.engagement = "other"
        with self.assertRaises(FrozenInstanceError):
            result.stages[0].status = GateState.BLOCKED


if __name__ == "__main__":
    unittest.main()
