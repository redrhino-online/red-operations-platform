"""RED specialist agents registered through the OpenExecutive mechanism (ADR 0011).

This module is applied by ``scripts/apply_vendor_overlay.sh`` and registers RED's
nine core section 5 specialists through the fork's existing specialist registry
(ADR 0006): each agent is a ``BaseAgent`` subclass with a RED prompt, so the
fork's routing, caching, retrieval and eval machinery is inherited rather than
reimplemented. The registries here are merged into
``orchestrator/router.py``'s ``SPECIALIST_REGISTRY``/``SPECIALIST_DESCRIPTIONS``
and ``orchestrator/answer_sources.py``'s ``_AREAS`` by the overlay hook.

Capability slots 10 and 11 are chartered but deliberately absent: SPEC.md
section 5 reserves them as proposal-only with no execution permissions, and their
charters live in ``docs/agents/``. The generic corporate personas stay in place;
retiring them is a separate characterised change (ADR 0006), not part of this
overlay.
"""

from __future__ import annotations

from openexecutive.agents.base import BaseAgent
from openexecutive.prompts import redops_prompts


class _RedAgent(BaseAgent):
    """Shared RED specialist behaviour; only the prompt differs per agent."""

    visibility = "core"
    model = "claude-sonnet-5"

    def get_system_prompt(self) -> str:
        return self.prompt()


class DiscoveryAgent(_RedAgent):
    name = "discovery"
    domain = "discovery"

    def prompt(self) -> str:
        return redops_prompts.DISCOVERY_PROMPT


class IPStructuringAgent(_RedAgent):
    name = "ip_structuring"
    domain = "method"

    def prompt(self) -> str:
        return redops_prompts.IP_STRUCTURING_PROMPT


class OfferJourneyAgent(_RedAgent):
    name = "offer_journey"
    domain = "commercial"

    def prompt(self) -> str:
        return redops_prompts.OFFER_JOURNEY_PROMPT


class KnowledgeAgent(_RedAgent):
    name = "knowledge"
    domain = "knowledge"

    def prompt(self) -> str:
        return redops_prompts.KNOWLEDGE_PROMPT


class GovernanceAgent(_RedAgent):
    name = "governance"
    domain = "governance"

    def prompt(self) -> str:
        return redops_prompts.GOVERNANCE_PROMPT


class AssetProductionAgent(_RedAgent):
    name = "asset_production"
    domain = "production"

    def prompt(self) -> str:
        return redops_prompts.ASSET_PRODUCTION_PROMPT


class CampaignExecutionAgent(_RedAgent):
    name = "campaign_execution"
    domain = "execution"

    def prompt(self) -> str:
        return redops_prompts.CAMPAIGN_EXECUTION_PROMPT


class InsightAgent(_RedAgent):
    name = "insight"
    domain = "measurement"

    def prompt(self) -> str:
        return redops_prompts.INSIGHT_PROMPT


class IPPortfolioAgent(_RedAgent):
    name = "ip_portfolio"
    domain = "portfolio"

    def prompt(self) -> str:
        return redops_prompts.IP_PORTFOLIO_PROMPT


RED_SPECIALIST_REGISTRY: dict[str, BaseAgent] = {
    agent.name: agent
    for agent in (
        DiscoveryAgent(),
        IPStructuringAgent(),
        OfferJourneyAgent(),
        KnowledgeAgent(),
        GovernanceAgent(),
        AssetProductionAgent(),
        CampaignExecutionAgent(),
        InsightAgent(),
        IPPortfolioAgent(),
    )
}

RED_SPECIALIST_DESCRIPTIONS: dict[str, str] = {
    "discovery": "Discovery and Diagnosis — intake, diagnosis, avatar and the unknowns register",
    "ip_structuring": "IP Structuring — the Signature Solution and its versioned milestones",
    "offer_journey": "Offer and Journey Design — the offer specification and the customer path",
    "knowledge": "Knowledge Management — ingestion, indexing and tenant-scoped retrieval",
    "governance": "Governance and Approval — gate states, change impact and the decision log",
    "asset_production": "Business Asset Production — briefs and traced deliverables",
    "campaign_execution": "Campaign and Journey Execution — implementation, launch checks and incidents",
    "insight": "Insight and Performance — baseline, review and measured recommendations",
    "ip_portfolio": "IP Portfolio Development — derivative opportunities and investment cases",
}

RED_SPECIALIST_AREAS: dict[str, str] = {
    "discovery": "discovery and diagnosis",
    "ip_structuring": "IP structuring",
    "offer_journey": "offer and journey design",
    "knowledge": "knowledge management",
    "governance": "governance and approval",
    "asset_production": "asset production",
    "campaign_execution": "campaign execution",
    "insight": "insight and performance",
    "ip_portfolio": "IP portfolio development",
}
