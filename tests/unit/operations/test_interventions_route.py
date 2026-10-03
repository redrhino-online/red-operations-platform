"""HTTP-boundary behavioral tests for the intervention route (SPEC.md section 7).

SPEC.md section 7 lists ``/interventions``, requires the command center to
surface, per client, the blocked critical path and overdue approvals, to
deduplicate them and to allow dismissal with rationale; section 9 requires every
tenant resource query to carry ``tenant_id``. These tests drive the real FastAPI
app, the real production-view use case and the real ranking policy against fresh
in-memory gate and dismissal stores, so a card is derived only from the client's
own ledger and a dismissal is durable and tenant-scoped.

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


class InterventionsRouteTests(unittest.TestCase):
    """The intervention surface is a tenant-scoped read and a durable dismissal."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient

            from redops.api.app import create_app
            from redops.api.routes import (
                get_gate_ledger_repository,
                get_intervention_dismissal_repository,
                get_stage_run_repository,
            )
            from redops.contexts.governance.infrastructure.repositories import (
                InMemoryGateLedgerRepository,
                InMemoryStageRunRepository,
            )
            from redops.contexts.operations.infrastructure.repositories import (
                InMemoryInterventionDismissalRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.ledger_dependency = staticmethod(get_gate_ledger_repository)
        cls.run_dependency = staticmethod(get_stage_run_repository)
        cls.dismissal_dependency = staticmethod(
            get_intervention_dismissal_repository
        )
        cls.ledger_class = staticmethod(InMemoryGateLedgerRepository)
        cls.run_class = staticmethod(InMemoryStageRunRepository)
        cls.dismissal_class = staticmethod(
            InMemoryInterventionDismissalRepository
        )

    def setUp(self) -> None:
        self.app = self.create_app()
        self.ledger = self.ledger_class()
        self.runs = self.run_class()
        self.dismissals = self.dismissal_class()
        self.app.dependency_overrides[self.ledger_dependency] = lambda: self.ledger
        self.app.dependency_overrides[self.run_dependency] = lambda: self.runs
        self.app.dependency_overrides[self.dismissal_dependency] = (
            lambda: self.dismissals
        )
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    @staticmethod
    def blocked_decision(stage_number: int):
        from redops.contexts.governance.domain.entities import GateDecision
        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )
        from redops.contexts.governance.domain.value_objects import (
            AssetVersionRef,
            GateDisposition,
        )

        template = stage_zero_to_ten_template(VERSION)
        definition = template.definition_for(stage_number)
        assets = frozenset(
            AssetVersionRef(kind, 1)
            for kind in template.required_asset_kinds(stage_number)
        )
        return GateDecision(
            stage_number=stage_number,
            template_version=VERSION,
            required_assets=assets,
            checkpoint=definition.checkpoint,
            checkpoint_evidence="",
            reviewer="production-manager",
            scope="",
            disposition=GateDisposition.BLOCKED,
            rationale="blocked for the intervention route",
            decided_on=TODAY,
            assigned_owner="production-manager",
            due_on=date(2026, 10, 16),
            dependencies=template.dependencies_of(stage_number),
            next_action="resolve the blocker",
            blockers=frozenset({"required asset versions not approved"}),
            tenant_id=TENANT,
        )

    def read(self, tenant_id: str = TENANT):
        return self.client.get(
            "/red/interventions",
            params={
                "tenant_id": tenant_id,
                "engagement": ENGAGEMENT,
                "on": ON.isoformat(),
            },
        )

    def dismiss_body(self, **overrides):
        body = {
            "tenant_id": TENANT,
            "client": ENGAGEMENT,
            "reason": "blocked_critical_path",
            "subject": "stage-0",
            "rationale": "the blocker is being handled off-platform",
            "actor": "production-manager",
            "dismissed_on": ON.isoformat(),
        }
        body.update(overrides)
        return body

    def test_a_blocked_stage_surfaces_a_ranked_card(self) -> None:
        self.ledger.append(self.blocked_decision(0))

        response = self.read()

        self.assertEqual(200, response.status_code, response.text)
        payload = response.json()
        self.assertEqual(TENANT, payload["tenant_id"])
        self.assertEqual(ENGAGEMENT, payload["engagement"])
        self.assertEqual(1, payload["total"])
        card = payload["interventions"][0]
        self.assertEqual("blocked_critical_path", card["reason"])
        self.assertEqual("critical", card["severity"])
        self.assertEqual("production-manager", card["owner"])
        self.assertEqual("open", card["state"])
        self.assertIn("required asset versions not approved", card["evidence"])

    def test_a_dismissed_card_is_returned_with_its_rationale(self) -> None:
        self.ledger.append(self.blocked_decision(0))

        recorded = self.client.post(
            "/red/interventions/dismiss", json=self.dismiss_body()
        )

        self.assertEqual(201, recorded.status_code, recorded.text)
        self.assertEqual(
            "the blocker is being handled off-platform",
            recorded.json()["rationale"],
        )

        response = self.read()

        self.assertEqual(200, response.status_code, response.text)
        card = response.json()["interventions"][0]
        self.assertEqual("dismissed", card["state"])
        self.assertEqual(
            "the blocker is being handled off-platform", card["resolution_note"]
        )

    def test_a_card_is_not_surfaced_for_another_client(self) -> None:
        self.ledger.append(self.blocked_decision(0))

        response = self.read(OTHER_TENANT)

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(0, response.json()["total"])

    def test_the_tenant_parameter_is_required(self) -> None:
        response = self.client.get(
            "/red/interventions",
            params={"engagement": ENGAGEMENT, "on": ON.isoformat()},
        )

        self.assertEqual(422, response.status_code, response.text)

    def test_a_same_key_different_dismissal_is_a_409(self) -> None:
        self.client.post("/red/interventions/dismiss", json=self.dismiss_body())

        conflict = self.client.post(
            "/red/interventions/dismiss",
            json=self.dismiss_body(rationale="a different reason"),
        )

        self.assertEqual(409, conflict.status_code, conflict.text)
        self.assertEqual(
            "InterventionDismissalConflictError",
            conflict.json()["detail"]["error"],
        )

    def test_a_dismissal_without_a_rationale_is_refused(self) -> None:
        response = self.client.post(
            "/red/interventions/dismiss",
            json=self.dismiss_body(rationale="   "),
        )

        self.assertEqual(422, response.status_code, response.text)
        self.assertEqual(
            "InvalidInterventionDismissalError",
            response.json()["detail"]["error"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
