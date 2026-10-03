"""Behavioral tests for the production-manager view query use case.

SPEC.md section 4 requires the production view to answer, for each client, the
current stage, what is present and approved, who is accountable, which dependency
blocks work and what approval is next; SPEC.md section 6 requires the use case
layer to compose the domain view and depend on ports rather than stores. The
handler under test loads the tenant's ``GateLedger`` and each stage's durable
``StageRun`` through the repositories and returns the pure domain
``EngagementProductionView``. These tests drive the real repository adapters and
a fake that reaches past the tenant boundary, so the query cannot launder a
foreign run or invent progress.
"""

import unittest
from datetime import date

from redops.contexts.governance.application.queries import (
    EngagementProductionViewQuery,
    GetEngagementProductionViewHandler,
)
from redops.contexts.governance.application.ports import StageRunRepository
from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    StageRun,
)
from redops.contexts.governance.domain.errors import StageRunProjectionError
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateDisposition,
    GateState,
    MetricReportingBasis,
    MetricReportingView,
)
from redops.contexts.governance.infrastructure.repositories import (
    InMemoryGateLedgerRepository,
    InMemoryStageRunRepository,
)

VERSION = "2026.1"
TODAY = date(2026, 10, 2)
TENANT = "tenant-3f"
ENGAGEMENT = "engagement-3f"


def approved_decision(stage_number: int) -> GateDecision:
    template = stage_zero_to_ten_template(VERSION)
    definition = template.definition_for(stage_number)
    scope = f"stage-{stage_number + 1}-downstream"
    assets = frozenset(
        AssetVersionRef(kind, 1)
        for kind in template.required_asset_kinds(stage_number)
    )
    approvals = []
    for asset in assets:
        request = ApprovalRequest(
            asset=asset,
            scope=scope,
            requested_by="specialist-1",
            approver="client-approver-1",
        )
        request.approve(actor="client-approver-1", on=TODAY)
        approvals.append(request)
    return GateDecision(
        stage_number=stage_number,
        template_version=VERSION,
        required_assets=assets,
        checkpoint=definition.checkpoint,
        checkpoint_evidence=f"stage {stage_number} rubric result",
        reviewer="client-approver-1",
        scope=scope,
        disposition=GateDisposition.APPROVED,
        rationale="recorded for the production view query",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=date(2026, 10, 16),
        dependencies=template.dependencies_of(stage_number),
        next_action=f"advance stage {stage_number + 1}",
        asset_approvals=tuple(approvals),
        tenant_id=TENANT,
    )


def working_run(stage_number: int, **overrides) -> StageRun:
    values = {
        "engagement": ENGAGEMENT,
        "stage_number": stage_number,
        "template_version": VERSION,
        "assigned_owner": "run-owner",
        "tenant_id": TENANT,
    }
    values.update(overrides)
    run = StageRun(**values)
    run.start(
        actor=values["assigned_owner"],
        reason="work began",
        on=TODAY,
        correlation_id="corr-1",
    )
    return run


def query(**overrides) -> EngagementProductionViewQuery:
    values = {
        "template": stage_zero_to_ten_template(VERSION),
        "engagement": ENGAGEMENT,
        "tenant_id": TENANT,
        "on": TODAY,
    }
    values.update(overrides)
    return EngagementProductionViewQuery(**values)


def handler(
    ledger_repository=None, run_repository=None
) -> GetEngagementProductionViewHandler:
    return GetEngagementProductionViewHandler(
        ledger_repository=ledger_repository or InMemoryGateLedgerRepository(),
        run_repository=run_repository or InMemoryStageRunRepository(),
    )


class ProductionViewQueryTests(unittest.TestCase):
    def test_empty_stores_report_every_stage_not_started(self):
        result = handler().handle(query())

        self.assertEqual(11, len(result.stages))
        self.assertIs(GateState.NOT_STARTED, result.stages[0].status)
        self.assertEqual(0, result.current_stage.stage_number)
        self.assertEqual(0, result.progress.approved_gates)
        self.assertEqual(TENANT, result.tenant_id)
        self.assertEqual(ENGAGEMENT, result.engagement)

    def test_an_approved_gate_and_a_working_run_are_both_projected(self):
        ledgers = InMemoryGateLedgerRepository()
        ledgers.append(approved_decision(0))
        runs = InMemoryStageRunRepository()
        runs.save(working_run(1, assigned_owner="stage-1-owner"))

        result = handler(ledgers, runs).handle(query())

        stage0 = result.stage_by_number(0)
        self.assertIs(GateState.APPROVED, stage0.status)
        self.assertEqual("production-manager", stage0.assigned_owner)
        stage1 = result.stage_by_number(1)
        self.assertIs(GateState.WORKING, stage1.status)
        self.assertEqual("stage-1-owner", stage1.assigned_owner)
        self.assertEqual(TODAY, stage1.entered_at)
        self.assertEqual(1, result.current_stage.stage_number)

    def test_a_run_is_loaded_for_every_stage_the_template_defines(self):
        runs = InMemoryStageRunRepository()
        runs.save(working_run(5, assigned_owner="stage-5-owner"))

        stage5 = handler(run_repository=runs).handle(query()).stage_by_number(5)

        self.assertIs(GateState.WORKING, stage5.status)
        self.assertEqual("stage-5-owner", stage5.assigned_owner)

    def test_a_run_from_another_tenant_is_not_read_into_this_view(self):
        runs = InMemoryStageRunRepository()
        runs.save(working_run(0, tenant_id="other-client", engagement=ENGAGEMENT))

        stage0 = handler(run_repository=runs).handle(query()).stage_by_number(0)

        self.assertIs(GateState.NOT_STARTED, stage0.status)
        self.assertIsNone(stage0.assigned_owner)

    def test_milestones_activity_and_metrics_pass_through_unchanged(self):
        metrics = (
            MetricReportingView(
                metric_id="metric-cost-per-lead",
                tenant_id=TENANT,
                name="cost per lead",
                funnel_step="lead",
                unit="currency",
                direction="lower_is_better",
                value=12.0,
                window_start=date(2026, 9, 18),
                window_end=date(2026, 10, 1),
                sample_size=250,
                source="analytics://campaign-report",
                recorded_on=TODAY,
                basis=MetricReportingBasis.OBSERVED,
            ),
        )

        result = handler().handle(
            query(
                verified_post_launch_milestones=2,
                activity_entries=7,
                metric_reporting=metrics,
            )
        )

        self.assertEqual(2, result.progress.verified_post_launch_milestones)
        self.assertEqual(7, result.progress.activity_entries)
        self.assertEqual(metrics, result.metric_reporting)

    def test_a_repository_returning_a_foreign_run_is_refused(self):
        class ForeignRunRepository(StageRunRepository):
            def load(self, template_version, engagement, stage_number, tenant_id):
                if stage_number == 0:
                    return working_run(0, tenant_id="other-client")
                return None

            def save(self, run):
                raise AssertionError("the query must not write")

        with self.assertRaises(StageRunProjectionError):
            handler(run_repository=ForeignRunRepository()).handle(query())


if __name__ == "__main__":
    unittest.main()
