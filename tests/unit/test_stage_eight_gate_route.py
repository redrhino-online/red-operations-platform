"""HTTP-boundary behavioral tests for the stage 8 gate route.

SPEC.md section 6 requires the API to call use cases through ports and never
mutate persistence directly; SPEC.md section 7 makes the stage gate an explicit
REST resource; SPEC.md section 11 lists as minimum acceptance scenarios both
"unauthorized approval is rejected" and "a different client's retrieval produces
no result". SPEC.md section 4 makes the stage 8 "Funnel Complete" gate depend on
a passing stage 7 decision and turns on a same-tenant test prospect path whose
capture, engagement and conversion handoffs routed with reliable records and
ownership. Canon files 13, 14, 21 and 22 inform the stage 8 funnel shape
(SPEC.md section 12.3).

These tests drive the real FastAPI app, seed stages 0 through 7 through their own
routes, then record stage 8 through the tenant-scoped ``GateLedgerRepository`` and
``StageRunRepository`` ports (substituted with fresh in-memory adapters). The
payload builders for the earlier stages are reused from the stage 7 route test so
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
SCOPE = "stage-9-launch-qa"
CORRELATION = "corr-stage-8"
ON = "2026-10-03"
DUE = "2026-10-17"


class StageEightGateRouteTests(unittest.TestCase):
    """The stage 8 gate is recorded only through the domain use case and port."""

    @classmethod
    def setUpClass(cls) -> None:
        from tests.unit.test_stage_seven_gate_route import (
            StageSevenGateRouteTests,
        )

        try:
            StageSevenGateRouteTests.setUpClass()
            from redops.api.routes import (
                get_funnel_integration_repository,
                get_launch_qa_repository,
            )
            from redops.contexts.execution.domain.value_objects import (
                CANONICAL_FUNNEL_KINDS,
            )
            from redops.contexts.execution.infrastructure.repositories import (
                InMemoryFunnelIntegrationRepository,
                InMemoryLaunchQARepository,
            )
        except unittest.SkipTest:
            raise
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls._seven = StageSevenGateRouteTests(
            "test_a_passing_gate_is_recorded_and_pins_exact_versions"
        )
        cls.create_app = staticmethod(StageSevenGateRouteTests.create_app)
        cls.dependency = staticmethod(StageSevenGateRouteTests.dependency)
        cls.run_dependency = staticmethod(StageSevenGateRouteTests.run_dependency)
        cls.method_dependency = staticmethod(
            StageSevenGateRouteTests.method_dependency
        )
        cls.offer_dependency = staticmethod(
            StageSevenGateRouteTests.offer_dependency
        )
        cls.message_dependency = staticmethod(
            StageSevenGateRouteTests.message_dependency
        )
        cls.amplifier_dependency = staticmethod(
            StageSevenGateRouteTests.amplifier_dependency
        )
        cls.repository_class = staticmethod(
            StageSevenGateRouteTests.repository_class
        )
        cls.run_repository_class = staticmethod(
            StageSevenGateRouteTests.run_repository_class
        )
        cls.method_repository_class = staticmethod(
            StageSevenGateRouteTests.method_repository_class
        )
        cls.offer_repository_class = staticmethod(
            StageSevenGateRouteTests.offer_repository_class
        )
        cls.message_repository_class = staticmethod(
            StageSevenGateRouteTests.message_repository_class
        )
        cls.amplifier_repository_class = staticmethod(
            StageSevenGateRouteTests.amplifier_repository_class
        )
        cls.funnel_dependency = staticmethod(
            get_funnel_integration_repository
        )
        cls.funnel_repository_class = staticmethod(
            InMemoryFunnelIntegrationRepository
        )
        cls.launch_qa_dependency = staticmethod(get_launch_qa_repository)
        cls.launch_qa_repository_class = staticmethod(
            InMemoryLaunchQARepository
        )
        cls.funnel_kinds = CANONICAL_FUNNEL_KINDS

    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        self.app = self.create_app()
        self.repository = self.repository_class()
        self.run_repository = self.run_repository_class()
        self.method_repository = self.method_repository_class()
        self.offer_repository = self.offer_repository_class()
        self.message_repository = self.message_repository_class()
        self.amplifier_repository = self.amplifier_repository_class()
        self.funnel_repository = self.funnel_repository_class()
        self.launch_qa_repository = self.launch_qa_repository_class()
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
        self.app.dependency_overrides[self.message_dependency] = (
            lambda: self.message_repository
        )
        self.app.dependency_overrides[self.amplifier_dependency] = (
            lambda: self.amplifier_repository
        )
        self.app.dependency_overrides[self.funnel_dependency] = (
            lambda: self.funnel_repository
        )
        self.app.dependency_overrides[self.launch_qa_dependency] = (
            lambda: self.launch_qa_repository
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def _funnel(self, **overrides):
        body = {
            "integration_id": "funnel-3f",
            "owner": "integration-manager",
            "assets": {
                "campaign_architecture": "asset://funnel/architecture",
                "pages": "asset://funnel/pages",
                "forms": "asset://funnel/forms",
                "qualification": "asset://funnel/qualification",
                "booking": "asset://funnel/booking",
                "sequences": "asset://funnel/sequences",
                "crm": "asset://funnel/crm",
                "tags": "asset://funnel/tags",
                "automation": "asset://funnel/automation",
                "analytics": "asset://funnel/analytics",
                "tracking": "asset://funnel/tracking",
                "sales_handoff": "asset://funnel/sales-handoff",
                "sops": "asset://funnel/sops",
            },
            "dry_run": {
                "dry_run_id": "dryrun-3f",
                "handoffs": [
                    {
                        "kind": "capture",
                        "outcome": "routed",
                        "record_id": "record-capture",
                        "owner": "sdr",
                    },
                    {
                        "kind": "engagement",
                        "outcome": "routed",
                        "record_id": "record-engagement",
                        "owner": "setter",
                    },
                    {
                        "kind": "conversion",
                        "outcome": "routed",
                        "record_id": "record-conversion",
                        "owner": "closer",
                    },
                ],
            },
        }
        body.update(overrides)
        return body

    def payload(self, **overrides):
        seven = self._seven.payload()
        body = {
            "workspace_id": seven["workspace_id"],
            "authorities": seven["authorities"],
            "funnel_package_id": "funnel-package-3f",
            "funnel_version": 1,
            "message": seven["message"],
            "offer": seven["offer"],
            "method": seven["method"],
            "amplifier": seven["amplifier"],
            "claims": seven["claims"],
            "funnel": self._funnel(),
            "stage_owner": OWNER,
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE,
            "checkpoint_evidence": "prospect path dry run routed all handoffs",
            "rationale": "the funnel completed capture, engagement and conversion",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        body.update(overrides)
        return body

    def url(self, tenant_id: str = TENANT) -> str:
        return f"/red/clients/{tenant_id}/stages/8/gate"

    def seed_through_stage_seven(self, tenant_id: str = TENANT) -> None:
        six = self._seven._six
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
        response = self.client.post(
            f"/red/clients/{tenant_id}/stages/7/gate",
            json=self._seven.payload(),
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_a_passing_gate_is_recorded_and_pins_exact_versions(self) -> None:
        self.seed_through_stage_seven()

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)
        decision = response.json()
        self.assertEqual(decision["stage_number"], 8)
        self.assertEqual(decision["checkpoint"], "Funnel Complete")
        self.assertEqual(decision["disposition"], "approved")
        self.assertEqual(decision["reviewer"], APPROVER)
        self.assertEqual(decision["tenant_id"], TENANT)
        self.assertEqual(
            {asset["asset_id"] for asset in decision["required_assets"]},
            set(self.funnel_kinds),
        )
        self.assertTrue(
            all(asset["version"] == 1 for asset in decision["required_assets"])
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        decision_eight = reloaded.decision_for(8)
        self.assertIsNotNone(decision_eight)
        self.assertEqual(
            {asset.asset_id for asset in decision_eight.required_assets},
            set(self.funnel_kinds),
        )

    def test_the_stage_run_is_persisted_with_its_completion(self) -> None:
        self.seed_through_stage_seven()

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )
        from redops.contexts.governance.domain.value_objects import StageStatus

        run = self.run_repository.load(
            stage_zero_to_ten_template().version, "ws-3f", 8, TENANT
        )
        self.assertIsNotNone(run)
        self.assertEqual(StageStatus.COMPLETE, run.status)
        self.assertEqual(OWNER, run.assigned_owner)
        self.assertEqual(TENANT, run.tenant_id)

    def test_a_stage_eight_gate_without_a_passing_stage_seven_is_rejected(
        self,
    ) -> None:
        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "GateDecisionError"
        )

    def test_a_failed_handoff_prevents_funnel_completion(self) -> None:
        self.seed_through_stage_seven()

        funnel = self._funnel()
        funnel["dry_run"]["handoffs"][2]["outcome"] = "failed"
        response = self.client.post(
            self.url(), json=self.payload(funnel=funnel)
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "FunnelIncompleteError"
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertIsNone(reloaded.decision_for(8))

    def test_re_stating_the_approved_amplifier_with_different_content_is_refused(
        self,
    ) -> None:
        self.seed_through_stage_seven()

        amplifier = self._seven.payload()["amplifier"]
        amplifier["script"][0]["content"] = "a different promise"
        response = self.client.post(
            self.url(), json=self.payload(amplifier=amplifier)
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"],
            "AuthorityAmplifierVersionConflictError",
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertIsNone(reloaded.decision_for(8))

    def test_an_unauthorized_approver_is_rejected_without_a_write(self) -> None:
        self.seed_through_stage_seven()

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
        self.assertIsNone(reloaded.decision_for(8))

    def test_a_stage_eight_decision_is_not_visible_to_another_client(
        self,
    ) -> None:
        self.seed_through_stage_seven()
        self.assertEqual(
            self.client.post(self.url(), json=self.payload()).status_code, 201
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        other = self.repository.load(
            stage_zero_to_ten_template(), OTHER_TENANT
        )
        self.assertIsNone(other.decision_for(8))


if __name__ == "__main__":
    unittest.main()
