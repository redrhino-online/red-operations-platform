"""HTTP-boundary behavioral tests for the stage 9 gate route.

SPEC.md section 6 requires the API to call use cases through ports and never
mutate persistence directly; SPEC.md section 7 makes the stage gate an explicit
REST resource; SPEC.md section 11 lists as minimum acceptance scenarios both
"unauthorized approval is rejected" and "a different client's retrieval produces
no result". SPEC.md section 4 makes the stage 9 "Launch Approved" gate depend on
a passing stage 8 decision and turns on "all critical path checks pass, exceptions
have owners, and the designated human authorizes traffic". Canon files 01, 08, 21,
22 and 24 inform the stage 9 shape (SPEC.md section 12.3).

These tests drive the real FastAPI app, seed stages 0 through 8 through their own
routes, then record stage 9 through the tenant-scoped ``GateLedgerRepository`` and
``StageRunRepository`` ports (substituted with fresh in-memory adapters). The
payload builders for the earlier stages are reused from the stage 8 route test so
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
SCOPE = "stage-10-traffic"
CORRELATION = "corr-stage-9"
ON = "2026-10-03"
DUE = "2026-10-17"


class StageNineGateRouteTests(unittest.TestCase):
    """The stage 9 gate is recorded only through the domain use case and port."""

    @classmethod
    def setUpClass(cls) -> None:
        from tests.unit.test_stage_eight_gate_route import (
            StageEightGateRouteTests,
        )

        try:
            StageEightGateRouteTests.setUpClass()
            from redops.contexts.execution.domain.value_objects import (
                CANONICAL_LAUNCH_KINDS,
            )
        except unittest.SkipTest:
            raise
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls._eight = StageEightGateRouteTests(
            "test_a_passing_gate_is_recorded_and_pins_exact_versions"
        )
        cls.create_app = staticmethod(StageEightGateRouteTests.create_app)
        cls.dependency = staticmethod(StageEightGateRouteTests.dependency)
        cls.run_dependency = staticmethod(StageEightGateRouteTests.run_dependency)
        cls.method_dependency = staticmethod(
            StageEightGateRouteTests.method_dependency
        )
        cls.offer_dependency = staticmethod(
            StageEightGateRouteTests.offer_dependency
        )
        cls.message_dependency = staticmethod(
            StageEightGateRouteTests.message_dependency
        )
        cls.amplifier_dependency = staticmethod(
            StageEightGateRouteTests.amplifier_dependency
        )
        cls.repository_class = staticmethod(
            StageEightGateRouteTests.repository_class
        )
        cls.run_repository_class = staticmethod(
            StageEightGateRouteTests.run_repository_class
        )
        cls.method_repository_class = staticmethod(
            StageEightGateRouteTests.method_repository_class
        )
        cls.offer_repository_class = staticmethod(
            StageEightGateRouteTests.offer_repository_class
        )
        cls.message_repository_class = staticmethod(
            StageEightGateRouteTests.message_repository_class
        )
        cls.amplifier_repository_class = staticmethod(
            StageEightGateRouteTests.amplifier_repository_class
        )
        cls.funnel_dependency = staticmethod(
            StageEightGateRouteTests.funnel_dependency
        )
        cls.funnel_repository_class = staticmethod(
            StageEightGateRouteTests.funnel_repository_class
        )
        cls.launch_qa_dependency = staticmethod(
            StageEightGateRouteTests.launch_qa_dependency
        )
        cls.launch_qa_repository_class = staticmethod(
            StageEightGateRouteTests.launch_qa_repository_class
        )
        cls.launch_kinds = CANONICAL_LAUNCH_KINDS

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

    def _qa(self, **overrides):
        from redops.contexts.execution.domain.value_objects import (
            ComplianceAssetKind,
            QACheckKind,
        )

        body = {
            "qa_id": "qa-3f",
            "owner": "qa-owner",
            "designated_authority": AUTHORITY,
            "checks": [
                {
                    "kind": kind.value,
                    "outcome": "passed",
                    "evidence": f"evidence://{kind.value}",
                }
                for kind in QACheckKind
            ],
            "compliance": {
                "package_id": "compliance-3f",
                "target_markets": ["us"],
                "assets": [
                    {
                        "kind": kind.value,
                        "reference": f"asset://compliance/{kind.value}",
                        "version": 1,
                    }
                    for kind in ComplianceAssetKind
                ],
            },
            "authorization": {
                "authorized_by": AUTHORITY,
                "intended_use": "3f pilot launch",
                "authorized_on": ON,
            },
        }
        body.update(overrides)
        return body

    def payload(self, **overrides):
        eight = self._eight.payload()
        body = {
            "workspace_id": eight["workspace_id"],
            "authorities": eight["authorities"],
            "qa_package_id": "launch-package-3f",
            "qa_version": 1,
            "message": eight["message"],
            "offer": eight["offer"],
            "method": eight["method"],
            "amplifier": eight["amplifier"],
            "claims": eight["claims"],
            "funnel": eight["funnel"],
            "qa": self._qa(),
            "stage_owner": OWNER,
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE,
            "checkpoint_evidence": "all critical path checks passed and owned",
            "rationale": "the designated authority authorized traffic",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        body.update(overrides)
        return body

    def url(self, tenant_id: str = TENANT) -> str:
        return f"/red/clients/{tenant_id}/stages/9/gate"

    def seed_through_stage_eight(self, tenant_id: str = TENANT) -> None:
        eight = self._eight
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

    def test_a_passing_gate_is_recorded_and_pins_exact_versions(self) -> None:
        self.seed_through_stage_eight()

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)
        decision = response.json()
        self.assertEqual(decision["stage_number"], 9)
        self.assertEqual(decision["checkpoint"], "Launch Approved")
        self.assertEqual(decision["disposition"], "approved")
        self.assertEqual(decision["reviewer"], APPROVER)
        self.assertEqual(decision["tenant_id"], TENANT)
        self.assertEqual(
            {asset["asset_id"] for asset in decision["required_assets"]},
            set(self.launch_kinds),
        )
        self.assertTrue(
            all(asset["version"] == 1 for asset in decision["required_assets"])
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        decision_nine = reloaded.decision_for(9)
        self.assertIsNotNone(decision_nine)
        self.assertEqual(
            {asset.asset_id for asset in decision_nine.required_assets},
            set(self.launch_kinds),
        )

    def test_the_stage_run_is_persisted_with_its_completion(self) -> None:
        self.seed_through_stage_eight()

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )
        from redops.contexts.governance.domain.value_objects import StageStatus

        run = self.run_repository.load(
            stage_zero_to_ten_template().version, "ws-3f", 9, TENANT
        )
        self.assertIsNotNone(run)
        self.assertEqual(StageStatus.COMPLETE, run.status)
        self.assertEqual(OWNER, run.assigned_owner)
        self.assertEqual(TENANT, run.tenant_id)

    def test_a_stage_nine_gate_without_a_passing_stage_eight_is_rejected(
        self,
    ) -> None:
        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "GateDecisionError"
        )

    def test_a_failed_critical_path_check_prevents_launch_approval(self) -> None:
        self.seed_through_stage_eight()

        qa = self._qa()
        qa["checks"][1]["outcome"] = "failed"
        response = self.client.post(self.url(), json=self.payload(qa=qa))

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "LaunchQAIncompleteError"
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertIsNone(reloaded.decision_for(9))

    def test_a_missing_compliance_asset_prevents_launch_approval(self) -> None:
        self.seed_through_stage_eight()

        qa = self._qa()
        qa["compliance"]["assets"] = [
            asset
            for asset in qa["compliance"]["assets"]
            if asset["kind"] != "attorney_review"
        ]
        response = self.client.post(self.url(), json=self.payload(qa=qa))

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "MissingComplianceAssetError"
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertIsNone(reloaded.decision_for(9))

    def test_re_stating_the_completed_funnel_with_different_content_is_refused(
        self,
    ) -> None:
        self.seed_through_stage_eight()

        funnel = self._eight.payload()["funnel"]
        funnel["owner"] = "a different funnel owner"
        response = self.client.post(
            self.url(), json=self.payload(funnel=funnel)
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"],
            "FunnelVersionConflictError",
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertIsNone(reloaded.decision_for(9))

    def test_an_unauthorized_approver_is_rejected_without_a_write(self) -> None:
        self.seed_through_stage_eight()

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
        self.assertIsNone(reloaded.decision_for(9))

    def test_a_stage_nine_decision_is_not_visible_to_another_client(self) -> None:
        self.seed_through_stage_eight()
        self.assertEqual(
            self.client.post(self.url(), json=self.payload()).status_code, 201
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        other = self.repository.load(
            stage_zero_to_ten_template(), OTHER_TENANT
        )
        self.assertIsNone(other.decision_for(9))


if __name__ == "__main__":
    unittest.main()
