"""HTTP-boundary behavioral tests for the stage 7 gate route.

SPEC.md section 6 requires the API to call use cases through ports and never
mutate persistence directly; SPEC.md section 7 makes the stage gate an explicit
REST resource; SPEC.md section 11 lists as minimum acceptance scenarios both
"unauthorized approval is rejected" and "a different client's retrieval produces
no result". SPEC.md section 4 makes the stage 7 "Authority Amplifier Approved"
gate depend on a passing stage 6 decision and gives stage 7 two distinct
approvals -- script and supported proof before visual production, then final
creative acceptance. Canon files 13-18 and 28 inform the amplifier shape
(SPEC.md section 12.3).

These tests drive the real FastAPI app, seed stages 0 through 6 through their own
routes, then record stage 7 through the tenant-scoped ``GateLedgerRepository`` and
``StageRunRepository`` ports (substituted with fresh in-memory adapters). The
payload builders for the earlier stages are reused from the stage 6 route test so
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
SCOPE = "stage-8-funnel-integration"
CORRELATION = "corr-stage-7"
ON = "2026-10-03"
DUE = "2026-10-17"


class StageSevenGateRouteTests(unittest.TestCase):
    """The stage 7 gate is recorded only through the domain use case and port."""

    @classmethod
    def setUpClass(cls) -> None:
        from tests.unit.test_stage_six_gate_route import StageSixGateRouteTests

        try:
            StageSixGateRouteTests.setUpClass()
            from redops.api.routes import (
                get_authority_amplifier_repository,
                get_client_workspace_store,
            )
            from redops.contexts.engagement.infrastructure.repositories import (
                InMemoryClientWorkspaceStore,
            )
            from redops.contexts.production.domain.value_objects import (
                CANONICAL_AMPLIFIER_KINDS,
            )
            from redops.contexts.production.infrastructure.repositories import (
                InMemoryAuthorityAmplifierRepository,
            )
        except unittest.SkipTest:
            raise
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls._six = StageSixGateRouteTests(
            "test_a_passing_gate_is_recorded_and_pins_exact_versions"
        )
        cls.create_app = staticmethod(StageSixGateRouteTests.create_app)
        cls.dependency = staticmethod(StageSixGateRouteTests.dependency)
        cls.run_dependency = staticmethod(StageSixGateRouteTests.run_dependency)
        cls.workspace_dependency = staticmethod(get_client_workspace_store)
        cls.method_dependency = staticmethod(
            StageSixGateRouteTests.method_dependency
        )
        cls.offer_dependency = staticmethod(
            StageSixGateRouteTests.offer_dependency
        )
        cls.message_dependency = staticmethod(
            StageSixGateRouteTests.message_dependency
        )
        cls.repository_class = staticmethod(
            StageSixGateRouteTests.repository_class
        )
        cls.run_repository_class = staticmethod(
            StageSixGateRouteTests.run_repository_class
        )
        cls.workspace_store_class = staticmethod(InMemoryClientWorkspaceStore)
        cls.method_repository_class = staticmethod(
            StageSixGateRouteTests.method_repository_class
        )
        cls.offer_repository_class = staticmethod(
            StageSixGateRouteTests.offer_repository_class
        )
        cls.message_repository_class = staticmethod(
            StageSixGateRouteTests.message_repository_class
        )
        cls.amplifier_dependency = staticmethod(
            get_authority_amplifier_repository
        )
        cls.amplifier_repository_class = staticmethod(
            InMemoryAuthorityAmplifierRepository
        )
        cls.amplifier_kinds = CANONICAL_AMPLIFIER_KINDS

    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        self.app = self.create_app()
        self.repository = self.repository_class()
        self.run_repository = self.run_repository_class()
        self.workspaces = self.workspace_store_class()
        self.method_repository = self.method_repository_class()
        self.offer_repository = self.offer_repository_class()
        self.message_repository = self.message_repository_class()
        self.amplifier_repository = self.amplifier_repository_class()
        self.app.dependency_overrides[self.dependency] = lambda: self.repository
        self.app.dependency_overrides[self.run_dependency] = (
            lambda: self.run_repository
        )
        self.app.dependency_overrides[self.workspace_dependency] = (
            lambda: self.workspaces
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
        self.client = TestClient(self.app)
        self.register_workspace()

    def register_workspace(
        self, tenant_id: str = TENANT, *, with_approver: bool = True
    ) -> None:
        from tests.unit.workspace_fixture import register_workspace

        register_workspace(
            self.client,
            tenant_id=tenant_id,
            owner=OWNER,
            approver=APPROVER,
            with_approver=with_approver,
        )

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def _amplifier(self, **overrides):
        body = {
            "amplifier_id": "amplifier-3f",
            "owner": "production-manager",
            "script": [
                {"kind": kind, "content": f"{kind} content"}
                for kind in (
                    "promise",
                    "proof",
                    "problems",
                    "steps",
                    "context",
                    "action",
                )
            ],
            "proof_claim_ids": ["claim-1"],
            "visuals": {
                "storyboard": "asset://aa/storyboard",
                "brand_treatment": "asset://aa/brand",
                "presentation": "asset://aa/slides",
                "speaker_notes": "asset://aa/notes",
                "recording": "asset://aa/recording",
                "edited_video": "asset://aa/edited",
                "hosted_video": "asset://aa/hosted",
                "player_assets": "asset://aa/player",
            },
            "script_approval": {
                "approved_by": "production-manager",
                "intended_use": "3f pilot campaign",
                "approved_on": "2026-10-02",
            },
            "creative_approval": {
                "approved_by": "client-authority",
                "intended_use": "3f pilot campaign",
                "approved_on": "2026-10-03",
            },
        }
        body.update(overrides)
        return body

    def _claims(self):
        return [
            {
                "claim_id": "claim-1",
                "statement": "Method fact recorded with the client",
                "provenance": "known",
                "confidence_note": "directly observed",
                "citations": [
                    {
                        "source_id": "source-1",
                        "checksum": "sha256:abc",
                        "location": "p.1",
                    }
                ],
            }
        ]

    def payload(self, **overrides):
        body = {
            "workspace_id": "ws-3f",
            "amplifier_package_id": "amplifier-package-3f",
            "amplifier_version": 1,
            "message": self._six._message(),
            "offer": self._six._offer(),
            "method": self._six._method(),
            "amplifier": self._amplifier(),
            "claims": self._claims(),
            "stage_owner": OWNER,
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE,
            "checkpoint_evidence": "all nine stage 7 kinds reviewed",
            "rationale": "the amplifier message and supported proof passed review",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        body.update(overrides)
        return body

    def url(self, tenant_id: str = TENANT) -> str:
        return f"/red/clients/{tenant_id}/stages/7/gate"

    def seed_through_stage_six(self, tenant_id: str = TENANT) -> None:
        for number, payload in (
            (0, self._six.stage_zero_payload()),
            (1, self._six.stage_one_payload()),
            (2, self._six.stage_two_payload()),
            (3, self._six.stage_three_payload()),
            (4, self._six.stage_four_payload()),
            (5, self._six.stage_five_payload()),
            (6, self._six.payload()),
        ):
            response = self.client.post(
                f"/red/clients/{tenant_id}/stages/{number}/gate", json=payload
            )
            self.assertEqual(response.status_code, 201, response.text)

    def test_a_passing_gate_is_recorded_and_pins_exact_versions(self) -> None:
        self.seed_through_stage_six()

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)
        decision = response.json()
        self.assertEqual(decision["stage_number"], 7)
        self.assertEqual(decision["checkpoint"], "Authority Amplifier Approved")
        self.assertEqual(decision["disposition"], "approved")
        self.assertEqual(decision["reviewer"], APPROVER)
        self.assertEqual(decision["tenant_id"], TENANT)
        self.assertEqual(
            {asset["asset_id"] for asset in decision["required_assets"]},
            set(self.amplifier_kinds),
        )
        self.assertTrue(
            all(asset["version"] == 1 for asset in decision["required_assets"])
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        decision_seven = reloaded.decision_for(7)
        self.assertIsNotNone(decision_seven)
        self.assertEqual(
            {asset.asset_id for asset in decision_seven.required_assets},
            set(self.amplifier_kinds),
        )

    def test_the_stage_run_is_persisted_with_its_completion(self) -> None:
        self.seed_through_stage_six()

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )
        from redops.contexts.governance.domain.value_objects import StageStatus

        run = self.run_repository.load(
            stage_zero_to_ten_template().version, "ws-3f", 7, TENANT
        )
        self.assertIsNotNone(run)
        self.assertEqual(StageStatus.COMPLETE, run.status)
        self.assertEqual(OWNER, run.assigned_owner)
        self.assertEqual(TENANT, run.tenant_id)

    def test_a_stage_seven_gate_without_a_passing_stage_six_is_rejected(
        self,
    ) -> None:
        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "GateDecisionError"
        )

    def test_unsupported_proof_is_rejected_without_a_write(self) -> None:
        self.seed_through_stage_six()

        response = self.client.post(
            self.url(),
            json=self.payload(
                amplifier=self._amplifier(proof_claim_ids=["claim-unknown"])
            ),
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "UnsupportedProofError"
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertIsNone(reloaded.decision_for(7))

    def test_an_unauthorized_approver_is_rejected_without_a_write(self) -> None:
        self.seed_through_stage_six()

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
        self.assertIsNone(reloaded.decision_for(7))

    def test_a_gate_without_a_registered_workspace_is_a_named_404(self) -> None:
        self.seed_through_stage_six()

        response = self.client.post(
            self.url(), json=self.payload(workspace_id="ws-unregistered")
        )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "ClientWorkspaceNotFoundError"
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertIsNone(reloaded.decision_for(7))

    def test_the_gate_approves_against_the_persisted_registry(self) -> None:
        # The body no longer carries authorities; the approver is authorized
        # only if the persisted workspace registry names them. Seed through
        # stage 6 with an authorized approver, then rebuild the store without a
        # client-designated authority and the same stage 7 request is refused.
        self.seed_through_stage_six()
        self.workspaces = self.workspace_store_class()
        self.register_workspace(with_approver=False)

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"],
            "GateApproverNotAuthorizedError",
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertIsNone(reloaded.decision_for(7))

    def test_a_stage_seven_decision_is_not_visible_to_another_client(self) -> None:
        self.seed_through_stage_six()
        self.assertEqual(
            self.client.post(self.url(), json=self.payload()).status_code, 201
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        other = self.repository.load(
            stage_zero_to_ten_template(), OTHER_TENANT
        )
        self.assertIsNone(other.decision_for(7))


if __name__ == "__main__":
    unittest.main()
