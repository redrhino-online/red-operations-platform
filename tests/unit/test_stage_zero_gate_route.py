"""HTTP-boundary behavioral tests for the stage 0 gate route.

SPEC.md section 6 requires the API to call use cases through ports and never
mutate persistence directly; SPEC.md section 7 makes the stage gate an explicit
REST resource; SPEC.md section 11 lists as minimum acceptance scenarios both
"unauthorized approval is rejected" and "a different client's retrieval produces
no result". These tests drive the real FastAPI app and the real application use
case through the tenant-scoped ``GateLedgerRepository`` port (substituted with a
fresh in-memory adapter), then assert the durable result the reload produces.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest
from datetime import date

TENANT = "client-3f"
OTHER_TENANT = "client-other"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE = "stage-1-diagnosis"
CORRELATION = "corr-stage-0"
ON = "2026-10-02"
DUE = "2026-10-16"


class StageZeroGateRouteTests(unittest.TestCase):
    """The stage 0 gate is recorded only through the domain use case and port."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import get_gate_ledger_repository
            from redops.contexts.governance.infrastructure.repositories import (
                InMemoryGateLedgerRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.dependency = staticmethod(get_gate_ledger_repository)
        cls.repository_class = staticmethod(InMemoryGateLedgerRepository)

    def setUp(self) -> None:
        self.app = self.create_app()
        self.repository = self.repository_class()
        self.app.dependency_overrides[self.dependency] = lambda: self.repository
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def payload(**overrides):
        from redops.contexts.engagement.domain.value_objects import (
            CANONICAL_INTAKE_KINDS,
        )

        body = {
            "workspace_id": "ws-3f",
            "authorities": [
                {"actor": OWNER, "authority": "production-owner"},
                {
                    "actor": APPROVER,
                    "authority": "client-designated-authority",
                },
            ],
            "intake_package_id": "intake-3f",
            "assets": [
                {
                    "asset_id": f"{kind.value}-3f@1",
                    "kind": kind.value,
                    "version": 1,
                    "owner": OWNER,
                    "summary": f"Recorded {kind.value}",
                    "evidence_claim_ids": ["claim-intake-1"],
                }
                for kind in CANONICAL_INTAKE_KINDS
            ],
            "claims": [
                {
                    "claim_id": "claim-intake-1",
                    "statement": "Intake fact recorded with the client",
                    "provenance": "known",
                    "confidence_note": "captured during intake",
                    "citations": [
                        {
                            "source_id": "source-intake",
                            "checksum": "sha256:abc",
                            "location": "p.1",
                        }
                    ],
                }
            ],
            "stage_owner": OWNER,
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE,
            "checkpoint_evidence": "all twelve stage 0 assets reviewed",
            "rationale": "intake complete and owned",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        body.update(overrides)
        return body

    def url(self, tenant_id: str = TENANT) -> str:
        return f"/red/clients/{tenant_id}/stages/0/gate"

    def test_a_passing_gate_is_recorded_and_pins_exact_versions(self) -> None:
        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)
        decision = response.json()
        self.assertEqual(decision["stage_number"], 0)
        self.assertEqual(decision["checkpoint"], "Production Ready")
        self.assertEqual(decision["disposition"], "approved")
        self.assertEqual(decision["reviewer"], APPROVER)
        self.assertEqual(decision["tenant_id"], TENANT)
        self.assertEqual(
            {asset["asset_id"] for asset in decision["required_assets"]},
            {kind.value for kind in self._canonical_kinds()},
        )
        self.assertTrue(
            all(asset["version"] == 1 for asset in decision["required_assets"])
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertTrue(reloaded.has_passing_decision(0, on=date(2026, 10, 2)))
        self.assertEqual(
            {
                (asset.asset_id, asset.version)
                for asset in reloaded.decision_for(0).required_assets
            },
            {(kind.value, 1) for kind in self._canonical_kinds()},
        )

    @staticmethod
    def _canonical_kinds():
        from redops.contexts.engagement.domain.value_objects import (
            CANONICAL_INTAKE_KINDS,
        )

        return CANONICAL_INTAKE_KINDS

    def test_an_unauthorized_approver_is_rejected_without_a_write(self) -> None:
        response = self.client.post(
            self.url(), json=self.payload(approver="stranger")
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "GateApproverNotAuthorizedError"
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertIsNone(reloaded.decision_for(0))

    def test_a_self_approved_gate_is_rejected(self) -> None:
        response = self.client.post(
            self.url(), json=self.payload(proposed_by=APPROVER)
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "SelfApprovalError"
        )

    def test_a_recorded_gate_is_not_visible_to_another_client(self) -> None:
        self.assertEqual(
            self.client.post(self.url(), json=self.payload()).status_code, 201
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        other = self.repository.load(
            stage_zero_to_ten_template(), OTHER_TENANT
        )
        self.assertIsNone(other.decision_for(0))
        self.assertFalse(other.has_passing_decision(0, on=date(2026, 10, 2)))


if __name__ == "__main__":
    unittest.main()
