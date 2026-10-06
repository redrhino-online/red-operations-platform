"""HTTP-boundary behavioral tests for the production-manager view route.

SPEC.md section 4 requires a production view that answers, for each client, the
current stage, what is present and approved, what is missing, who is accountable,
which dependency blocks work, what approval is next and when it is due, and
separates the eight reporting dimensions; SPEC.md section 6 requires the API to
call the application use case through ports and never read a store directly.
These tests drive the real FastAPI app, the real query use case and the real
tenant-scoped repositories (substituted with fresh in-memory adapters), so the
route cannot bypass the domain projection or the tenant boundary.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest
from datetime import date

TENANT = "client-3f"
OTHER_TENANT = "client-other"
ENGAGEMENT = "ws-3f"
VERSION = "2026.1"
ON = date(2026, 10, 2)
TODAY = date(2026, 10, 2)


class ProductionViewRouteTests(unittest.TestCase):
    """The production view is served only through the use case and its ports."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import (
                get_gate_ledger_repository,
                get_stage_run_repository,
                get_umbrella_plan_repository,
            )
            from redops.contexts.governance.infrastructure.repositories import (
                InMemoryGateLedgerRepository,
                InMemoryStageRunRepository,
            )
            from redops.contexts.portfolio.infrastructure.repositories import (
                InMemoryUmbrellaPlanRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.ledger_dependency = staticmethod(get_gate_ledger_repository)
        cls.run_dependency = staticmethod(get_stage_run_repository)
        cls.umbrella_dependency = staticmethod(get_umbrella_plan_repository)
        cls.ledger_class = staticmethod(InMemoryGateLedgerRepository)
        cls.run_class = staticmethod(InMemoryStageRunRepository)
        cls.umbrella_class = staticmethod(InMemoryUmbrellaPlanRepository)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.ledger = self.ledger_class()
        self.runs = self.run_class()
        self.umbrella_plans = self.umbrella_class()
        self.app.dependency_overrides[self.ledger_dependency] = lambda: self.ledger
        self.app.dependency_overrides[self.run_dependency] = lambda: self.runs
        self.app.dependency_overrides[self.umbrella_dependency] = (
            lambda: self.umbrella_plans
        )
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def url(self, tenant_id: str = TENANT) -> str:
        return (
            f"/red/clients/{tenant_id}/engagements/{ENGAGEMENT}/production-view"
        )

    @staticmethod
    def approved_decision(stage_number: int):
        from redops.contexts.governance.domain.entities import (
            ApprovalRequest,
            GateDecision,
        )
        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )
        from redops.contexts.governance.domain.value_objects import (
            AssetVersionRef,
            GateDisposition,
        )

        template = stage_zero_to_ten_template(VERSION)
        definition = template.definition_for(stage_number)
        scope = f"stage-{stage_number}-downstream"
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
            rationale="recorded for the production view route",
            decided_on=TODAY,
            assigned_owner="production-manager",
            due_on=date(2026, 10, 16),
            dependencies=template.dependencies_of(stage_number),
            next_action=f"advance stage {stage_number + 1}",
            asset_approvals=tuple(approvals),
            tenant_id=TENANT,
        )

    def working_run(self, stage_number: int, owner: str):
        from redops.contexts.governance.domain.entities import StageRun

        run = StageRun(
            engagement=ENGAGEMENT,
            stage_number=stage_number,
            template_version=VERSION,
            assigned_owner=owner,
            tenant_id=TENANT,
        )
        run.start(
            actor=owner,
            reason="work began",
            on=TODAY,
            correlation_id="corr-1",
        )
        return run

    def test_the_view_reports_stages_assets_owners_and_progress(self) -> None:
        self.ledger.append(self.approved_decision(0))
        self.runs.save(self.working_run(1, "stage-1-owner"))

        response = self.client.get(
            self.url(),
            params={
                "on": ON.isoformat(),
                "verified_post_launch_milestones": 2,
                "activity_entries": 5,
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        view = response.json()
        self.assertEqual(TENANT, view["tenant_id"])
        self.assertEqual(ENGAGEMENT, view["engagement"])
        self.assertEqual(VERSION, view["template_version"])
        self.assertEqual(1, view["current_stage_number"])
        self.assertEqual(1, view["next_approval_stage_number"])

        progress = view["progress"]
        self.assertEqual(1, progress["approved_gates"])
        self.assertEqual(11, progress["total_gates"])
        self.assertEqual(10, progress["gates_remaining"])
        self.assertEqual(2, progress["verified_post_launch_milestones"])
        self.assertEqual(5, progress["activity_entries"])
        self.assertEqual(3, progress["verified_progress"])

        stage0 = view["stages"][0]
        self.assertEqual("approved", stage0["status"])
        self.assertTrue(stage0["is_approved"])
        self.assertEqual("production-manager", stage0["assigned_owner"])
        self.assertEqual("Production Ready", stage0["checkpoint"])
        self.assertEqual([], stage0["missing_asset_kinds"])
        self.assertEqual(
            {asset["asset_id"] for asset in stage0["approved_assets"]},
            set(stage0["required_asset_kinds"]),
        )
        self.assertTrue(
            all(asset["version"] == 1 for asset in stage0["approved_assets"])
        )

        stage1 = view["stages"][1]
        self.assertEqual("working", stage1["status"])
        self.assertEqual("stage-1-owner", stage1["assigned_owner"])
        self.assertEqual(ON.isoformat(), stage1["entered_at"])
        self.assertFalse(stage1["is_approved"])

    def test_an_empty_store_reports_every_stage_not_started(self) -> None:
        response = self.client.get(self.url(), params={"on": ON.isoformat()})

        self.assertEqual(response.status_code, 200, response.text)
        view = response.json()
        self.assertEqual(0, view["current_stage_number"])
        self.assertEqual(0, view["progress"]["approved_gates"])
        self.assertEqual(11, len(view["stages"]))
        self.assertTrue(
            all(stage["status"] == "not_started" for stage in view["stages"])
        )

    def test_a_recorded_gate_is_not_visible_to_another_client(self) -> None:
        self.ledger.append(self.approved_decision(0))

        response = self.client.get(
            self.url(OTHER_TENANT), params={"on": ON.isoformat()}
        )

        self.assertEqual(response.status_code, 200, response.text)
        view = response.json()
        self.assertEqual(OTHER_TENANT, view["tenant_id"])
        self.assertEqual(0, view["progress"]["approved_gates"])
        self.assertEqual("not_started", view["stages"][0]["status"])

    def test_the_evaluation_instant_is_required(self) -> None:
        response = self.client.get(self.url())

        self.assertEqual(response.status_code, 422, response.text)

    @staticmethod
    def umbrella_plan(tenant_id: str = TENANT, workspace_id: str = ENGAGEMENT):
        from datetime import timedelta

        from redops.contexts.engagement.domain.entities import ClientWorkspace
        from redops.contexts.engagement.domain.value_objects import ClientAuthority
        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )
        from redops.contexts.portfolio.domain.value_objects import (
            LAUNCH_MAP_SECTIONS,
            LAUNCH_MAP_SECTION_STAGES,
            QUARTERLY_REVIEW_DAYS,
            BusinessTarget,
            QuarterlyReview,
            UmbrellaPlan,
            UmbrellaSection,
        )

        return UmbrellaPlan(
            plan_id="umbrella-3f",
            tenant_id=tenant_id,
            owner="red-principal",
            workspace=ClientWorkspace(
                workspace_id=workspace_id,
                tenant_id=tenant_id,
                authorities=(
                    ClientAuthority(
                        actor="red-owner", authority="production-owner"
                    ),
                ),
            ),
            template=stage_zero_to_ten_template(VERSION),
            sections=tuple(
                UmbrellaSection(
                    section=kind,
                    stages=LAUNCH_MAP_SECTION_STAGES[kind],
                    objective=f"{kind.value} objective",
                )
                for kind in LAUNCH_MAP_SECTIONS
            ),
            targets=(
                BusinessTarget(
                    target_id="target-leads",
                    name="qualified strategy calls",
                    metric="booked strategy calls per week",
                    goal="20 per week",
                    due_on=date(2026, 12, 31),
                ),
            ),
            reviews=(
                QuarterlyReview(
                    reviewed_on=TODAY,
                    next_review_on=TODAY
                    + timedelta(days=QUARTERLY_REVIEW_DAYS),
                    actor="red-principal",
                ),
            ),
            created_on=TODAY,
        )

    def test_the_view_supplies_the_stored_umbrella_plan(self) -> None:
        self.umbrella_plans.save(self.umbrella_plan())

        response = self.client.get(self.url(), params={"on": ON.isoformat()})

        self.assertEqual(response.status_code, 200, response.text)
        umbrella = response.json()["umbrella_plan"]
        self.assertIsNotNone(umbrella)
        self.assertEqual("umbrella-3f", umbrella["plan_id"])
        self.assertEqual(TENANT, umbrella["tenant_id"])
        self.assertEqual("red-principal", umbrella["owner"])
        self.assertEqual(list(range(11)), umbrella["covered_stages"])
        self.assertEqual(TODAY.isoformat(), umbrella["reviewed_on"])

    def test_the_view_omits_an_absent_umbrella_plan(self) -> None:
        response = self.client.get(self.url(), params={"on": ON.isoformat()})

        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()["umbrella_plan"])

    def test_another_clients_umbrella_plan_is_not_shown(self) -> None:
        self.umbrella_plans.save(
            self.umbrella_plan(tenant_id=OTHER_TENANT, workspace_id=ENGAGEMENT)
        )

        response = self.client.get(self.url(), params={"on": ON.isoformat()})

        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()["umbrella_plan"])


if __name__ == "__main__":
    unittest.main()
