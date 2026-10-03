"""Cross-tenant isolation security suite for SPEC.md section 13 condition 3.

Condition 3 requires that cross tenant isolation holds at the API, retrieval,
background worker and artifact URL layers. This suite covers the API layer that
exists in the running platform today: the stage 0-10 gate write routes and the
production-manager view read route, together with the tenant-scoped
``GateLedgerRepository`` and ``StageRunRepository`` ports they sit on. It drives
the real FastAPI app over HTTP and proves that a gate decision, a stage run and a
progress projection recorded for one client are invisible to another client,
that a stage gate prerequisite is enforced per client so one client's approvals
never satisfy another client's gate, that an unauthorized approver is rejected
over the API without a write, and that the durable seams refuse an unscoped
(blank-tenant) read.

The retrieval, background worker and artifact URL layers named by condition 3 do
not exist yet (there is no retrieval port, worker entry point or artifact-serving
route), so they are recorded as an open gap in the implementation plan rather
than tested here; coverage must be added when those seams are built. The suite
adds no rule: the pure domain, the application use cases and the repository ports
decide behaviour.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest

TENANT = "client-3f"
OTHER_TENANT = "client-other"
ENGAGEMENT = "ws-3f"
ON = "2026-10-03"


class CrossTenantIsolationTests(unittest.TestCase):
    """One client's gate progress never crosses into another client's scope."""

    @classmethod
    def setUpClass(cls) -> None:
        from tests.unit.test_stage_ten_gate_route import (
            StageTenGateRouteTests,
        )

        try:
            StageTenGateRouteTests.setUpClass()
        except unittest.SkipTest:
            raise
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls._driver_class = StageTenGateRouteTests

    def setUp(self) -> None:
        # Compose the stage 10 route test as a fixture: it builds the real app,
        # seeds the tenant-scoped in-memory ports and exposes the stage 0-9 seed
        # helper, the stage 10 payload builder and the earlier stage payloads.
        self.driver = self._driver_class(
            "test_a_passing_gate_is_recorded_and_pins_exact_versions"
        )
        self.driver.setUp()
        self.client = self.driver.client
        self.repository = self.driver.repository
        self.run_repository = self.driver.run_repository

    def tearDown(self) -> None:
        self.driver.tearDown()

    def _seed_full_pipeline(self, tenant_id: str = TENANT) -> None:
        """Seed stages 0 through 10 for one client through its own routes."""

        self.driver.seed_through_stage_nine(tenant_id=tenant_id)
        response = self.client.post(
            f"/red/clients/{tenant_id}/stages/10/gate",
            json=self.driver.payload(),
        )
        self.assertEqual(response.status_code, 201, response.text)

    def _template(self):
        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        return stage_zero_to_ten_template()

    def test_production_view_does_not_leak_another_clients_pipeline(self) -> None:
        self._seed_full_pipeline(TENANT)

        own = self.client.get(
            f"/red/clients/{TENANT}/engagements/{ENGAGEMENT}/production-view",
            params={"on": ON},
        )
        self.assertEqual(own.status_code, 200, own.text)
        self.assertEqual(11, own.json()["progress"]["approved_gates"])

        other = self.client.get(
            f"/red/clients/{OTHER_TENANT}/engagements/{ENGAGEMENT}"
            "/production-view",
            params={"on": ON},
        )
        self.assertEqual(other.status_code, 200, other.text)
        view = other.json()
        self.assertEqual(OTHER_TENANT, view["tenant_id"])
        self.assertEqual(0, view["progress"]["approved_gates"])
        self.assertIsNotNone(view["current_stage_number"])
        for stage in view["stages"]:
            self.assertFalse(stage["is_approved"], stage)
            self.assertEqual([], stage["approved_assets"], stage)

    def test_stage_gate_prerequisite_is_scoped_to_the_client(self) -> None:
        self._seed_full_pipeline(TENANT)

        # The other client has no passing stage 0, so its stage 1 gate is
        # refused even though the first client's whole pipeline is approved.
        # Register its workspace first: the gate resolves the authority registry
        # from the durable store, so an unregistered workspace would be a 404
        # rather than the prerequisite refusal this test asserts.
        self.driver.register_workspace(OTHER_TENANT)
        six = self.driver._nine._eight._seven._six
        response = self.client.post(
            f"/red/clients/{OTHER_TENANT}/stages/1/gate",
            json=six.stage_one_payload(),
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "GateDecisionError"
        )
        other_ledger = self.repository.load(self._template(), OTHER_TENANT)
        self.assertIsNone(other_ledger.decision_for(0))
        self.assertIsNone(other_ledger.decision_for(1))

    def test_gate_decisions_are_invisible_through_another_clients_ledger(
        self,
    ) -> None:
        self._seed_full_pipeline(TENANT)

        other_ledger = self.repository.load(self._template(), OTHER_TENANT)
        for stage_number in range(11):
            self.assertIsNone(other_ledger.decision_for(stage_number))

        own_ledger = self.repository.load(self._template(), TENANT)
        for stage_number in range(11):
            decision = own_ledger.decision_for(stage_number)
            self.assertIsNotNone(decision)
            self.assertEqual(TENANT, decision.tenant_id)

    def test_stage_runs_are_scoped_to_the_client(self) -> None:
        self._seed_full_pipeline(TENANT)

        for stage_number in range(11):
            self.assertIsNotNone(
                self.run_repository.load(
                    self._template().version,
                    ENGAGEMENT,
                    stage_number,
                    TENANT,
                )
            )
            self.assertIsNone(
                self.run_repository.load(
                    self._template().version,
                    ENGAGEMENT,
                    stage_number,
                    OTHER_TENANT,
                )
            )

    def test_an_unscoped_gate_read_is_refused(self) -> None:
        from redops.contexts.governance.domain.errors import (
            CrossTenantGateError,
            CrossTenantStageRunError,
        )

        with self.assertRaises(CrossTenantGateError):
            self.repository.load(self._template(), "")

        with self.assertRaises(CrossTenantStageRunError):
            self.run_repository.load(
                self._template().version, ENGAGEMENT, 0, "  "
            )

    def test_an_unauthorized_approver_is_rejected_without_a_write(self) -> None:
        from redops.contexts.governance.domain.errors import (
            CrossTenantGateError,
        )

        six = self.driver._nine._eight._seven._six
        payload = six.stage_zero_payload()
        payload["approver"] = "stranger"
        # Register the other client's workspace so the refusal is the authority
        # check (the persisted registry does not name the stranger), not a
        # missing-workspace 404.
        self.driver.register_workspace(OTHER_TENANT)
        response = self.client.post(
            f"/red/clients/{OTHER_TENANT}/stages/0/gate", json=payload
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"],
            "GateApproverNotAuthorizedError",
        )
        # The rejected approval leaves no partial write, and an unscoped read
        # is refused rather than returning everything.
        other_ledger = self.repository.load(self._template(), OTHER_TENANT)
        self.assertIsNone(other_ledger.decision_for(0))
        with self.assertRaises(CrossTenantGateError):
            self.repository.load(self._template(), "")


if __name__ == "__main__":
    unittest.main()
