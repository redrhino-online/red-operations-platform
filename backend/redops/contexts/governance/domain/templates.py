"""Canonical versioned stage 0-10 production template (pure domain).

The table in SPEC.md section 4 ("RED production engagement: stages 0 through 10")
is the default gated dependency graph. This module seeds it once so gate
integrity can be evaluated against the canonical dependencies and required asset
packages rather than a gate's self-declared set. The template is data, not an
authority: it names roles (accountable, approver), not people. Named human
owners and the client-designated authority remain open decisions.
"""

from __future__ import annotations

from redops.contexts.governance.domain.value_objects import (
    StageDefinition,
    StageTemplate,
)

STAGE_ZERO_TO_TEN_VERSION = "2026.1"

_ACCOUNTABLE = {
    0: "Engagement and Governance",
    1: "Discovery and Diagnosis",
    2: "Discovery, IP Structuring, Commercial Design",
    3: "IP Structuring and Commercial Design",
    4: "IP Structuring",
    5: "Offer and Journey Design",
    6: "Offer and Journey Design, Business Asset Production",
    7: "Business Asset Production",
    8: "Campaign and Journey Execution",
    9: "Campaign and Journey Execution, Governance",
    10: "Campaign and Journey Execution, Insight and Performance",
}


def _stage(
    stage_number: int,
    name: str,
    checkpoint: str,
    required_asset_kinds: frozenset[str],
) -> StageDefinition:
    dependencies = (
        frozenset() if stage_number == 0 else frozenset({stage_number - 1})
    )
    return StageDefinition(
        stage_number=stage_number,
        name=name,
        required_asset_kinds=required_asset_kinds,
        checkpoint=checkpoint,
        accountable_role=_ACCOUNTABLE[stage_number],
        approver_role="client-designated-authority",
        dependencies=dependencies,
    )


def stage_zero_to_ten_template(
    version: str = STAGE_ZERO_TO_TEN_VERSION,
) -> StageTemplate:
    """Return the canonical 0-10 gated production template for a version."""

    return StageTemplate(
        version=version,
        stages=(
            _stage(
                0,
                "Intake",
                "Production Ready",
                frozenset(
                    {
                        "client-record",
                        "signed-scope",
                        "billing-confirmation",
                        "intake-questionnaire",
                        "brand-asset-inventory",
                        "access-checklist",
                        "baseline-measures",
                        "workspace",
                        "communication-channel",
                        "timeline",
                        "responsibilities",
                        "launch-definition",
                    }
                ),
            ),
            _stage(
                1,
                "Diagnose",
                "Avatar Locked",
                frozenset(
                    {
                        "business-snapshot",
                        "offer-funnel-audit",
                        "avatar-profile",
                        "pains",
                        "goals",
                        "consequences-of-inaction",
                        "awareness-map",
                        "audience-reach-estimate",
                        "target-market-match",
                        "customer-evidence",
                        "voice-notes",
                    }
                ),
            ),
            _stage(
                2,
                "Position",
                "Currency Locked",
                frozenset(
                    {
                        "category",
                        "currency-inventory",
                        "primary-currency",
                        "current-measures",
                        "desired-measures",
                        "horizon",
                        "qualifications",
                        "transformation-statement",
                        "core-problem",
                        "million-dollar-message",
                    }
                ),
            ),
            _stage(
                3,
                "Model",
                "Diagnostic Model Approved",
                frozenset(
                    {
                        "profit-pyramid-levels",
                        "observable-measures",
                        "level-symptoms",
                        "level-behaviors",
                        "level-problems",
                        "progression",
                        "qualification-logic",
                        "diagnostic-model-name",
                        "diagnostic-model-visual",
                        "diagnostic-model-copy",
                    }
                ),
            ),
            _stage(
                4,
                "Package IP",
                "IP Architecture Locked",
                frozenset(
                    {
                        "transformation-map",
                        "process-inventory",
                        "three-phases",
                        "nine-steps",
                        "named-stages",
                        "starting-state",
                        "final-state",
                        "stage-inputs",
                        "stage-actions",
                        "stage-outputs",
                        "transformation-narrative",
                        "transformation-visual",
                        "thirteen-transformations",
                    }
                ),
            ),
            _stage(
                5,
                "Productize",
                "Offer Locked",
                frozenset(
                    {
                        "delivery-model",
                        "duration",
                        "modules",
                        "responsibilities",
                        "support-cadence",
                        "stage-deliverables",
                        "outcome-measures",
                        "pricing-payments",
                        "scope",
                        "guarantee-decision",
                        "eligibility",
                        "offer-stack",
                        "product-program",
                    }
                ),
            ),
            _stage(
                6,
                "Message",
                "Campaign Message Approved",
                frozenset(
                    {
                        "promise",
                        "problem-hierarchy",
                        "desired-outcome",
                        "proof-objections",
                        "story",
                        "method-explanation",
                        "cta",
                        "lead-magnet",
                        "hook",
                        "angles",
                        "landing-message",
                        "authority-amplifier-outline",
                    }
                ),
            ),
            _stage(
                7,
                "Produce",
                "Authority Amplifier Approved",
                frozenset(
                    {
                        "authority-amplifier-script",
                        "aa-storyboard",
                        "brand-treatment",
                        "aa-presentation",
                        "aa-speaker-notes",
                        "aa-recording",
                        "aa-edited-video",
                        "aa-hosted-video",
                        "aa-player-assets",
                    }
                ),
            ),
            _stage(
                8,
                "Integrate",
                "Funnel Complete",
                frozenset(
                    {
                        "campaign-architecture",
                        "pages",
                        "forms",
                        "qualification",
                        "booking",
                        "sequences",
                        "crm",
                        "tags",
                        "automation",
                        "analytics",
                        "tracking",
                        "sales-handoff",
                        "sops",
                    }
                ),
            ),
            _stage(
                9,
                "QA",
                "Launch Approved",
                frozenset(
                    {
                        "recorded-message",
                        "technical-tests",
                        "commercial-tests",
                        "qa-forms",
                        "qa-crm",
                        "qa-email",
                        "qa-automation",
                        "qa-booking",
                        "qa-tracking",
                        "qa-payment",
                        "qa-handoff",
                        "client-approval",
                        "budget-approval",
                        "creative-approval",
                        "launch-dashboard",
                        "launch-decision",
                        "compliance-package",
                    }
                ),
            ),
            _stage(
                10,
                "Launch",
                "Performance Baseline Established",
                frozenset(
                    {
                        "live-campaign",
                        "spend-records",
                        "lead-records",
                        "conversion-measures",
                        "engagement-measures",
                        "applications",
                        "bookings",
                        "shows",
                        "closes",
                        "acquisition-cost",
                        "attribution",
                        "issue-log",
                    }
                ),
            ),
        ),
    )
