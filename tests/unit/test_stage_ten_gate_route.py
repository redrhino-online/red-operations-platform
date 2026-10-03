"""HTTP-boundary behavioral tests for the stage 10 gate route.

SPEC.md section 6 requires the API to call use cases through ports and never
mutate persistence directly; SPEC.md section 7 makes the stage gate an explicit
REST resource; SPEC.md section 11 lists as minimum acceptance scenarios both
"unauthorized approval is rejected" and "a different client's retrieval produces
no result". SPEC.md section 4 makes the stage 10 "Performance Baseline
Established" gate depend on a passing stage 9 decision and turns on the stage 9
traffic authorization plus an observed first qualified traffic milestone, with
the later lead, appointment and sale milestones shown as pending. Canon files 22,
23, 29-31, 33 and 34 inform the stage 10 shape (SPEC.md section 12.3).

These tests drive the real FastAPI app, seed stages 0 through 9 through their own
routes, then record stage 10 through the tenant-scoped ``GateLedgerRepository``
and ``StageRunRepository`` ports (substituted with fresh in-memory adapters). The
payload builders for the earlier stages are reused from the stage 9 route test so
the two suites cannot drift in how they re-state the pipelined upstream content.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest


TENANT = "client-3f"
OTHER_TENANT = "client-other"
OWNER = "red-owner"
APPROVER = "client-approver-1"
AUTHORITY = "client-authority"
SCOPE = "stage-10-baseline"
CORRELATION = "corr-stage-10"
ON = "2026-10-03"
DUE = "2026-10-17"


class StageTenGateRouteTests(unittest.TestCase):
    """The stage 10 gate is recorded only through the domain use case and port."""

    @classmethod
    def setUpClass(cls) -> None:
        from tests.unit.test_stage_nine_gate_route import (
            StageNineGateRouteTests,
        )

        try:
            StageNineGateRouteTests.setUpClass()
            from redops.contexts.execution.domain.value_objects import (
                CANONICAL_BASELINE_KINDS,
            )
        except unittest.SkipTest:
            raise
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls._nine = StageNineGateRouteTests(
            "test_a_passing_gate_is_recorded_and_pins_exact_versions"
        )
        cls.create_app = staticmethod(StageNineGateRouteTests.create_app)
        cls.dependency = staticmethod(StageNineGateRouteTests.dependency)
        cls.run_dependency = staticmethod(StageNineGateRouteTests.run_dependency)
        cls.method_dependency = staticmethod(
            StageNineGateRouteTests.method_dependency
        )
        cls.offer_dependency = staticmethod(
            StageNineGateRouteTests.offer_dependency
        )
        cls.repository_class = staticmethod(
            StageNineGateRouteTests.repository_class
        )
        cls.run_repository_class = staticmethod(
            StageNineGateRouteTests.run_repository_class
        )
        cls.method_repository_class = staticmethod(
            StageNineGateRouteTests.method_repository_class
        )
        cls.offer_repository_class = staticmethod(
            StageNineGateRouteTests.offer_repository_class
        )
        cls.baseline_kinds = CANONICAL_BASELINE_KINDS

    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        self.app = self.create_app()
        self.repository = self.repository_class()
        self.run_repository = self.run_repository_class()
        self.method_repository = self.method_repository_class()
        self.offer_repository = self.offer_repository_class()
        self.app.dependency_overrides[self.dependency] = lambda: self.repository
        self.app.dependency_overrides[self.run_dependency] = (
            lambda: self.run_repository
        )
        self.app.dependency_overrides[self.method_dependency] = (
            lambda: self.method_repository
        )
        self.app.dependency_overrides[self.offer_dependency] = (
            lambda: self.offer_repository
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def _baseline(self, **overrides):
        body = {
            "baseline_id": "baseline-3f",
            "owner": "baseline-owner",
            "assets": {
                "live_campaign": "asset://campaign/3f",
                "spend_records": "asset://spend/3f",
                "lead_records": "asset://leads/3f",
                "conversion_measures": "asset://conversion/3f",
                "engagement_measures": "asset://engagement/3f",
                "applications": "asset://applications/3f",
                "bookings": "asset://bookings/3f",
                "shows": "asset://shows/3f",
                "closes": "asset://closes/3f",
                "acquisition_cost": "asset://acquisition-cost/3f",
                "attribution": "asset://attribution/3f",
                "issue_log": "asset://issue-log/3f",
            },
            "milestones": [
                {
                    "kind": "first_qualified_traffic",
                    "status": "observed",
                    "observed_on": ON,
                    "source": "analytics://traffic/3f",
                },
                {"kind": "lead", "status": "pending"},
                {"kind": "appointment", "status": "pending"},
                {"kind": "sale", "status": "pending"},
            ],
        }
        body.update(overrides)
        return body

    def payload(self, **overrides):
        nine = self._nine.payload()
        body = {
            "workspace_id": nine["workspace_id"],
            "authorities": nine["authorities"],
            "baseline_package_id": "baseline-package-3f",
            "baseline_version": 1,
            "message": nine["message"],
            "offer": nine["offer"],
            "method": nine["method"],
            "amplifier": nine["amplifier"],
            "claims": nine["claims"],
            "funnel": nine["funnel"],
            "qa": nine["qa"],
            "baseline": self._baseline(),
            "stage_owner": OWNER,
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE,
            "checkpoint_evidence": "first qualified traffic observed and recorded",
            "rationale": "the baseline is grounded on the authorized launch",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        body.update(overrides)
        return body

    def url(self, tenant_id: str = TENANT) -> str:
        return f"/red/clients/{tenant_id}/stages/10/gate"

    def seed_through_stage_nine(self, tenant_id: str = TENANT) -> None:
        nine = self._nine
        eight = nine._eight
        six = eight._seven._six
        for number, payload in (
            (0, six.stage_zero_payload()),
            (1, six.stage_one_payload()),
            (2, six.stage_two_payload()),
            (3, six.stage_three_payload()),
            (4, six.stage_four_payload()),
            (5, six.stage_five_payload()),
            (6, six.payload()),
        ):
            response = self.client.post(
                f"/red/clients/{tenant_id}/stages/{number}/gate", json=payload
            )
            self.assertEqual(response.status_code, 201, response.text)
        for number, payload in (
            (7, eight._seven.payload()),
            (8, eight.payload()),
        ):
            response = self.client.post(
                f"/red/clients/{tenant_id}/stages/{number}/gate", json=payload
            )
            self.assertEqual(response.status_code, 201, response.text)
        response = self.client.post(
            f"/red/clients/{tenant_id}/stages/9/gate", json=nine.payload()
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_a_passing_gate_is_recorded_and_pins_exact_versions(self) -> None:
        self.seed_through_stage_nine()

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)
        decision = response.json()
        self.assertEqual(decision["stage_number"], 10)
        self.assertEqual(decision["checkpoint"], "Performance Baseline Established")
        self.assertEqual(decision["disposition"], "approved")
        self.assertEqual(decision["reviewer"], APPROVER)
        self.assertEqual(decision["tenant_id"], TENANT)
        self.assertEqual(
            {asset["asset_id"] for asset in decision["required_assets"]},
            set(self.baseline_kinds),
        )
        self.assertTrue(
            all(asset["version"] == 1 for asset in decision["required_assets"])
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        decision_ten = reloaded.decision_for(10)
        self.assertIsNotNone(decision_ten)
        self.assertEqual(
            {asset.asset_id for asset in decision_ten.required_assets},
            set(self.baseline_kinds),
        )

    def test_the_stage_run_is_persisted_with_its_completion(self) -> None:
        self.seed_through_stage_nine()

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )
        from redops.contexts.governance.domain.value_objects import StageStatus

        run = self.run_repository.load(
            stage_zero_to_ten_template().version, "ws-3f", 10, TENANT
        )
        self.assertIsNotNone(run)
        self.assertEqual(StageStatus.COMPLETE, run.status)
        self.assertEqual(OWNER, run.assigned_owner)
        self.assertEqual(TENANT, run.tenant_id)

    def test_a_stage_ten_gate_without_a_passing_stage_nine_is_rejected(
        self,
    ) -> None:
        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "GateDecisionError"
        )

    def test_missing_first_qualified_traffic_prevents_establishment(self) -> None:
        self.seed_through_stage_nine()

        baseline = self._baseline()
        baseline["milestones"][0] = {
            "kind": "first_qualified_traffic",
            "status": "pending",
        }
        response = self.client.post(
            self.url(), json=self.payload(baseline=baseline)
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"],
            "PerformanceBaselineIncompleteError",
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertIsNone(reloaded.decision_for(10))

    def test_an_omitted_milestone_prevents_establishment(self) -> None:
        self.seed_through_stage_nine()

        baseline = self._baseline()
        baseline["milestones"] = baseline["milestones"][:2]
        response = self.client.post(
            self.url(), json=self.payload(baseline=baseline)
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"],
            "PerformanceBaselineIncompleteError",
        )

    def test_an_unauthorized_approver_is_rejected_without_a_write(self) -> None:
        self.seed_through_stage_nine()

        response = self.client.post(
            self.url(), json=self.payload(approver="stranger")
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"],
            "GateApproverNotAuthorizedError",
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertIsNone(reloaded.decision_for(10))

    def test_a_stage_ten_decision_is_not_visible_to_another_client(self) -> None:
        self.seed_through_stage_nine()
        self.assertEqual(
            self.client.post(self.url(), json=self.payload()).status_code, 201
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        other = self.repository.load(
            stage_zero_to_ten_template(), OTHER_TENANT
        )
        self.assertIsNone(other.decision_for(10))


if __name__ == "__main__":
    unittest.main()
