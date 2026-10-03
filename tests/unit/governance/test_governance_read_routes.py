"""HTTP-boundary behavioral tests for the governance read routes (SPEC.md section 7).

SPEC.md section 7 lists ``/approvals`` and ``/decisions``; section 3 makes a
Decision an append-only record and an ApprovalRequest a version-specific,
scoped approval; section 9 requires every tenant resource query to carry
``tenant_id`` and every list endpoint to enforce client access and pagination.
These tests drive the real FastAPI app against a fresh in-memory gate ledger
after recording a real stage 0 gate, so the routes read the durable decision and
its exact-version approvals, another client sees nothing, and the tenant
parameter is mandatory.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest

TENANT = "3fmindset"
OTHER_TENANT = "client-other"
OWNER = "owner-1"
APPROVER = "approver-1"
SCOPE = "downstream production use"
ON = "2026-10-02"
DUE = "2026-10-09"
CORRELATION = "corr-intake-1"


class GovernanceReadRouteTests(unittest.TestCase):
    """Decisions and approvals are read from the durable tenant-scoped ledger."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import (
                get_client_workspace_store,
                get_gate_ledger_repository,
                get_stage_run_repository,
            )
            from redops.contexts.engagement.infrastructure.repositories import (
                InMemoryClientWorkspaceStore,
            )
            from redops.contexts.governance.infrastructure.repositories import (
                InMemoryGateLedgerRepository,
                InMemoryStageRunRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.dependency = staticmethod(get_gate_ledger_repository)
        cls.run_dependency = staticmethod(get_stage_run_repository)
        cls.workspace_dependency = staticmethod(get_client_workspace_store)
        cls.repository_class = staticmethod(InMemoryGateLedgerRepository)
        cls.run_repository_class = staticmethod(InMemoryStageRunRepository)
        cls.workspace_store_class = staticmethod(InMemoryClientWorkspaceStore)

    def setUp(self) -> None:
        from tests.unit.workspace_fixture import register_workspace

        self.app = self.create_app()
        self.repository = self.repository_class()
        self.run_repository = self.run_repository_class()
        self.workspaces = self.workspace_store_class()
        self.app.dependency_overrides[self.dependency] = lambda: self.repository
        self.app.dependency_overrides[self.run_dependency] = (
            lambda: self.run_repository
        )
        self.app.dependency_overrides[self.workspace_dependency] = (
            lambda: self.workspaces
        )
        self.client = self.test_client(self.app)
        register_workspace(
            self.client,
            tenant_id=TENANT,
            owner=OWNER,
            approver=APPROVER,
        )

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def payload(**overrides):
        from redops.contexts.engagement.domain.value_objects import (
            CANONICAL_INTAKE_KINDS,
        )

        body = {
            "workspace_id": "ws-3f",
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

    def seed_stage_zero(self) -> None:
        response = self.client.post(
            f"/red/clients/{TENANT}/stages/0/gate", json=self.payload()
        )
        self.assertEqual(201, response.status_code, response.text)

    def test_the_decisions_route_lists_the_recorded_decision(self) -> None:
        self.seed_stage_zero()

        listed = self.client.get("/red/decisions", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        body = listed.json()
        self.assertEqual(1, body["total"])
        decision = body["decisions"][0]
        self.assertEqual(0, decision["stage_number"])
        self.assertEqual("approved", decision["disposition"])
        self.assertEqual(APPROVER, decision["reviewer"])
        self.assertEqual(SCOPE, decision["scope"])
        self.assertEqual(TENANT, decision["tenant_id"])
        self.assertEqual(ON, decision["decided_on"])

        from redops.contexts.engagement.domain.value_objects import (
            CANONICAL_INTAKE_KINDS,
        )

        self.assertEqual(
            {asset["asset_id"] for asset in decision["required_assets"]},
            {kind.value for kind in CANONICAL_INTAKE_KINDS},
        )
        self.assertTrue(
            all(asset["version"] == 1 for asset in decision["required_assets"])
        )

    def test_a_decision_is_not_visible_to_another_client(self) -> None:
        self.seed_stage_zero()

        listed = self.client.get(
            "/red/decisions", params={"tenant_id": OTHER_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["decisions"])

    def test_the_approvals_route_lists_exact_version_approvals(self) -> None:
        self.seed_stage_zero()

        listed = self.client.get("/red/approvals", params={"tenant_id": TENANT})

        self.assertEqual(200, listed.status_code, listed.text)
        body = listed.json()
        self.assertEqual(
            len(body["approvals"]), body["total"]
        )
        self.assertGreater(body["total"], 0)
        for approval in body["approvals"]:
            self.assertEqual(1, approval["version"])
            self.assertEqual(SCOPE, approval["scope"])
            self.assertEqual(APPROVER, approval["approver"])
            self.assertEqual(OWNER, approval["requested_by"])
            self.assertEqual("approved", approval["outcome"])
            self.assertEqual(0, approval["stage_number"])
            self.assertEqual(ON, approval["decided_on"])

    def test_an_approval_is_not_visible_to_another_client(self) -> None:
        self.seed_stage_zero()

        listed = self.client.get(
            "/red/approvals", params={"tenant_id": OTHER_TENANT}
        )

        self.assertEqual(200, listed.status_code, listed.text)
        self.assertEqual(0, listed.json()["total"])
        self.assertEqual([], listed.json()["approvals"])

    def test_the_tenant_parameter_is_required_on_both_routes(self) -> None:
        decisions = self.client.get("/red/decisions")
        approvals = self.client.get("/red/approvals")

        self.assertEqual(422, decisions.status_code, decisions.text)
        self.assertEqual(422, approvals.status_code, approvals.text)

    def test_pagination_is_applied_after_tenant_scoping(self) -> None:
        self.seed_stage_zero()

        page = self.client.get(
            "/red/approvals",
            params={"tenant_id": TENANT, "limit": 2, "offset": 1},
        )

        self.assertEqual(200, page.status_code, page.text)
        body = page.json()
        self.assertGreater(body["total"], 2)
        self.assertEqual(2, body["limit"])
        self.assertEqual(1, body["offset"])
        self.assertEqual(2, len(body["approvals"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
