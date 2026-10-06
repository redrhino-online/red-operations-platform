"""End-to-end proof of SPEC.md section 13 definition-of-done condition 1.

Condition 1: one client (the 3F pilot) runs stage 0 through stage 10 through the
REST API, and every gate pins an exact approved asset version. This suite drives
the real FastAPI app over HTTP (``TestClient``) from stage 0 "Intake" to stage 10
"Performance Baseline Established", then reads the production-manager view back
through the real query use case and inspects the durable ``GateLedger`` to prove
each of the eleven gates pinned an exact version.

The stage 0-9 gate payloads and the stage 10 baseline payload are reused from the
existing route tests (``tests/unit/test_stage_ten_gate_route.py``, which itself
chains back through the earlier stage route tests) so this suite cannot drift
from the pipelined upstream content those suites already exercise. The HTTP
boundary, the application handlers, the domain policies and the tenant-scoped
repository ports are all real; only the outer infrastructure adapters are the
in-memory reference implementations, so the suite is deterministic and needs no
database. The durable PostgreSQL adapter is covered separately by
``tests/unit/governance/test_gate_ledger_postgres.py`` (SPEC.md section 13
condition 4).

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest

TENANT = "client-3f"
ON = "2026-10-03"


class StageZeroToTenE2ETests(unittest.TestCase):
    """The 3F pilot runs intake to Performance Baseline over the REST API."""

    @classmethod
    def setUpClass(cls) -> None:
        from tests.unit.test_stage_ten_gate_route import (
            StageTenGateRouteTests,
        )

        try:
            StageTenGateRouteTests.setUpClass()
        except unittest.SkipTest:
            raise
        cls._driver_class = StageTenGateRouteTests

    def setUp(self) -> None:
        # Compose the stage 10 route test as a fixture: it builds the real app,
        # seeds the tenant-scoped in-memory ports, exposes the stage 0-9 seed
        # helper and the stage 10 payload builder.
        self.driver = self._driver_class(
            "test_a_passing_gate_is_recorded_and_pins_exact_versions"
        )
        self.driver.setUp()
        self.client = self.driver.client
        self.repository = self.driver.repository
        self.run_repository = self.driver.run_repository

    def tearDown(self) -> None:
        self.driver.tearDown()

    def test_intake_to_performance_baseline_pins_every_gate(self) -> None:
        self.driver.seed_through_stage_nine()

        payload = self.driver.payload()
        engagement = payload["workspace_id"]

        response = self.client.post(
            f"/red/clients/{TENANT}/stages/10/gate", json=payload
        )

        self.assertEqual(response.status_code, 201, response.text)
        decision = response.json()
        self.assertEqual(decision["stage_number"], 10)
        self.assertEqual(
            decision["checkpoint"], "Performance Baseline Established"
        )
        self.assertEqual(decision["disposition"], "approved")
        self.assertEqual(decision["tenant_id"], TENANT)

        # The production view is the same read model an operator sees. With the
        # whole pipeline approved it reports no blocked stage and no next
        # approval: the engagement is in post-launch measurement, not done
        # (SPEC.md section 4).
        view_response = self.client.get(
            f"/red/clients/{TENANT}/engagements/{engagement}/production-view",
            params={"on": ON},
        )
        self.assertEqual(view_response.status_code, 200, view_response.text)
        view = view_response.json()

        self.assertEqual(11, len(view["stages"]))
        self.assertEqual(11, view["progress"]["approved_gates"])
        self.assertEqual(0, view["progress"]["gates_remaining"])
        self.assertIsNone(view["current_stage_number"])
        self.assertIsNone(view["next_approval_stage_number"])
        for stage in view["stages"]:
            self.assertTrue(stage["is_approved"], stage)
            self.assertEqual("approved", stage["status"], stage)
            self.assertEqual([], stage["missing_asset_kinds"], stage)
            self.assertEqual(
                {asset["asset_id"] for asset in stage["approved_assets"]},
                set(stage["required_asset_kinds"]),
                stage,
            )

        # Every gate pinned an exact approved asset version in the durable
        # ledger, not merely an activity entry.
        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        ledger = self.repository.load(stage_zero_to_ten_template(), TENANT)
        for stage_number in range(11):
            recorded = ledger.decision_for(stage_number)
            self.assertIsNotNone(recorded, f"stage {stage_number} unpinned")
            self.assertEqual(TENANT, recorded.tenant_id)
            self.assertTrue(
                recorded.required_assets,
                f"stage {stage_number} pinned no assets",
            )
            self.assertTrue(
                all(asset.version == 1 for asset in recorded.required_assets),
                f"stage {stage_number} pinned a non-exact version",
            )
            self.assertTrue(
                all(
                    approval.outcome.value == "approved"
                    for approval in recorded.asset_approvals
                ),
                f"stage {stage_number} carries an unapproved asset",
            )


RED_TENANT = "3fmindset"


class RedAgentProviderPathE2ETests(unittest.TestCase):
    """Condition 5: the deterministic fake gateway drives the 3F agent path.

    SPEC.md section 13 condition 5 requires the agent path to run
    deterministically in e2e through a fake model gateway. This class drives the
    RED Director and every chartered specialist through the ``ModelGateway`` port
    with ``DeterministicFakeModelGateway`` for the 3F workspace, and proves the
    fork's specialist registry (which the vendor overlay registers RED agents
    into, ADR 0006/0011) exposes them. No network and no credential is used.
    """

    def test_routes_every_red_agent_through_the_fake_gateway(self) -> None:
        from redops.agents.application.registry import RedAgentRegistry
        from redops.agents.application.router import RedAgentRouter
        from redops.agents.infrastructure.fake_gateway import (
            DeterministicFakeModelGateway,
        )

        gateway = DeterministicFakeModelGateway()
        router = RedAgentRouter(gateway)
        responses = router.route_all(
            "draft the stage 1 diagnosis for the 3F pilot",
            tenant_id=RED_TENANT,
            trace_id="trace-3f-e2e",
        )

        registry = RedAgentRegistry.canonical()
        self.assertEqual(set(registry.keys()), set(responses))
        self.assertEqual(12, len(responses))
        self.assertEqual(12, len(gateway.calls))
        for key, response in responses.items():
            agent = registry.get(key)
            self.assertEqual(agent.model, response.model, key)
            self.assertEqual(agent.prompt_version, response.prompt_version, key)
            self.assertEqual("trace-3f-e2e", response.trace_id, key)

    def test_fork_registry_exposes_the_red_specialists(self) -> None:
        try:
            from openexecutive.agents.redops_agents import (
                RED_SPECIALIST_REGISTRY,
            )
            from openexecutive.orchestrator.router import (
                SPECIALIST_DESCRIPTIONS,
                SPECIALIST_REGISTRY,
                SPECIALIST_TOOLS,
            )
        except ImportError as exc:  # pragma: no cover - domain-only interpreter
            self.skipTest(f"vendored openexecutive unavailable: {exc}")

        red_keys = set(RED_SPECIALIST_REGISTRY)
        self.assertEqual(9, len(red_keys))
        self.assertEqual(red_keys, set(SPECIALIST_REGISTRY))
        self.assertEqual(red_keys, set(SPECIALIST_DESCRIPTIONS))
        tool_keys = set(
            SPECIALIST_TOOLS[0]["input_schema"]["properties"]["specialist"]["enum"]
        )
        self.assertEqual(red_keys, tool_keys)
        self.assertNotIn("cso", SPECIALIST_REGISTRY)
        self.assertNotIn("cfo", SPECIALIST_REGISTRY)

        from openexecutive.orchestrator.answer_sources import _AREAS
        self.assertEqual(red_keys, set(_AREAS))



if __name__ == "__main__":
    unittest.main()
