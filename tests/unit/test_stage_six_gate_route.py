"""HTTP-boundary behavioral tests for the stage 6 gate route.

SPEC.md section 6 requires the API to call use cases through ports and never
mutate persistence directly; SPEC.md section 7 makes the stage gate an explicit
REST resource; SPEC.md section 11 lists as minimum acceptance scenarios both
"unauthorized approval is rejected" and "a different client's retrieval produces
no result". SPEC.md section 4 makes the stage 6 "Campaign Message Approved" gate
depend on a passing stage 5 decision, so these tests drive the real FastAPI app,
seed stages 0 through 5 through their own routes, then record stage 6 through the
tenant-scoped ``GateLedgerRepository`` and ``StageRunRepository`` ports
(substituted with fresh in-memory adapters).

The checkpoint requires the avatar, currency, problem, promise, method, product
and CTA to agree, so the tests also prove the domain refuses a message that
conflicts with its approved offer.

The entry point imports FastAPI and the vendored ``openexecutive`` package, so
the class skips cleanly when the domain-only interpreter runs the suite.
"""

from __future__ import annotations

import unittest


TENANT = "client-3f"
OTHER_TENANT = "client-other"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE = "stage-7-authority-amplifier"
CORRELATION = "corr-stage-6"
ON = "2026-10-03"
DUE = "2026-10-17"


class StageSixGateRouteTests(unittest.TestCase):
    """The stage 6 gate is recorded only through the domain use case and port."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from redops.api.app import create_app
            from redops.api.routes import (
                get_campaign_message_repository,
                get_gate_ledger_repository,
                get_method_version_repository,
                get_offer_version_repository,
                get_stage_run_repository,
            )
            from redops.contexts.commercial.domain.value_objects import (
                CANONICAL_CURRENCY_KINDS,
                CANONICAL_DIAGNOSIS_KINDS,
                CANONICAL_DIAGNOSTIC_KINDS,
                CANONICAL_MESSAGE_KINDS,
                CANONICAL_OFFER_KINDS,
                CANONICAL_SIGNATURE_KINDS,
            )
            from redops.contexts.engagement.domain.value_objects import (
                CANONICAL_INTAKE_KINDS,
            )
            from redops.contexts.commercial.infrastructure.repositories import (
                InMemoryCampaignMessageRepository,
                InMemoryOfferVersionRepository,
            )
            from redops.contexts.governance.infrastructure.repositories import (
                InMemoryGateLedgerRepository,
                InMemoryStageRunRepository,
            )
            from redops.contexts.method.infrastructure.repositories import (
                InMemoryMethodVersionRepository,
            )
        except Exception as exc:  # pragma: no cover - depends on environment
            raise unittest.SkipTest(
                f"app dependencies unavailable: {exc}"
            ) from exc
        cls.test_client = TestClient
        cls.create_app = staticmethod(create_app)
        cls.dependency = staticmethod(get_gate_ledger_repository)
        cls.run_dependency = staticmethod(get_stage_run_repository)
        cls.method_dependency = staticmethod(get_method_version_repository)
        cls.offer_dependency = staticmethod(get_offer_version_repository)
        cls.message_dependency = staticmethod(
            get_campaign_message_repository
        )
        cls.repository_class = staticmethod(InMemoryGateLedgerRepository)
        cls.run_repository_class = staticmethod(InMemoryStageRunRepository)
        cls.method_repository_class = staticmethod(
            InMemoryMethodVersionRepository
        )
        cls.offer_repository_class = staticmethod(
            InMemoryOfferVersionRepository
        )
        cls.message_repository_class = staticmethod(
            InMemoryCampaignMessageRepository
        )
        cls.intake_kinds = CANONICAL_INTAKE_KINDS
        cls.diagnosis_kinds = CANONICAL_DIAGNOSIS_KINDS
        cls.currency_kinds = CANONICAL_CURRENCY_KINDS
        cls.diagnostic_kinds = CANONICAL_DIAGNOSTIC_KINDS
        cls.signature_kinds = CANONICAL_SIGNATURE_KINDS
        cls.offer_kinds = CANONICAL_OFFER_KINDS
        cls.message_kinds = CANONICAL_MESSAGE_KINDS

    def setUp(self) -> None:
        self.app = self.create_app()
        self.repository = self.repository_class()
        self.run_repository = self.run_repository_class()
        self.method_repository = self.method_repository_class()
        self.offer_repository = self.offer_repository_class()
        self.message_repository = self.message_repository_class()
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
            "awareness_map": {
                "map_id": "awareness-3f",
                "version": 1,
                "primary_level": "problem_aware",
                "research_evidence": ["reviews name the unpredictable pipeline"],
                "message_requirements": [
                    "lead with the predictable pipeline outcome"
                ],
                "retarget_level": "solution_aware",
            },
            "audience_reach_estimate": {
                "estimate_id": "reach-3f",
                "version": 1,
                "owner": OWNER,
                "platform": "facebook_audience_insights",
                "audience": {
                    "location": "United States",
                    "age": "35-50",
                    "gender": "all",
                    "interests": [
                        {"kind": "expert", "value": "small service firm coach"}
                    ],
                },
                "estimated_reach": 180000,
                "source_note": "Facebook Audience Insights sizing",
                "captured_on": ON,
            },
            "target_market_match": {
                "matchmaker_id": "match-3f",
                "version": 1,
                "candidates": [
                    {
                        "market_id": "market-referrals",
                        "name": "Referral-starved service business owners",
                        "passion": "we have run this play inside the trade",
                        "problem": "unpredictable referral flow",
                        "profit": "they already spend on lead generation",
                        "reachability": "active in two owner-operator communities",
                        "pathway": "from a referral drought to a referral partner engine",
                    },
                    {
                        "market_id": "market-coaches",
                        "name": "New executive coaches",
                        "passion": "we coach this transition",
                        "problem": "no repeatable client acquisition",
                        "profit": "they invest in their practice",
                        "reachability": "active in coach communities",
                        "pathway": "from no pipeline to a repeatable acquisition engine",
                    },
                ],
                "selected_market_id": "market-referrals",
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

    def stage_two_payload(self):
        return {
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
            "scope": "stage-3-model",
            "checkpoint_evidence": "all ten stage 2 assets reviewed",
            "rationale": "one primary currency locked and owned",
            "assigned_owner": OWNER,
            "due_on": "2026-10-02",
            "on": "2026-10-02",
            "correlation_id": "corr-stage-2",
        }

    def stage_three_payload(self):
        return {
            "workspace_id": "ws-3f",
            "authorities": self._authorities(),
            "diagnostic_package_id": "diagnostic-model-3f",
            "model": {
                "model_id": "diagnostic-model-3f",
                "version": 1,
                "name": "The Predictable Pipeline Pyramid",
                "levels": [
                    {
                        "level_id": "level-reference",
                        "name": "Referral Dependent",
                        "observable_measures": ["3 conversations per month"],
                        "symptoms": ["quiet weeks between projects"],
                        "behaviors": ["asks for referrals after delivery"],
                        "problems": ["cannot forecast revenue"],
                    },
                    {
                        "level_id": "level-emerging",
                        "name": "Emerging Pipeline",
                        "observable_measures": ["6 conversations per month"],
                        "symptoms": ["some months fill, some do not"],
                        "behaviors": ["runs one offer inconsistently"],
                        "problems": ["lead flow still spikes and stalls"],
                    },
                    {
                        "level_id": "level-systematic",
                        "name": "Systematic Demand",
                        "observable_measures": ["12 conversations per month"],
                        "symptoms": ["pipeline is visible weekly"],
                        "behaviors": ["runs one CTA on a schedule"],
                        "problems": ["still dependent on the owner"],
                    },
                    {
                        "level_id": "level-predictable",
                        "name": "Predictable Demand",
                        "observable_measures": [
                            "12 plus conversations per month"
                        ],
                        "symptoms": ["pipeline covers two months out"],
                        "behaviors": ["delegates the daily funnel checks"],
                        "problems": ["scaling without diluting fit"],
                    },
                ],
                "progression": (
                    "each level adds repeatable demand and removes owner "
                    "dependence"
                ),
                "qualification_logic": (
                    "place by the observable conversations per month"
                ),
                "visual": "a four step pyramid with one measure per tier",
                "explanatory_copy": (
                    "each tier states its measure and its next move"
                ),
            },
            "stage_owner": OWNER,
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": "stage-4-package-ip",
            "checkpoint_evidence": "all ten stage 3 assets reviewed",
            "rationale": "levels are distinguishable by observation and owned",
            "assigned_owner": OWNER,
            "due_on": "2026-10-02",
            "on": "2026-10-02",
            "correlation_id": "corr-stage-3",
        }

    def _step(self, index: int, name: str):
        return {
            "step_id": f"step-{index}",
            "name": name,
            "starting_state": f"state-{index}",
            "final_state": f"state-{index + 1}",
            "inputs": [f"input-{index}"],
            "actions": [f"action-{index}"],
            "outputs": [f"output-{index}"],
        }

    def _solution(self):
        names = [
            "Extract the diagnosis",
            "Draft the map",
            "Name the phases",
            "Write the steps",
            "Bind the inputs",
            "Define the actions",
            "Pin the outputs",
            "Write the narrative",
            "Draw the visual",
        ]
        steps = [self._step(i, name) for i, name in enumerate(names)]
        phases = [
            {
                "phase_id": "phase-extract",
                "name": "Extract",
                "steps": steps[0:3],
            },
            {
                "phase_id": "phase-content",
                "name": "Content",
                "steps": steps[3:6],
            },
            {
                "phase_id": "phase-expand",
                "name": "Expand",
                "steps": steps[6:9],
            },
        ]
        return {
            "solution_id": "signature-3f",
            "version": 1,
            "transformation_map": "from referral chaos to predictable demand",
            "process_inventory": ["discovery", "build", "launch"],
            "phases": phases,
            "starting_state": "state-0",
            "final_state": "state-9",
            "narrative": "nine named stages move the client across three phases",
            "visual": "a three lane map with nine labelled stages",
        }

    def stage_four_payload(self):
        return {
            "workspace_id": "ws-3f",
            "authorities": self._authorities(),
            "signature_package_id": "signature-3f",
            "solution": self._solution(),
            "transformations": {
                "transformations_id": "transformations-3f",
                "version": 1,
                "million_dollar_message": (
                    "from referral chaos to predictable demand in 90 days"
                ),
            },
            "stage_owner": OWNER,
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": "stage-5-productize",
            "checkpoint_evidence": "all twelve stage 4 assets reviewed",
            "rationale": "the transformation is coherent and owned",
            "assigned_owner": OWNER,
            "due_on": "2026-10-02",
            "on": "2026-10-02",
            "correlation_id": "corr-stage-4",
        }

    def _delivery(self):
        return {
            "delivery_id": "delivery-3f",
            "version": 1,
            "signature_solution": self._solution(),
            "delivery_model": "group coaching program",
            "duration": "eight weeks",
            "modules": ["one module per named stage"],
            "responsibilities": ["RED builds the machine", "client serves"],
            "support_cadence": "weekly training and weekly coaching",
            "step_deliveries": [
                {
                    "step_id": f"step-{index}",
                    "action": f"deliver action {index}",
                    "actor": "RED delivery lead",
                    "deliverable": f"deliverable {index}",
                    "timing": f"week {index + 1}",
                    "measure": f"measure {index}",
                }
                for index in range(9)
            ],
            "outcome_measures": ["qualified conversations per month"],
            "pricing_payments": "outcome based fee in three payments",
            "scope": "the full nine step transformation",
            "guarantee_decision": "no guarantee until results are measured",
            "eligibility": "owner-operator with a delivery team",
            "offer_stack": ["diagnostic offer", "core program"],
        }

    def _program(self):
        step_names = [
            "Extract the diagnosis",
            "Draft the map",
            "Name the phases",
            "Write the steps",
            "Bind the inputs",
            "Define the actions",
            "Pin the outputs",
            "Write the narrative",
            "Draw the visual",
        ]
        return {
            "program_id": "program-3f",
            "version": 1,
            "owner": "red-offer-owner",
            "model": "group_consulting",
            "pricing_basis": "outcome_value",
            "duration_weeks": 9,
            "cadence": "monday_training_thursday_coaching",
            "modules": [
                {
                    "module_id": f"module-{index + 1}",
                    "signature_step": name,
                    "position": index + 1,
                    "outcome": f"the client reaches {name}",
                    "deliverable": f"the {name} worksheet",
                }
                for index, name in enumerate(step_names)
            ],
        }

    def stage_five_payload(self):
        return {
            "workspace_id": "ws-3f",
            "authorities": self._authorities(),
            "offer_package_id": "offer-3f",
            "delivery": self._delivery(),
            "product_program": self._program(),
            "stage_owner": OWNER,
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE,
            "checkpoint_evidence": "all thirteen stage 5 assets reviewed",
            "rationale": "every method step is delivered and owned",
            "assigned_owner": OWNER,
            "due_on": "2026-10-02",
            "on": "2026-10-02",
            "correlation_id": "corr-stage-5",
        }

    def _method(self):
        return {
            "method_id": "method-3f",
            "parent_method": "signature-solution",
            "semantic_version": {"major": 1, "minor": 0, "patch": 0},
            "stages": ["diagnose", "position", "model"],
            "currency": "qualified referrals",
            "primary_currency": {
                "currency": "qualified referrals",
                "version": 1,
                "audience": "owner-operators of small service firms",
                "current_measure": "4 per month",
                "desired_measure": "12 per month",
                "mechanism": "referral partner network",
            },
            "diagnostic_model": {
                "model_id": "model-3f",
                "version": 1,
                "name": "Growth Pyramid",
                "levels": [
                    {
                        "level_id": "level-stuck",
                        "name": "Stuck",
                        "observable_measures": ["under 4 per month"],
                        "symptoms": ["quiet months"],
                        "behaviors": ["waits for referrals"],
                        "problems": ["cannot forecast revenue"],
                    },
                    {
                        "level_id": "level-scaling",
                        "name": "Scaling",
                        "observable_measures": ["12 or more per month"],
                        "symptoms": ["pipeline visible"],
                        "behaviors": ["runs the network"],
                        "problems": ["lead flow stalls"],
                    },
                ],
                "progression": "climb by installing the referral network",
                "qualification_logic": "rank by monthly referral count",
                "visual": "asset://diagnostic/3f-growth-pyramid.png",
                "explanatory_copy": "two levels placed by referral count",
            },
            "approved_by": APPROVER,
            "intended_use": "3f pilot campaign",
            "approved_on": "2026-10-02",
            "claims": ["claim-1"],
        }

    def _offer(self):
        return {
            "offer_id": "offer-3f",
            "audience": "owner-operators of small service firms",
            "promise": "twice the qualified referrals",
            "eligibility": "service businesses with a proven offer",
            "price_hypothesis": "USD 7,500",
            "owner": "offer-owner",
            "delivery": self._delivery(),
        }

    def _message(self, **overrides):
        body = {
            "message_id": "message-3f",
            "owner": "message-owner",
            "avatar": "owner-operators of small service firms",
            "currency": "qualified referrals",
            "problem": "cannot forecast revenue",
            "promise": "twice the qualified referrals",
            "cta": "Book a diagnostic call",
            "product_offer_id": "offer-3f",
            "problem_hierarchy": [
                "no predictable referral flow",
                "referrals depend on luck",
            ],
            "desired_outcome": "a predictable referral engine",
            "proof_objections": [
                "proof: referral partner network",
                "objection: no time to build it",
            ],
            "story": "an owner-operator story",
            "method_explanation": "install the referral network in nine steps",
            "lead_magnet": "referral readiness checklist",
            "hook": "why referrals stall at four a month",
            "angles": ["referral drought", "referral engine"],
            "landing_message": "turn referrals into a system",
            "authority_amplifier_outline": (
                "Promise, Proof, Problems, Steps, Context, Action"
            ),
        }
        body.update(overrides)
        return body

    def payload(self, **overrides):
        body = {
            "workspace_id": "ws-3f",
            "authorities": self._authorities(),
            "campaign_message_package_id": "message-package-3f",
            "message_version": 1,
            "message": self._message(),
            "offer": self._offer(),
            "method": self._method(),
            "stage_owner": OWNER,
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE,
            "checkpoint_evidence": "all twelve stage 6 assets reviewed",
            "rationale": "the message agrees with the offer and method",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        body.update(overrides)
        return body

    def url(self, tenant_id: str = TENANT) -> str:
        return f"/red/clients/{tenant_id}/stages/6/gate"

    def seed_stage_five(self, tenant_id: str = TENANT) -> None:
        for number, payload in (
            (0, self.stage_zero_payload()),
            (1, self.stage_one_payload()),
            (2, self.stage_two_payload()),
            (3, self.stage_three_payload()),
            (4, self.stage_four_payload()),
            (5, self.stage_five_payload()),
        ):
            response = self.client.post(
                f"/red/clients/{tenant_id}/stages/{number}/gate", json=payload
            )
            self.assertEqual(response.status_code, 201, response.text)

    def test_a_passing_gate_is_recorded_and_pins_exact_versions(self) -> None:
        self.seed_stage_five()

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)
        decision = response.json()
        self.assertEqual(decision["stage_number"], 6)
        self.assertEqual(decision["checkpoint"], "Campaign Message Approved")
        self.assertEqual(decision["disposition"], "approved")
        self.assertEqual(decision["reviewer"], APPROVER)
        self.assertEqual(decision["tenant_id"], TENANT)
        self.assertEqual(
            {asset["asset_id"] for asset in decision["required_assets"]},
            {kind for kind in self.message_kinds},
        )
        self.assertTrue(
            all(asset["version"] == 1 for asset in decision["required_assets"])
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        decision_six = reloaded.decision_for(6)
        self.assertIsNotNone(decision_six)
        self.assertEqual(
            {asset.asset_id for asset in decision_six.required_assets},
            set(self.message_kinds),
        )

    def test_the_stage_run_is_persisted_with_its_completion(self) -> None:
        self.seed_stage_five()

        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 201, response.text)

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )
        from redops.contexts.governance.domain.value_objects import StageStatus

        run = self.run_repository.load(
            stage_zero_to_ten_template().version, "ws-3f", 6, TENANT
        )
        self.assertIsNotNone(run)
        self.assertEqual(StageStatus.COMPLETE, run.status)
        self.assertEqual(OWNER, run.assigned_owner)
        self.assertEqual(TENANT, run.tenant_id)

    def test_a_stage_six_gate_without_a_passing_stage_five_is_rejected(
        self,
    ) -> None:
        response = self.client.post(self.url(), json=self.payload())

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "GateDecisionError"
        )

    def test_a_message_conflicting_with_its_offer_is_rejected(self) -> None:
        self.seed_stage_five()

        response = self.client.post(
            self.url(),
            json=self.payload(message=self._message(promise="a different promise")),
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"],
            "CampaignMessageAlignmentError",
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        reloaded = self.repository.load(stage_zero_to_ten_template(), TENANT)
        self.assertIsNone(reloaded.decision_for(6))

    def test_an_unauthorized_approver_is_rejected_without_a_write(self) -> None:
        self.seed_stage_five()

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
        self.assertIsNone(reloaded.decision_for(6))

    def test_a_stage_six_decision_is_not_visible_to_another_client(self) -> None:
        self.seed_stage_five()
        self.assertEqual(
            self.client.post(self.url(), json=self.payload()).status_code, 201
        )

        from redops.contexts.governance.domain.templates import (
            stage_zero_to_ten_template,
        )

        other = self.repository.load(
            stage_zero_to_ten_template(), OTHER_TENANT
        )
        self.assertIsNone(other.decision_for(6))

    def test_re_stating_the_approved_method_with_different_content_is_refused(
        self,
    ) -> None:
        self.seed_stage_five()
        self.assertEqual(
            self.client.post(self.url(), json=self.payload()).status_code, 201
        )

        tampered = self._method()
        tampered["currency"] = "monthly revenue"
        tampered["primary_currency"]["currency"] = "monthly revenue"

        response = self.client.post(
            self.url(), json=self.payload(method=tampered)
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "MethodVersionConflictError"
        )

    def test_re_stating_the_approved_offer_with_different_content_is_refused(
        self,
    ) -> None:
        self.seed_stage_five()
        self.assertEqual(
            self.client.post(self.url(), json=self.payload()).status_code, 201
        )

        tampered = self._offer()
        tampered["promise"] = "a different promise"

        response = self.client.post(
            self.url(), json=self.payload(offer=tampered)
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"], "OfferVersionConflictError"
        )

    def test_re_stating_the_approved_message_with_different_content_is_refused(
        self,
    ) -> None:
        self.seed_stage_five()
        self.assertEqual(
            self.client.post(self.url(), json=self.payload()).status_code, 201
        )

        response = self.client.post(
            self.url(),
            json=self.payload(
                message=self._message(story="a different owner story")
            ),
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["error"],
            "CampaignMessageVersionConflictError",
        )


if __name__ == "__main__":
    unittest.main()
