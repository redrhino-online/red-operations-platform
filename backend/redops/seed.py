"""Seed the 3F pilot workspace end to end through the real domain use cases.

Item K1 (IMPLEMENTATION_PLAN.md) seeds the ``3fmindset`` pilot workspace so the
single-shell cockpit renders real data instead of empty states. SPEC.md section 1
makes the 3F pilot the first client, section 4 makes the stage 0-10 pipeline the
product, section 6 requires the API to call use cases through ports and never
mutate persistence directly, and section 7 makes the stage gate an explicit REST
resource. The live check ``[14.6]`` in ``scripts/check_cockpit_overhaul.sh``
(lines 97-100) requires ``GET /red/clients?tenant_id=3fmindset`` to answer with
the pilot workspace, so this module drives the same routes the e2e suite proves.

Fixture derivation: the API image ships only ``backend/`` (no ``tests/``), so this
module is self-contained production code with no ``tests.*`` import. The demo
payload shapes mirror the e2e fixture payloads in
``tests/unit/test_stage_six_gate_route.py``, ``test_stage_seven_gate_route.py``,
``test_stage_eight_gate_route.py``, ``test_stage_nine_gate_route.py`` and
``test_stage_ten_gate_route.py`` (which chain back through the earlier stage route
tests) so the seeded workspace matches the pipeline the e2e proves. The asset
lists are generated from the canonical kind constants exactly as the fixtures do,
so template growth is tracked rather than hard-coded.

Demo-marking convention: every seeded identifier except the tenant and workspace
id carries a ``demo-`` prefix, every actor/owner/approver value carries a
``demo-`` prefix, and every free-text prose value carries the ``Demo `` or
``demo: `` marker. Canonical enum and keyword values (provenance ``known``,
outcomes ``passed``/``routed``/``observed``/``pending``, step and check kinds,
modality, audience state, model, pricing basis, cadence, strategy, platform,
payment method, awareness levels, interest kind, gender, channels, swimlane
channel and stalled/next step keys, and the ``faq`` source) are never marked.
The one recorded exception is the tenant id ``3fmindset`` and the workspace id
``ws-3f``: those are the pilot's real identifiers, fixed by the owner's 3F pilot
decision and the cockpit gate, so they stay unmarked.
"""

from __future__ import annotations

import json
import os
from typing import Any, Mapping

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
from redops.contexts.execution.domain.value_objects import (
    CANONICAL_BASELINE_KINDS,
    CANONICAL_FUNNEL_KINDS,
    CANONICAL_LAUNCH_KINDS,
)
from redops.contexts.production.domain.value_objects import (
    CANONICAL_AMPLIFIER_KINDS,
)

DEMO_TENANT = "3fmindset"
DEMO_WORKSPACE_ID = "ws-3f"
DEMO_OWNER = "demo-red-principal"
DEMO_APPROVER = "demo-client-approver"
DEMO_AUTHORITY = "demo-client-authority"

DEMO_STEP_NAMES: tuple[str, ...] = (
    "Demo: extract the diagnosis",
    "Demo: draft the map",
    "Demo: name the phases",
    "Demo: write the steps",
    "Demo: bind the inputs",
    "Demo: define the actions",
    "Demo: pin the outputs",
    "Demo: write the narrative",
    "Demo: draw the visual",
)


class SeedError(RuntimeError):
    """A seed step failed; carries the route status and response detail."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        detail: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class SeedConfigurationError(SeedError):
    """The seed cannot run without a durable database configuration."""


def _kind_value(kind: Any) -> str:
    """Return the string value of a canonical kind (enum or plain string)."""

    return kind.value if hasattr(kind, "value") else kind


def _demo_asset_ids(*kind_groups: Any) -> list[str]:
    """Generate the demo asset ids for the given canonical kind groups."""

    return [
        f"demo-{_kind_value(kind)}-3f@1"
        for kinds in kind_groups
        for kind in kinds
    ]


def _solution() -> dict[str, Any]:
    steps = [
        {
            "step_id": f"demo-step-{index}",
            "name": name,
            "starting_state": f"Demo: state-{index}",
            "final_state": f"Demo: state-{index + 1}",
            "inputs": [f"Demo: input-{index}"],
            "actions": [f"Demo: action-{index}"],
            "outputs": [f"Demo: output-{index}"],
        }
        for index, name in enumerate(DEMO_STEP_NAMES)
    ]
    phases = [
        {
            "phase_id": "demo-phase-extract",
            "name": "Demo: extract",
            "steps": steps[0:3],
        },
        {
            "phase_id": "demo-phase-content",
            "name": "Demo: content",
            "steps": steps[3:6],
        },
        {
            "phase_id": "demo-phase-expand",
            "name": "Demo: expand",
            "steps": steps[6:9],
        },
    ]
    return {
        "solution_id": "demo-signature-3f",
        "version": 1,
        "transformation_map": "Demo: from referral chaos to predictable demand",
        "process_inventory": [
            "Demo: discovery",
            "Demo: build",
            "Demo: launch",
        ],
        "phases": phases,
        "starting_state": "Demo: state-0",
        "final_state": "Demo: state-9",
        "narrative": "Demo: nine named stages move the client across three phases",
        "visual": "Demo: a three lane map with nine labelled stages",
    }


def _delivery() -> dict[str, Any]:
    return {
        "delivery_id": "demo-delivery-3f",
        "version": 1,
        "signature_solution": _solution(),
        "delivery_model": "Demo: group coaching program",
        "duration": "Demo: eight weeks",
        "modules": ["Demo: one module per named stage"],
        "responsibilities": [
            "Demo: RED builds the machine",
            "Demo: client serves",
        ],
        "support_cadence": "Demo: weekly training and weekly coaching",
        "step_deliveries": [
            {
                "step_id": f"demo-step-{index}",
                "action": f"Demo: deliver action {index}",
                "actor": "Demo: RED delivery lead",
                "deliverable": f"Demo: deliverable {index}",
                "timing": f"Demo: week {index + 1}",
                "measure": f"Demo: measure {index}",
            }
            for index in range(9)
        ],
        "outcome_measures": ["Demo: qualified conversations per month"],
        "pricing_payments": "Demo: outcome based fee in three payments",
        "scope": "Demo: the full nine step transformation",
        "guarantee_decision": "Demo: no guarantee until results are measured",
        "eligibility": "Demo: owner-operator with a delivery team",
        "offer_stack": ["Demo: diagnostic offer", "Demo: core program"],
    }


def _program() -> dict[str, Any]:
    return {
        "program_id": "demo-program-3f",
        "version": 1,
        "owner": "demo-red-offer-owner",
        "model": "group_consulting",
        "pricing_basis": "outcome_value",
        "duration_weeks": 9,
        "cadence": "monday_training_thursday_coaching",
        "modules": [
            {
                "module_id": f"demo-module-{index + 1}",
                "signature_step": name,
                "position": index + 1,
                "outcome": f"Demo: the client reaches {name}",
                "deliverable": f"Demo: the {name} worksheet",
            }
            for index, name in enumerate(DEMO_STEP_NAMES)
        ],
    }


def _method() -> dict[str, Any]:
    return {
        "method_id": "demo-method-3f",
        "parent_method": "Demo: signature-solution",
        "semantic_version": {"major": 1, "minor": 0, "patch": 0},
        "stages": ["Demo: diagnose", "Demo: position", "Demo: model"],
        "currency": "Demo: qualified referrals",
        "primary_currency": {
            "currency": "Demo: qualified referrals",
            "version": 1,
            "audience": "Demo: owner-operators of small service firms",
            "current_measure": "Demo: 4 per month",
            "desired_measure": "Demo: 12 per month",
            "mechanism": "Demo: referral partner network",
        },
        "diagnostic_model": {
            "model_id": "demo-model-3f",
            "version": 1,
            "name": "Demo: growth pyramid",
            "levels": [
                {
                    "level_id": "demo-level-stuck",
                    "name": "Demo: stuck",
                    "observable_measures": ["Demo: under 4 per month"],
                    "symptoms": ["Demo: quiet months"],
                    "behaviors": ["Demo: waits for referrals"],
                    "problems": ["Demo: cannot forecast revenue"],
                },
                {
                    "level_id": "demo-level-scaling",
                    "name": "Demo: scaling",
                    "observable_measures": ["Demo: 12 or more per month"],
                    "symptoms": ["Demo: pipeline visible"],
                    "behaviors": ["Demo: runs the network"],
                    "problems": ["Demo: lead flow stalls"],
                },
            ],
            "progression": "Demo: climb by installing the referral network",
            "qualification_logic": "Demo: rank by monthly referral count",
            "visual": "Demo: asset://diagnostic/3f-growth-pyramid.png",
            "explanatory_copy": "Demo: two levels placed by referral count",
        },
        "approved_by": DEMO_APPROVER,
        "intended_use": "Demo: 3f pilot campaign",
        "approved_on": "2026-10-02",
        "claims": ["demo-claim-1"],
    }


def _offer() -> dict[str, Any]:
    return {
        "offer_id": "demo-offer-3f",
        "audience": "Demo: owner-operators of small service firms",
        "promise": "Demo: twice the qualified referrals",
        "eligibility": "Demo: service businesses with a proven offer",
        "price_hypothesis": "Demo: USD 7,500",
        "owner": "demo-offer-owner",
        "delivery": _delivery(),
    }


def _message() -> dict[str, Any]:
    return {
        "message_id": "demo-message-3f",
        "owner": "demo-message-owner",
        "avatar": "Demo: owner-operators of small service firms",
        "currency": "Demo: qualified referrals",
        "problem": "Demo: cannot forecast revenue",
        "promise": "Demo: twice the qualified referrals",
        "cta": "Demo: book a diagnostic call",
        "product_offer_id": "demo-offer-3f",
        "problem_hierarchy": [
            "Demo: no predictable referral flow",
            "Demo: referrals depend on luck",
        ],
        "desired_outcome": "Demo: a predictable referral engine",
        "proof_objections": [
            "Demo: proof: referral partner network",
            "Demo: objection: no time to build it",
        ],
        "story": "Demo: an owner-operator story",
        "method_explanation": "Demo: install the referral network in nine steps",
        "lead_magnet": "Demo: referral readiness checklist",
        "hook": "Demo: why referrals stall at four a month",
        "angles": ["Demo: referral drought", "Demo: referral engine"],
        "landing_message": "Demo: turn referrals into a system",
        "authority_amplifier_outline": (
            "Demo: promise, proof, problems, steps, context, action"
        ),
    }


def _roadmap() -> dict[str, Any]:
    return {
        "roadmap_id": "demo-roadmap-3f",
        "version": 1,
        "owner": "demo-content-owner",
        "topics": [
            {
                "topic_id": f"demo-topic-{index + 1}",
                "name": f"Demo: {name} audience questions",
                "signature_step": name,
                "question": f"Demo: what does {name} change for the client?",
                "channels": ["blog", "youtube", "facebook"],
            }
            for index, name in enumerate(DEMO_STEP_NAMES)
        ],
    }


def _crusher() -> dict[str, Any]:
    return {
        "crusher_id": "demo-crusher-3f",
        "version": 1,
        "owner": "demo-content-owner",
        "topic_id": "demo-topic-1",
        "title": "Demo: why the first step matters now",
        "promise_measure": "Demo: a measurable result",
        "promise_timeline": "Demo: within 90 days",
        "frustrations": ["Demo: the current approach stalls"],
        "goal": "Demo: reach the next level with confidence",
        "model": "Demo: the transformation model",
        "metaphor": "Demo: a map for the journey",
        "context": "Demo: part of the signature program",
        "steps": [DEMO_STEP_NAMES[0]],
        "story": "Demo: a client who made the shift",
        "choice": "Demo: keep guessing or follow the method",
        "action": "Demo: book the next step",
    }


def _content_plan() -> dict[str, Any]:
    return {
        "plan_id": "demo-plan-3f",
        "version": 1,
        "owner": "demo-content-owner",
        "primary_currency": {
            "currency": "Demo: qualified referrals",
            "version": 1,
            "audience": "Demo: owner-operators of small service firms",
            "current_measure": "Demo: 4 per month",
            "desired_measure": "Demo: 12 per month",
            "mechanism": "Demo: referral partner network",
        },
        "themes": [
            {
                "theme_id": "demo-theme-1",
                "name": "Demo: the current measure",
                "currency_measure": "Demo: 4 per month",
            }
        ],
        "ideas": [
            {
                "idea_id": "demo-idea-1",
                "signature_step": DEMO_STEP_NAMES[0],
                "source": "faq",
                "prompt": "Demo: what does the first step change for the client?",
                "theme_id": "demo-theme-1",
                "channels": ["email", "social"],
            }
        ],
    }


def _amplifier() -> dict[str, Any]:
    return {
        "amplifier_id": "demo-amplifier-3f",
        "owner": "demo-production-manager",
        "script": [
            {"kind": kind, "content": f"Demo: {kind} content"}
            for kind in (
                "promise",
                "proof",
                "problems",
                "steps",
                "context",
                "action",
            )
        ],
        "proof_claim_ids": ["demo-claim-1"],
        "visuals": {
            "storyboard": "asset://demo/aa/storyboard",
            "brand_treatment": "asset://demo/aa/brand",
            "presentation": "asset://demo/aa/slides",
            "speaker_notes": "asset://demo/aa/notes",
            "recording": "asset://demo/aa/recording",
            "edited_video": "asset://demo/aa/edited",
            "hosted_video": "asset://demo/aa/hosted",
            "player_assets": "asset://demo/aa/player",
        },
        "script_approval": {
            "approved_by": "demo-production-manager",
            "intended_use": "Demo: 3f pilot campaign",
            "approved_on": "2026-10-02",
        },
        "creative_approval": {
            "approved_by": DEMO_AUTHORITY,
            "intended_use": "Demo: 3f pilot campaign",
            "approved_on": "2026-10-03",
        },
    }


def _claims() -> list[dict[str, Any]]:
    return [
        {
            "claim_id": "demo-claim-1",
            "statement": "Demo: method fact recorded with the client",
            "provenance": "known",
            "confidence_note": "demo: directly observed",
            "citations": [
                {
                    "source_id": "demo-source-method",
                    "checksum": "sha256:demo-method",
                    "location": "p.1",
                }
            ],
        }
    ]


def _funnel() -> dict[str, Any]:
    return {
        "integration_id": "demo-funnel-3f",
        "owner": "demo-integration-manager",
        "assets": {
            "campaign_architecture": "asset://demo/funnel/architecture",
            "pages": "asset://demo/funnel/pages",
            "forms": "asset://demo/funnel/forms",
            "qualification": "asset://demo/funnel/qualification",
            "booking": "asset://demo/funnel/booking",
            "sequences": "asset://demo/funnel/sequences",
            "crm": "asset://demo/funnel/crm",
            "tags": "asset://demo/funnel/tags",
            "automation": "asset://demo/funnel/automation",
            "analytics": "asset://demo/funnel/analytics",
            "tracking": "asset://demo/funnel/tracking",
            "sales_handoff": "asset://demo/funnel/sales-handoff",
            "sops": "asset://demo/funnel/sops",
        },
        "dry_run": {
            "dry_run_id": "demo-dryrun-3f",
            "handoffs": [
                {
                    "kind": "capture",
                    "outcome": "routed",
                    "record_id": "demo-record-capture",
                    "owner": "demo-sdr",
                },
                {
                    "kind": "engagement",
                    "outcome": "routed",
                    "record_id": "demo-record-engagement",
                    "owner": "demo-setter",
                },
                {
                    "kind": "conversion",
                    "outcome": "routed",
                    "record_id": "demo-record-conversion",
                    "owner": "demo-closer",
                },
            ],
        },
    }


def _swimlanes() -> dict[str, Any]:
    channels = (
        ("messages", "traffic", "opt_in"),
        ("ads", "opt_in", "watch_amplifier"),
        ("human_outreach", "watch_amplifier", "book_call"),
        ("offline_direct_mail", "book_call", "show"),
        ("content", "show", "enroll"),
    )
    return {
        "plan_id": "demo-swimlanes-3f",
        "owner": "demo-recovery-owner",
        "moves": [
            {
                "move_id": f"demo-move-{channel}",
                "channel": channel,
                "stalled_step": stalled,
                "next_step": next_step,
                "vehicle": "email",
                "next_action": "Demo: drive the prospect to the next step",
            }
            for channel, stalled, next_step in channels
        ],
    }


def _qa() -> dict[str, Any]:
    from redops.contexts.execution.domain.value_objects import (
        ComplianceAssetKind,
        QACheckKind,
    )

    return {
        "qa_id": "demo-qa-3f",
        "owner": "demo-qa-owner",
        "designated_authority": DEMO_AUTHORITY,
        "checks": [
            {
                "kind": kind.value,
                "outcome": "passed",
                "evidence": f"Demo: evidence://{kind.value}",
            }
            for kind in QACheckKind
        ],
        "compliance": {
            "package_id": "demo-compliance-3f",
            "target_markets": ["us"],
            "assets": [
                {
                    "kind": kind.value,
                    "reference": f"asset://demo/compliance/{kind.value}",
                    "version": 1,
                }
                for kind in ComplianceAssetKind
            ],
        },
        "authorization": {
            "authorized_by": DEMO_AUTHORITY,
            "intended_use": "Demo: 3f pilot launch",
            "authorized_on": "2026-10-03",
        },
    }


def _enrollment() -> dict[str, Any]:
    return {
        "plan_id": "demo-enrollment-3f",
        "owner": "demo-journey-owner",
        "closer": "demo-sales-closer",
        "homework": {
            "signature_step": DEMO_STEP_NAMES[0],
            "questions": [
                "Demo: what are your current sales?",
                "Demo: what is holding you back?",
            ],
            "max_days_to_call": 3,
        },
        "steps": [
            {
                "step_kind": kind,
                "purpose": f"Demo: run the {kind} stage",
                "opt_out_check": "Demo: confirm the prospect wants this now",
            }
            for kind in ("frame", "examine", "prescribe", "prognosis")
        ],
        "qualification": {
            "accept_criteria": ["Demo: established business at 10k per month"],
            "reject_criteria": ["Demo: still has a day job with no revenue"],
        },
        "payment": {
            "method": "card",
            "deposit_amount": 2000,
            "collected_live": True,
        },
    }


def _client_process() -> dict[str, Any]:
    return {
        "process_id": "demo-process-3f",
        "owner": "demo-red-process-owner",
        "approver": DEMO_AUTHORITY,
        "strategy": "paid-strategy-session",
        "homework": {
            "signature_step": DEMO_STEP_NAMES[0],
            "questions": [
                "Demo: what is your current measure?",
                "Demo: what is stopping you?",
            ],
            "booking_window_days": 3,
        },
        "steps": [
            {
                "step_kind": kind,
                "purpose": f"Demo: run the {kind} part",
                "prompt": f"Demo: the client's own wording for {kind}",
            }
            for kind in (
                "frame",
                "discover-problems",
                "prescription",
                "application",
                "invitation",
                "objection-crusher",
            )
        ],
        "checkpoints": [
            {
                "kind": kind,
                "question": f"Demo: the client's question for {kind}",
                "on_fail_action": "Demo: step back and reset before continuing",
            }
            for kind in (
                "intent",
                "commitment",
                "value",
                "confidence",
                "desire",
            )
        ],
        "acceptance_criteria": [
            "Demo: existing business with a delivered offer"
        ],
        "rejection_criteria": ["Demo: no product and no revenue"],
        "objections": [
            {
                "concern": "Demo: how much does it cost?",
                "answer": "Demo: the client asks how many clients make it pay",
            }
        ],
        "terms": {
            "price_floor": 3000,
            "no_show_rules": ["Demo: confirm within the booking window"],
        },
    }


def _baseline() -> dict[str, Any]:
    return {
        "baseline_id": "demo-baseline-3f",
        "owner": "demo-baseline-owner",
        "assets": {
            "live_campaign": "asset://demo/campaign/3f",
            "spend_records": "asset://demo/spend/3f",
            "lead_records": "asset://demo/leads/3f",
            "conversion_measures": "asset://demo/conversion/3f",
            "engagement_measures": "asset://demo/engagement/3f",
            "applications": "asset://demo/applications/3f",
            "bookings": "asset://demo/bookings/3f",
            "shows": "asset://demo/shows/3f",
            "closes": "asset://demo/closes/3f",
            "acquisition_cost": "asset://demo/acquisition-cost/3f",
            "attribution": "asset://demo/attribution/3f",
            "issue_log": "asset://demo/issue-log/3f",
        },
        "milestones": [
            {
                "kind": "first_qualified_traffic",
                "status": "observed",
                "observed_on": "2026-10-03",
                "source": "Demo: analytics://traffic/3f",
            },
            {"kind": "lead", "status": "pending"},
            {"kind": "appointment", "status": "pending"},
            {"kind": "sale", "status": "pending"},
        ],
    }


def _nurture() -> dict[str, Any]:
    return {
        "plan_id": "demo-nurture-3f",
        "owner": "demo-campaign-operator",
        "sequences": [
            {
                "sequence_id": "demo-sequence-opted",
                "audience_state": "opted_in_not_booked",
                "messages": [
                    {
                        "message_id": "demo-nurture-1",
                        "name": "Demo: what stalls your referrals",
                        "audience_state": "opted_in_not_booked",
                        "modality": "problem",
                        "signature_step": DEMO_STEP_NAMES[0],
                        "subject": (
                            "Demo: the referral question you keep avoiding"
                        ),
                        "purpose": (
                            "Demo: name the problem so the lead recognizes it"
                        ),
                    },
                    {
                        "message_id": "demo-nurture-2",
                        "name": "Demo: book a referral diagnostic",
                        "audience_state": "opted_in_not_booked",
                        "modality": "promotion",
                        "signature_step": DEMO_STEP_NAMES[0],
                        "subject": "Demo: your referral diagnostic is open",
                        "purpose": "Demo: promote the next step",
                    },
                ],
            }
        ],
    }


def stage_zero_payload() -> dict[str, Any]:
    return {
        "workspace_id": DEMO_WORKSPACE_ID,
        "intake_package_id": "demo-intake-3f",
        "assets": [
            {
                "asset_id": f"demo-{kind.value}-3f@1",
                "kind": kind.value,
                "version": 1,
                "owner": DEMO_OWNER,
                "summary": f"Demo: recorded {kind.value}",
                "evidence_claim_ids": ["demo-claim-intake-1"],
            }
            for kind in CANONICAL_INTAKE_KINDS
        ],
        "claims": [
            {
                "claim_id": "demo-claim-intake-1",
                "statement": "Demo: intake fact recorded with the client",
                "provenance": "known",
                "confidence_note": "demo: captured during intake",
                "citations": [
                    {
                        "source_id": "demo-source-intake",
                        "checksum": "sha256:demo-intake",
                        "location": "p.1",
                    }
                ],
            }
        ],
        "stage_owner": DEMO_OWNER,
        "approver": DEMO_APPROVER,
        "proposed_by": DEMO_OWNER,
        "scope": "stage-1-diagnosis",
        "checkpoint_evidence": "Demo: all stage 0 assets reviewed",
        "rationale": "Demo: intake complete and owned",
        "assigned_owner": DEMO_OWNER,
        "due_on": "2026-10-02",
        "on": "2026-10-02",
        "correlation_id": "demo-corr-stage-0",
    }


def stage_one_payload() -> dict[str, Any]:
    return {
        "workspace_id": DEMO_WORKSPACE_ID,
        "diagnosis_package_id": "demo-diagnosis-3f",
        "avatar": {
            "avatar_id": "demo-avatar-3f",
            "version": 1,
            "name": "Demo: owner-operator of a small service firm",
            "demographics": "Demo: 35-50, runs a small local service firm",
            "psychographics": "Demo: proud of craft, skeptical of marketing",
            "pains": ["Demo: feast and famine pipeline"],
            "goals": ["Demo: predictable qualified demand"],
            "consequences_of_inaction": [
                "Demo: hires then lays off as work dries up"
            ],
            "awareness": "problem aware, not solution aware",
            "customer_evidence_claim_ids": ["demo-claim-voice-1"],
            "voice_notes": [
                "Demo: I cannot plan payroll when the phone is quiet"
            ],
        },
        "business_snapshot": {
            "snapshot_id": "demo-snapshot-3f",
            "version": 1,
            "business_model": "Demo: project based service work billed hourly",
            "current_offers": ["Demo: hourly support retainer"],
            "lead_sources": ["Demo: referrals"],
            "constraints": ["Demo: two delivery people, no marketing owner"],
            "narrative": "Demo: steady referrals but no predictable pipeline",
            "evidence_claim_ids": ["demo-claim-offer-1"],
        },
        "offer_funnel_audit": {
            "audit_id": "demo-audit-3f",
            "version": 1,
            "offer_findings": ["Demo: the retainer has no stated outcome"],
            "funnel_steps": [
                "Demo: referral",
                "Demo: call",
                "Demo: quote",
                "Demo: project",
            ],
            "conversion_evidence": [
                "Demo: quotes are tracked in a spreadsheet"
            ],
            "gaps": ["Demo: no qualification step before the call"],
            "narrative": (
                "Demo: the funnel has no owner between referral and quote"
            ),
            "evidence_claim_ids": ["demo-claim-offer-2"],
        },
        "awareness_map": {
            "map_id": "demo-awareness-3f",
            "version": 1,
            "primary_level": "problem_aware",
            "research_evidence": [
                "Demo: reviews name the unpredictable pipeline"
            ],
            "message_requirements": [
                "Demo: lead with the predictable pipeline outcome"
            ],
            "retarget_level": "solution_aware",
        },
        "audience_reach_estimate": {
            "estimate_id": "demo-reach-3f",
            "version": 1,
            "owner": DEMO_OWNER,
            "platform": "facebook_audience_insights",
            "audience": {
                "location": "Demo: United States",
                "age": "Demo: 35-50",
                "gender": "all",
                "interests": [
                    {"kind": "expert", "value": "Demo: small service firm coach"}
                ],
            },
            "estimated_reach": 180000,
            "source_note": "Demo: Facebook Audience Insights sizing",
            "captured_on": "2026-10-03",
        },
        "target_market_match": {
            "matchmaker_id": "demo-match-3f",
            "version": 1,
            "candidates": [
                {
                    "market_id": "demo-market-referrals",
                    "name": "Demo: referral-starved service business owners",
                    "passion": "Demo: we have run this play inside the trade",
                    "problem": "Demo: unpredictable referral flow",
                    "profit": "Demo: they already spend on lead generation",
                    "reachability": (
                        "Demo: active in two owner-operator communities"
                    ),
                    "pathway": (
                        "Demo: from a referral drought to a referral partner "
                        "engine"
                    ),
                },
                {
                    "market_id": "demo-market-coaches",
                    "name": "Demo: new executive coaches",
                    "passion": "Demo: we coach this transition",
                    "problem": "Demo: no repeatable client acquisition",
                    "profit": "Demo: they invest in their practice",
                    "reachability": "Demo: active in coach communities",
                    "pathway": (
                        "Demo: from no pipeline to a repeatable acquisition "
                        "engine"
                    ),
                },
            ],
            "selected_market_id": "demo-market-referrals",
        },
        "claims": [
            {
                "claim_id": claim_id,
                "statement": (
                    "Demo: stage 1 diagnosis fact recorded with the client"
                ),
                "provenance": "known",
                "confidence_note": "demo: captured during diagnosis",
                "citations": [
                    {
                        "source_id": "demo-source-diagnosis",
                        "checksum": "sha256:demo-diagnosis",
                        "location": "p.2",
                    }
                ],
            }
            for claim_id in (
                "demo-claim-voice-1",
                "demo-claim-offer-1",
                "demo-claim-offer-2",
            )
        ],
        "stage_owner": DEMO_OWNER,
        "approver": DEMO_APPROVER,
        "proposed_by": DEMO_OWNER,
        "scope": "stage-2-position",
        "checkpoint_evidence": "Demo: all nine stage 1 assets reviewed",
        "rationale": "Demo: avatar locked and owned",
        "assigned_owner": DEMO_OWNER,
        "due_on": "2026-10-02",
        "on": "2026-10-02",
        "correlation_id": "demo-corr-stage-1",
    }


def stage_two_payload() -> dict[str, Any]:
    return {
        "workspace_id": DEMO_WORKSPACE_ID,
        "currency_package_id": "demo-currency-3f",
        "inventory": {
            "inventory_id": "demo-inventory-3f",
            "version": 1,
            "category": "Demo: marketing operations for service firms",
            "currencies_to_increase": [
                "Demo: qualified leads",
                "Demo: margin",
            ],
            "currencies_to_decrease": [
                "Demo: cost per lead",
                "Demo: owner hours",
            ],
        },
        "positioning": {
            "decision_id": "demo-positioning-3f",
            "version": 1,
            "core_problem": (
                "Demo: referrals are unpredictable and unmeasurable"
            ),
            "transformation_statement": (
                "Demo: a predictable qualified demand pipeline the owner "
                "controls"
            ),
            "horizon": "Demo: 90 days",
            "qualifications": ["Demo: has a delivery team already"],
            "disqualifications": ["Demo: wants done-for-you sales calls"],
        },
        "primary_currency": {
            "currency": "Demo: qualified sales conversations",
            "version": 1,
            "audience": "Demo: owner-operators of small local service firms",
            "current_measure": "Demo: 3 per month from referrals",
            "desired_measure": "Demo: 12 per month on a repeatable path",
            "mechanism": "Demo: a positioned diagnostic offer with one CTA",
        },
        "million_dollar_message": {
            "message_id": "demo-mdm-3f",
            "version": 1,
            "avatar": "Demo: owner-operator of a small local service firm",
            "currency": "Demo: qualified sales conversations",
            "metric": "Demo: 3 to 12 per month",
            "timeline": "Demo: 90 days",
            "pain": "Demo: feast and famine pipeline",
            "message": (
                "Demo: owner-operators of small local service firms get from "
                "3 to 12 qualified sales conversations a month in 90 days "
                "without feast-and-famine referrals"
            ),
        },
        "stage_owner": DEMO_OWNER,
        "approver": DEMO_APPROVER,
        "proposed_by": DEMO_OWNER,
        "scope": "stage-3-model",
        "checkpoint_evidence": "Demo: all ten stage 2 assets reviewed",
        "rationale": "Demo: one primary currency locked and owned",
        "assigned_owner": DEMO_OWNER,
        "due_on": "2026-10-02",
        "on": "2026-10-02",
        "correlation_id": "demo-corr-stage-2",
    }


def stage_three_payload() -> dict[str, Any]:
    return {
        "workspace_id": DEMO_WORKSPACE_ID,
        "diagnostic_package_id": "demo-diagnostic-model-3f",
        "model": {
            "model_id": "demo-diagnostic-model-3f",
            "version": 1,
            "name": "Demo: the predictable pipeline pyramid",
            "levels": [
                {
                    "level_id": "demo-level-reference",
                    "name": "Demo: referral dependent",
                    "observable_measures": [
                        "Demo: 3 conversations per month"
                    ],
                    "symptoms": ["Demo: quiet weeks between projects"],
                    "behaviors": ["Demo: asks for referrals after delivery"],
                    "problems": ["Demo: cannot forecast revenue"],
                },
                {
                    "level_id": "demo-level-emerging",
                    "name": "Demo: emerging pipeline",
                    "observable_measures": [
                        "Demo: 6 conversations per month"
                    ],
                    "symptoms": ["Demo: some months fill, some do not"],
                    "behaviors": ["Demo: runs one offer inconsistently"],
                    "problems": ["Demo: lead flow still spikes and stalls"],
                },
                {
                    "level_id": "demo-level-systematic",
                    "name": "Demo: systematic demand",
                    "observable_measures": [
                        "Demo: 12 conversations per month"
                    ],
                    "symptoms": ["Demo: pipeline is visible weekly"],
                    "behaviors": ["Demo: runs one CTA on a schedule"],
                    "problems": ["Demo: still dependent on the owner"],
                },
                {
                    "level_id": "demo-level-predictable",
                    "name": "Demo: predictable demand",
                    "observable_measures": [
                        "Demo: 12 plus conversations per month"
                    ],
                    "symptoms": ["Demo: pipeline covers two months out"],
                    "behaviors": ["Demo: delegates the daily funnel checks"],
                    "problems": ["Demo: scaling without diluting fit"],
                },
            ],
            "progression": (
                "Demo: each level adds repeatable demand and removes owner "
                "dependence"
            ),
            "qualification_logic": (
                "Demo: place by the observable conversations per month"
            ),
            "visual": "Demo: a four step pyramid with one measure per tier",
            "explanatory_copy": (
                "Demo: each tier states its measure and its next move"
            ),
        },
        "stage_owner": DEMO_OWNER,
        "approver": DEMO_APPROVER,
        "proposed_by": DEMO_OWNER,
        "scope": "stage-4-package-ip",
        "checkpoint_evidence": "Demo: all ten stage 3 assets reviewed",
        "rationale": (
            "Demo: levels are distinguishable by observation and owned"
        ),
        "assigned_owner": DEMO_OWNER,
        "due_on": "2026-10-02",
        "on": "2026-10-02",
        "correlation_id": "demo-corr-stage-3",
    }


def stage_four_payload() -> dict[str, Any]:
    return {
        "workspace_id": DEMO_WORKSPACE_ID,
        "signature_package_id": "demo-signature-3f",
        "solution": _solution(),
        "transformations": {
            "transformations_id": "demo-transformations-3f",
            "version": 1,
            "million_dollar_message": (
                "Demo: from referral chaos to predictable demand in 90 days"
            ),
        },
        "stage_owner": DEMO_OWNER,
        "approver": DEMO_APPROVER,
        "proposed_by": DEMO_OWNER,
        "scope": "stage-5-productize",
        "checkpoint_evidence": "Demo: all twelve stage 4 assets reviewed",
        "rationale": "Demo: the transformation is coherent and owned",
        "assigned_owner": DEMO_OWNER,
        "due_on": "2026-10-02",
        "on": "2026-10-02",
        "correlation_id": "demo-corr-stage-4",
    }


def stage_five_payload() -> dict[str, Any]:
    return {
        "workspace_id": DEMO_WORKSPACE_ID,
        "offer_package_id": "demo-offer-3f",
        "delivery": _delivery(),
        "product_program": _program(),
        "stage_owner": DEMO_OWNER,
        "approver": DEMO_APPROVER,
        "proposed_by": DEMO_OWNER,
        "scope": "stage-7-authority-amplifier",
        "checkpoint_evidence": "Demo: all thirteen stage 5 assets reviewed",
        "rationale": "Demo: every method step is delivered and owned",
        "assigned_owner": DEMO_OWNER,
        "due_on": "2026-10-02",
        "on": "2026-10-02",
        "correlation_id": "demo-corr-stage-5",
    }


def stage_six_payload() -> dict[str, Any]:
    return {
        "workspace_id": DEMO_WORKSPACE_ID,
        "campaign_message_package_id": "demo-message-package-3f",
        "message_version": 1,
        "message": _message(),
        "content_roadmap": _roadmap(),
        "content_crusher": _crusher(),
        "content_plan": _content_plan(),
        "offer": _offer(),
        "method": _method(),
        "stage_owner": DEMO_OWNER,
        "approver": DEMO_APPROVER,
        "proposed_by": DEMO_OWNER,
        "scope": "stage-7-authority-amplifier",
        "checkpoint_evidence": "Demo: all twelve stage 6 assets reviewed",
        "rationale": "Demo: the message agrees with the offer and method",
        "assigned_owner": DEMO_OWNER,
        "due_on": "2026-10-17",
        "on": "2026-10-03",
        "correlation_id": "demo-corr-stage-6",
    }


def stage_seven_payload() -> dict[str, Any]:
    return {
        "workspace_id": DEMO_WORKSPACE_ID,
        "amplifier_package_id": "demo-amplifier-package-3f",
        "amplifier_version": 1,
        "message": _message(),
        "offer": _offer(),
        "method": _method(),
        "amplifier": _amplifier(),
        "claims": _claims(),
        "stage_owner": DEMO_OWNER,
        "approver": DEMO_APPROVER,
        "proposed_by": DEMO_OWNER,
        "scope": "stage-8-funnel-integration",
        "checkpoint_evidence": "Demo: all nine stage 7 kinds reviewed",
        "rationale": (
            "Demo: the amplifier message and supported proof passed review"
        ),
        "assigned_owner": DEMO_OWNER,
        "due_on": "2026-10-17",
        "on": "2026-10-03",
        "correlation_id": "demo-corr-stage-7",
    }


def stage_eight_payload() -> dict[str, Any]:
    return {
        "workspace_id": DEMO_WORKSPACE_ID,
        "funnel_package_id": "demo-funnel-package-3f",
        "funnel_version": 1,
        "message": _message(),
        "offer": _offer(),
        "method": _method(),
        "amplifier": _amplifier(),
        "claims": _claims(),
        "funnel": _funnel(),
        "swimlanes": _swimlanes(),
        "swimlanes_version": 1,
        "stage_owner": DEMO_OWNER,
        "approver": DEMO_APPROVER,
        "proposed_by": DEMO_OWNER,
        "scope": "stage-9-launch-qa",
        "checkpoint_evidence": (
            "Demo: prospect path dry run routed all handoffs"
        ),
        "rationale": (
            "Demo: the funnel completed capture, engagement and conversion"
        ),
        "assigned_owner": DEMO_OWNER,
        "due_on": "2026-10-17",
        "on": "2026-10-03",
        "correlation_id": "demo-corr-stage-8",
    }


def stage_nine_payload() -> dict[str, Any]:
    return {
        "workspace_id": DEMO_WORKSPACE_ID,
        "qa_package_id": "demo-launch-package-3f",
        "qa_version": 1,
        "message": _message(),
        "offer": _offer(),
        "method": _method(),
        "amplifier": _amplifier(),
        "claims": _claims(),
        "funnel": _funnel(),
        "swimlanes": _swimlanes(),
        "swimlanes_version": 1,
        "enrollment": _enrollment(),
        "enrollment_version": 1,
        "product_program": _program(),
        "client_process": _client_process(),
        "client_process_version": 1,
        "qa": _qa(),
        "stage_owner": DEMO_OWNER,
        "approver": DEMO_APPROVER,
        "proposed_by": DEMO_OWNER,
        "scope": "stage-10-traffic",
        "checkpoint_evidence": (
            "Demo: all critical path checks passed and owned"
        ),
        "rationale": "Demo: the designated authority authorized traffic",
        "assigned_owner": DEMO_OWNER,
        "due_on": "2026-10-17",
        "on": "2026-10-03",
        "correlation_id": "demo-corr-stage-9",
    }


def stage_ten_payload() -> dict[str, Any]:
    return {
        "workspace_id": DEMO_WORKSPACE_ID,
        "baseline_package_id": "demo-baseline-package-3f",
        "baseline_version": 1,
        "message": _message(),
        "offer": _offer(),
        "method": _method(),
        "amplifier": _amplifier(),
        "claims": _claims(),
        "funnel": _funnel(),
        "qa": _qa(),
        "baseline": _baseline(),
        "nurture": _nurture(),
        "nurture_version": 1,
        "stage_owner": DEMO_OWNER,
        "approver": DEMO_APPROVER,
        "proposed_by": DEMO_OWNER,
        "scope": "stage-10-baseline",
        "checkpoint_evidence": (
            "Demo: first qualified traffic observed and recorded"
        ),
        "rationale": "Demo: the baseline is grounded on the authorized launch",
        "assigned_owner": DEMO_OWNER,
        "due_on": "2026-10-17",
        "on": "2026-10-03",
        "correlation_id": "demo-corr-stage-10",
    }


def _stage_payloads() -> tuple[dict[str, Any], ...]:
    return (
        stage_zero_payload(),
        stage_one_payload(),
        stage_two_payload(),
        stage_three_payload(),
        stage_four_payload(),
        stage_five_payload(),
        stage_six_payload(),
        stage_seven_payload(),
        stage_eight_payload(),
        stage_nine_payload(),
        stage_ten_payload(),
    )


def demo_sources() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "demo-source-intake",
            "locator": "demo://3f/intake-notes",
            "checksum": "sha256:demo-intake",
            "captured_on": "2026-10-01",
            "access_rule": "client-and-red-only",
        },
        {
            "source_id": "demo-source-diagnosis",
            "locator": "demo://3f/diagnosis-notes",
            "checksum": "sha256:demo-diagnosis",
            "captured_on": "2026-10-01",
            "access_rule": "client-and-red-only",
        },
        {
            "source_id": "demo-source-method",
            "locator": "demo://3f/method-notes",
            "checksum": "sha256:demo-method",
            "captured_on": "2026-10-01",
            "access_rule": "client-and-red-only",
        },
    ]


def demo_claims() -> list[dict[str, Any]]:
    return [
        {
            "claim_id": "demo-claim-intake-1",
            "tenant_id": DEMO_TENANT,
            "statement": "Demo: intake fact recorded with the client",
            "provenance": "known",
            "confidence_note": "demo: captured during intake",
            "citations": [
                {
                    "source_id": "demo-source-intake",
                    "checksum": "sha256:demo-intake",
                    "location": "p.1",
                }
            ],
        },
        {
            "claim_id": "demo-claim-voice-1",
            "tenant_id": DEMO_TENANT,
            "statement": (
                "Demo: stage 1 diagnosis fact recorded with the client"
            ),
            "provenance": "known",
            "confidence_note": "demo: captured during diagnosis",
            "citations": [
                {
                    "source_id": "demo-source-diagnosis",
                    "checksum": "sha256:demo-diagnosis",
                    "location": "p.2",
                }
            ],
        },
        {
            "claim_id": "demo-claim-offer-1",
            "tenant_id": DEMO_TENANT,
            "statement": (
                "Demo: stage 1 diagnosis fact recorded with the client"
            ),
            "provenance": "known",
            "confidence_note": "demo: captured during diagnosis",
            "citations": [
                {
                    "source_id": "demo-source-diagnosis",
                    "checksum": "sha256:demo-diagnosis",
                    "location": "p.2",
                }
            ],
        },
        {
            "claim_id": "demo-claim-offer-2",
            "tenant_id": DEMO_TENANT,
            "statement": (
                "Demo: stage 1 diagnosis fact recorded with the client"
            ),
            "provenance": "known",
            "confidence_note": "demo: captured during diagnosis",
            "citations": [
                {
                    "source_id": "demo-source-diagnosis",
                    "checksum": "sha256:demo-diagnosis",
                    "location": "p.2",
                }
            ],
        },
        {
            "claim_id": "demo-claim-1",
            "tenant_id": DEMO_TENANT,
            "statement": "Demo: method fact recorded with the client",
            "provenance": "known",
            "confidence_note": "demo: directly observed",
            "citations": [
                {
                    "source_id": "demo-source-method",
                    "checksum": "sha256:demo-method",
                    "location": "p.1",
                }
            ],
        },
    ]


def demo_builds() -> list[dict[str, Any]]:
    return [
        {
            "build_id": "demo-build-amplifier-video",
            "tenant_id": DEMO_TENANT,
            "build_type": "video",
            "purpose": "Demo: produce the authority amplifier video",
            "audience": "Demo: 3f pilot prospects",
            "owner": "demo-production-manager",
            "next_action": "Demo: record the amplifier video",
            "refs": _demo_asset_ids(
                CANONICAL_INTAKE_KINDS,
                CANONICAL_DIAGNOSIS_KINDS,
                CANONICAL_CURRENCY_KINDS,
                CANONICAL_DIAGNOSTIC_KINDS,
                CANONICAL_SIGNATURE_KINDS,
                CANONICAL_OFFER_KINDS,
                CANONICAL_MESSAGE_KINDS,
                CANONICAL_AMPLIFIER_KINDS,
            ),
        },
        {
            "build_id": "demo-build-landing-pages",
            "tenant_id": DEMO_TENANT,
            "build_type": "page",
            "purpose": "Demo: build the funnel landing pages",
            "audience": "Demo: 3f pilot prospects",
            "owner": "demo-integration-manager",
            "next_action": "Demo: publish the landing pages",
            "refs": _demo_asset_ids(
                CANONICAL_INTAKE_KINDS,
                CANONICAL_DIAGNOSIS_KINDS,
                CANONICAL_CURRENCY_KINDS,
                CANONICAL_DIAGNOSTIC_KINDS,
                CANONICAL_SIGNATURE_KINDS,
                CANONICAL_OFFER_KINDS,
                CANONICAL_MESSAGE_KINDS,
                CANONICAL_AMPLIFIER_KINDS,
                CANONICAL_FUNNEL_KINDS,
            ),
        },
        {
            "build_id": "demo-build-baseline-dashboard",
            "tenant_id": DEMO_TENANT,
            "build_type": "dashboard",
            "purpose": "Demo: build the performance baseline dashboard",
            "audience": "Demo: 3f pilot operators",
            "owner": "demo-baseline-owner",
            "next_action": "Demo: wire the baseline metrics",
            "refs": _demo_asset_ids(
                CANONICAL_INTAKE_KINDS,
                CANONICAL_DIAGNOSIS_KINDS,
                CANONICAL_CURRENCY_KINDS,
                CANONICAL_DIAGNOSTIC_KINDS,
                CANONICAL_SIGNATURE_KINDS,
                CANONICAL_OFFER_KINDS,
                CANONICAL_MESSAGE_KINDS,
                CANONICAL_AMPLIFIER_KINDS,
                CANONICAL_FUNNEL_KINDS,
                CANONICAL_LAUNCH_KINDS,
                CANONICAL_BASELINE_KINDS,
            ),
        },
    ]


def _require_status(response: Any, expected: int) -> None:
    if response.status_code != expected:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise SeedError(
            f"seed step expected HTTP {expected} but got "
            f"{response.status_code}: {detail}",
            status_code=response.status_code,
            detail=detail,
        )


def seed_pilot_workspace(
    client: Any, *, tenant_id: str = DEMO_TENANT
) -> dict[str, Any]:
    """Seed the pilot workspace idempotently through the real routes."""

    report: dict[str, Any] = {
        "tenant_id": tenant_id,
        "workspace_id": DEMO_WORKSPACE_ID,
        "workspace_created": False,
        "sources_created": [],
        "claims_created": [],
        "builds_created": [],
        "gates_recorded": [],
        "gates_already_approved": [],
    }

    response = client.get("/red/clients", params={"tenant_id": tenant_id})
    _require_status(response, 200)
    workspaces = response.json()["workspaces"]
    if not any(
        workspace["workspace_id"] == DEMO_WORKSPACE_ID
        for workspace in workspaces
    ):
        response = client.post(
            "/red/clients",
            json={
                "workspace_id": DEMO_WORKSPACE_ID,
                "tenant_id": tenant_id,
                "authorities": [
                    {"actor": DEMO_OWNER, "authority": "production-owner"},
                    {
                        "actor": DEMO_APPROVER,
                        "authority": "client-designated-authority",
                    },
                ],
            },
        )
        _require_status(response, 201)
        report["workspace_created"] = True

    response = client.get(f"/red/clients/{tenant_id}/sources")
    _require_status(response, 200)
    existing_sources = {
        source["source_id"] for source in response.json()["sources"]
    }
    for source in demo_sources():
        if source["source_id"] in existing_sources:
            continue
        response = client.post(
            f"/red/clients/{tenant_id}/sources", json=source
        )
        _require_status(response, 201)
        report["sources_created"].append(source["source_id"])

    response = client.get("/red/claims", params={"tenant_id": tenant_id})
    _require_status(response, 200)
    existing_claims = {
        claim["claim_id"] for claim in response.json()["claims"]
    }
    for claim in demo_claims():
        if claim["claim_id"] in existing_claims:
            continue
        response = client.post("/red/claims", json=claim)
        _require_status(response, 201)
        report["claims_created"].append(claim["claim_id"])

    response = client.get("/red/builds", params={"tenant_id": tenant_id})
    _require_status(response, 200)
    existing_builds = {
        build["build_id"] for build in response.json()["builds"]
    }
    for build in demo_builds():
        if build["build_id"] in existing_builds:
            continue
        response = client.post("/red/builds", json=build)
        _require_status(response, 201)
        report["builds_created"].append(build["build_id"])

    response = client.get("/red/decisions", params={"tenant_id": tenant_id})
    _require_status(response, 200)
    approved = {
        decision["stage_number"]
        for decision in response.json()["decisions"]
        if decision["disposition"] == "approved"
    }
    for stage_number, payload in enumerate(_stage_payloads()):
        if stage_number in approved:
            report["gates_already_approved"].append(stage_number)
            continue
        response = client.post(
            f"/red/clients/{tenant_id}/stages/{stage_number}/gate",
            json=payload,
        )
        _require_status(response, 201)
        report["gates_recorded"].append(stage_number)

    return report


def seed_from_env(
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Seed the pilot workspace into the database named by ``DATABASE_URL``."""

    env = os.environ if environ is None else environ
    database_url = env.get("DATABASE_URL")
    if not database_url or not database_url.strip():
        raise SeedConfigurationError(
            "DATABASE_URL is required to seed the pilot workspace; per-request "
            "in-memory stores cannot persist a seed"
        )

    from fastapi.testclient import TestClient

    from redops.api.app import create_app

    client = TestClient(create_app())
    return seed_pilot_workspace(client)


def main(argv: list[str] | None = None) -> int:
    report = seed_from_env()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
