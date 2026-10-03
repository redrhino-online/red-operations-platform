"""HTTP-boundary behavioral tests for the stage 2 gate route.

SPEC.md section 6 requires the API to call use cases through ports and never
mutate persistence directly; SPEC.md section 7 makes the stage gate an explicit
REST resource; SPEC.md section 11 lists as minimum acceptance scenarios both
"unauthorized approval is rejected" and "a different client's retrieval produces
no result". SPEC.md section 4 makes the stage 2 "Currency Locked" gate depend on
a passing stage 1 decision, so these tests drive the real FastAPI app, seed
stages 0 and 1 through their own routes, then record stage 2 through the
tenant-scoped ``GateLedgerRepository`` and ``StageRunRepository`` ports
(substituted with fresh in-memory adapters).

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest


TENANT = "client-3f"
OTHER_TENANT = "client-other"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE = "stage-3-model"
CORRELATION = "corr-stage-2"
ON = "2026-10-03"
DUE = "2026-10-17"


class StageTwoGateRouteTests(unittest.TestCase):
    """The stage 2 gate is recorded only through the domain use case and port."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import (
                get_gate_ledger_repository,
                get_stage_run_repository,
            )
            from redops.contexts.commercial.domain.value_objects import (
                CANONICAL_CURRENCY_KINDS,
                CANONICAL_DIAGNOSIS_KINDS,
            )
            from redops.contexts.engagement.domain.value_objects import (
                CANONICAL_INTAKE_KINDS,
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
        cls.repository_class = staticmethod(InMemoryGateLedgerRepository)
        cls.run_repository_class = staticmethod(InMemoryStageRunRepository)
        cls.intake_kinds = CANONICAL_INTAKE_KINDS
        cls.diagnosis_kinds = CANONICAL_DIAGNOSIS_KINDS
        cls.currency_kinds = CANONICAL_CURRENCY_KINDS

    def setUp(self) -> None:
        self.app = self.create_app()
        self.repository = self.repository_class()
        self.run_repository = self.run_repository_class()
        self.app.dependency_overrides[self.dependency] = lambda: self.repository
        self.app.dependency_overrides[self.run_dependency] = (
            lambda: self.run_repository
        )
        self.client = self.test_client(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def _authorities(self):
        return [
            {"actor": OWNER, "authority": "production-owner"},
            {"actor": APPROVER, "authority": "client-designated-authority"},
        ]

    def stage_zero_payload(self):
        return {
            "workspace_id": "ws-3f",
            "authorities": self._authorities(),
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
                for kind in self.intake_kinds
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
            "scope": "stage-1-diagnosis",
            "checkpoint_evidence": "all stage 0 assets reviewed",
            "rationale": "intake complete and owned",
            "assigned_owner": OWNER,
            "due_on": "2026-10-02",
            "on": "2026-10-02",
            "correlation_id": "corr-stage-0",
        }

    def stage_one_payload(self):
        return {
            "workspace_id": "ws-3f",
            "authorities": self._authorities(),
            "diagnosis_package_id": "diagnosis-3f",
            "avatar": {
                "avatar_id": "avatar-3f",
                "version": 1,
                "name": "Owner-operator of a small service firm",
                "demographics": "35-50, runs a small local service firm",
                "psychographics": "proud of craft, skeptical of marketing",
                "pains": ["feast and famine pipeline"],
                "goals": ["predictable qualified demand"],
                "consequences_of_inaction": [
                    "hires then lays off as work dries up"
                ],
                "awareness": "problem aware, not solution aware",
                "customer_evidence_claim_ids": ["claim-voice-1"],
                "voice_notes": [
                    "I cannot plan payroll when the phone is quiet"
                ],
            },
            "business_snapshot": {
                "snapshot_id": "snapshot-3f",
                "version": 1,
                "business_model": "project based service work billed hourly",
                "current_offers": ["hourly support retainer"],
                "lead_sources": ["referrals"],
                "constraints": ["two delivery people, no marketing owner"],
                "narrative": "Steady referrals but no predictable pipeline",
                "evidence_claim_ids": ["claim-offer-1"],
            },
            "offer_funnel_audit": {
                "audit_id": "audit-3f",
                "version": 1,
                "offer_findings": ["the retainer has no stated outcome"],
                "funnel_steps": ["referral", "call", "quote", "project"],
                "conversion_evidence": [
                    "quotes are tracked in a spreadsheet"
                ],
                "gaps": ["no qualification step before the call"],
                "narrative": "The funnel has no owner between referral and quote",
                "evidence_claim_ids": ["claim-offer-2"],
            },
            "claims": [
                {
                    "claim_id": claim_id,
                    "statement": "Stage 1 diagnosis fact recorded with the client",
                    "provenance": "known",
                    "confidence_note": "captured during diagnosis",
                    "citations": [
                        {
                            "source_id": "source-diagnosis",
                            "checksum": "sha256:def",
                            "location": "p.2",
                        }
                    ],
                }
                for claim_id in (
                    "claim-voice-1",
                    "claim-offer-1",
                    "claim-offer-2",
                )
            ],
            "stage_owner": OWNER,
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": "stage-2-position",
            "checkpoint_evidence": "all nine stage 1 assets reviewed",
            "rationale": "avatar locked and owned",
            "assigned_owner": OWNER,
            "due_on": "2026-10-02",
            "on": "2026-10-02",
            "correlation_id": "corr-stage-1",
        }

    def payload(self, **overrides):
        body = {
            "workspace_id": "ws-3f",
            "authorities": self._authorities(),
            "currency_package_id": "currency-3f",
            "inventory": {
                "inventory_id": "inventory-3f",
                "version": 1,
                "category": "marketing operations for service firms",
                "currencies_to_increase": ["qualified leads", "margin"],
                "currencies_to_decrease": ["cost per lead", "owner hours"],
            },
            "positioning": {
                "decision_id": "positioning-3f",
                "version": 1,
                "core_problem": "referrals are unpredictable and unmeasurable",
                "transformation_statement": (
                    "a predictable qualified demand pipeline the owner controls"
                ),
                "horizon": "90 days",
                "qualifications": ["has a delivery team already"],
                "disqualifications": ["wants done-for-you sales calls"],
            },
            "primary_currency": {
                "currency": "qualified sales conversations",
                "version": 1,
                "audience": "owner-operators of small local service firms",
                "current_measure": "3 per month from referrals",
                "desired_measure": "12 per month on a repeatable path",
                "mechanism": "a positioned diagnostic offer with one CTA",
            },
            "million_dollar_message": {
                "message_id": "mdm-3f",
                "version": 1,
                "avatar": "owner-operator of a small local service firm",
                "currency": "qualified sales conversations",
                "metric": "3 to 12 per month",
                "timeline": "90 days",
                "pain": "feast and famine pipeline",
                "message": (
                    "Owner-operators of small local service firms get from 3 "
                    "to 12 qualified sales conversations a month in 90 days "
                    "without feast-and-famine referrals"
                ),
            },
            "stage_owner": OWNER,
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE,
            "checkpoint_evidence": "all ten stage 2 assets reviewed",
            "rationale": "one primary currency locked and owned",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        body.update(overrides)
        return body

    def url(self, tenant_id: str = TENANT) -> str:
        return f"/red/clients/{tenant_id}/stages/2/gate"

    def seed_stage_one(self, tenant_id: str = TENANT) -> None:
        response = self.client.post(
            f"/red/clients/{tenant_id}/stages/0/gate",
            json=self.stage_zero_payload(),
        )
        self.assertEqual(response.status_code, 201, response.text)
        response = self.client.post(
            f"/red/clients/{tenant_id}/stages/1/gate",
            json=self.stage_one_payload(),
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_a_passing_gate_is_recorded_and_pins_exact_versions(self) -> None:
        self.seed_stage_one()

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)
        decision = response.json()
        self.assertEqual(decision["stage_number"], 2)
        self.assertEqual(decision["checkpoint"], "Currency Locked")
        self.assertEqual(decision["disposition"], "approved")
        self.assertEqual(decision["reviewer"], APPROVER)
        self.assertEqual(decision["tenant_id"], TENANT)
        self.assertEqual(
            {asset["asset_id"] for asset in decision["required_assets"]},
            {kind for kind in self.currency_kinds},
        )
        self.assertTrue(
            all(asset["version"] == 1 for asset in decision["required_assets"])
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        decision_two = reloaded.decision_for(2)
        self.assertIsNotNone(decision_two)
        self.assertEqual(
            {asset.asset_id for asset in decision_two.required_assets},
            set(self.currency_kinds),
        )

    def test_the_stage_run_is_persisted_with_its_completion(self) -> None:
        self.seed_stage_one()

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )
        from redops.contexts.governance.domain.value_objects import StageStatus

        run = self.run_repository.load(
            stage_zero_to_ten_template().version, "ws-3f", 2, TENANT
        )
        self.assertIsNotNone(run)
        self.assertEqual(StageStatus.COMPLETE, run.status)
        self.assertEqual(OWNER, run.assigned_owner)
        self.assertEqual(TENANT, run.tenant_id)

    def test_a_stage_two_gate_without_a_passing_stage_one_is_rejected(
        self,
    ) -> None:
        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "GateDecisionError"
        )

    def test_an_unauthorized_approver_is_rejected_without_a_write(self) -> None:
        self.seed_stage_one()

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
        self.assertIsNone(reloaded.decision_for(2))

    def test_a_stage_two_decision_is_not_visible_to_another_client(self) -> None:
        self.seed_stage_one()
        self.assertEqual(
            self.client.post(self.url(), json=self.payload()).status_code, 201
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        other = self.repository.load(
            stage_zero_to_ten_template(), OTHER_TENANT
        )
        self.assertIsNone(other.decision_for(2))


if __name__ == "__main__":
    unittest.main()
