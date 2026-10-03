"""Shared pure-domain fixtures for Commercial Design tests.

These build a valid stage 5 `DeliverySpecification` so tests that approve an
OfferVersion can pin its required stage 5 asset without restating the same
content in every file. They are test data only and carry no behavior.
"""

from __future__ import annotations

from datetime import date

from redops.contexts.commercial.domain.entities import CampaignMessage, OfferVersion
from redops.contexts.commercial.domain.value_objects import (
    AUTHORITY_AMPLIFIER_BEATS,
    ContentChannel,
    ContentCrusher,
    ContentPromise,
    ContentRoadmap,
    ContentTopic,
    DeliverySpecification,
    MethodReference,
    ProductMatrixModel,
    ProductModule,
    ProductProgram,
    ProgramCadence,
    ProgramPricingBasis,
    StepDelivery,
)
from redops.contexts.method.domain.entities import MethodVersion, SignatureSolution
from redops.contexts.method.domain.value_objects import SemanticVersion

from ..method.fixtures import (
    diagnostic_model,
    primary_currency,
    signature_solution,
)

TENANT = "client-3f"
USE = "3f pilot campaign"
TODAY = date(2026, 10, 2)


def step_delivery(
    step_id: str = "step-1", tenant_id: str = TENANT, **overrides
) -> StepDelivery:
    values = {
        "step_id": step_id,
        "tenant_id": tenant_id,
        "action": f"deliver {step_id}",
        "actor": "red-specialist",
        "deliverable": f"{step_id} artifact",
        "timing": "within the engagement phase",
        "measure": f"{step_id} outcome observed",
    }
    values.update(overrides)
    return StepDelivery(**values)


def step_deliveries(
    solution: SignatureSolution, tenant_id: str = TENANT
) -> tuple[StepDelivery, ...]:
    return tuple(step_delivery(step.step_id, tenant_id) for step in solution.steps)


def delivery_specification(**overrides) -> DeliverySpecification:
    solution = overrides.pop("signature_solution", None) or signature_solution()
    values = {
        "delivery_id": "delivery-3f",
        "tenant_id": solution.tenant_id,
        "signature_solution": solution,
        "delivery_model": "done-with-you implementation",
        "duration": "12 weeks",
        "modules": ("diagnose", "productize", "launch"),
        "responsibilities": ("red builds", "client reviews"),
        "support_cadence": "weekly working session",
        "step_deliveries": step_deliveries(solution, solution.tenant_id),
        "outcome_measures": ("qualified referrals per month",),
        "pricing_payments": "USD 7,500 in three instalments",
        "scope": "one campaign, one offer, one avatar",
        "guarantee_decision": "no guarantee in the pilot",
        "eligibility": "service businesses with a proven offer",
        "offer_stack": ("core engagement", "follow-on optimization"),
    }
    values.update(overrides)
    return DeliverySpecification(**values)


def product_program(
    solution: SignatureSolution | None = None, **overrides
) -> ProductProgram:
    solution = solution or signature_solution()
    modules = tuple(
        ProductModule(
            module_id=f"module-{index + 1}",
            tenant_id=solution.tenant_id,
            signature_step=step.name,
            position=index + 1,
            outcome=f"the client reaches {step.name}",
            deliverable=f"the {step.name} worksheet",
        )
        for index, step in enumerate(solution.steps)
    )
    values = {
        "program_id": "program-3f",
        "tenant_id": solution.tenant_id,
        "owner": "red-offer-owner",
        "method": solution,
        "model": ProductMatrixModel.GROUP_CONSULTING,
        "pricing_basis": ProgramPricingBasis.OUTCOME_VALUE,
        "duration_weeks": 9,
        "cadence": ProgramCadence.MONDAY_TRAINING_THURSDAY_COACHING,
        "modules": modules,
    }
    values.update(overrides)
    return ProductProgram(**values)


def content_roadmap(
    solution: SignatureSolution | None = None, **overrides
) -> ContentRoadmap:
    """A valid stage 6 content roadmap mapped from a Signature Solution."""

    solution = solution or signature_solution()
    topics = tuple(
        ContentTopic(
            topic_id=f"topic-{index + 1}",
            tenant_id=solution.tenant_id,
            name=f"{step.name} audience questions",
            signature_step=step.name,
            question=f"what does {step.name} change for the client?",
            channels=(ContentChannel.BLOG,),
            script_beats=AUTHORITY_AMPLIFIER_BEATS,
        )
        for index, step in enumerate(solution.steps)
    )
    values = {
        "roadmap_id": "roadmap-3f",
        "tenant_id": solution.tenant_id,
        "owner": "content-owner",
        "method": solution,
        "topics": topics,
    }
    values.update(overrides)
    return ContentRoadmap(**values)


def content_crusher(
    roadmap: ContentRoadmap | None = None, **overrides
) -> ContentCrusher:
    """A valid stage 6 content crusher outlining the roadmap's first topic."""

    roadmap = roadmap or content_roadmap()
    topic = roadmap.topics[0]
    values = {
        "crusher_id": "crusher-3f",
        "tenant_id": roadmap.tenant_id,
        "owner": "content-owner",
        "roadmap": roadmap,
        "topic_id": topic.topic_id,
        "title": f"why {topic.name} matters now",
        "promise": ContentPromise(
            measure="a measurable result", timeline="within 90 days"
        ),
        "frustrations": ("the current approach stalls",),
        "goal": "reach the next level with confidence",
        "model": "the transformation model",
        "metaphor": "a map for the journey",
        "context": "part of the signature program",
        "steps": (topic.signature_step,),
        "story": "a client who made the shift",
        "choice": "keep guessing or follow the method",
        "action": "book the next step",
    }
    values.update(overrides)
    return ContentCrusher(**values)


def approved_method(
    version: SemanticVersion = SemanticVersion(1, 0, 0),
    tenant_id: str = TENANT,
    method_id: str = "method-3f",
    intended_use: str = USE,
    solution: SignatureSolution | None = None,
) -> MethodVersion:
    return MethodVersion(
        method_id=method_id,
        tenant_id=tenant_id,
        parent_method="signature-solution",
        semantic_version=version,
        stages=("diagnose", "position", "model"),
        currency="qualified-referrals",
        claims=frozenset({"claim-1"}),
        primary_currency=primary_currency(tenant_id),
        diagnostic_model=diagnostic_model(tenant_id),
        signature_solution=(
            signature_solution(tenant_id) if solution is None else solution
        ),
    ).approve(approved_by="client-authority", intended_use=intended_use, on=TODAY)


def offer_version(**overrides) -> OfferVersion:
    values = {
        "offer_id": "offer-1",
        "tenant_id": TENANT,
        "audience": "owner-operators",
        "promise": "twice the qualified referrals",
        "eligibility": "service businesses with a proven offer",
        "price_hypothesis": "USD 7,500",
        "method_refs": (
            MethodReference(
                method_id="method-3f",
                version=SemanticVersion(1, 0, 0),
                intended_use=USE,
            ),
        ),
        "owner": "offer-owner",
        "delivery_specification": delivery_specification(),
    }
    values.update(overrides)
    return OfferVersion(**values)


def production_ready_offer(
    methods: tuple[MethodVersion, ...] | None = None, **overrides
) -> OfferVersion:
    offer = offer_version(**overrides)
    return offer.require_production_ready(
        methods if methods is not None else (approved_method(),)
    )


def campaign_message(offer: OfferVersion | None = None, **overrides) -> CampaignMessage:
    offer = production_ready_offer() if offer is None else offer
    values = {
        "message_id": "message-3f",
        "tenant_id": offer.tenant_id,
        "offer": offer,
        "owner": "message-owner",
        "avatar": offer.audience,
        "currency": "qualified referrals",
        "problem": "Stuck problems",
        "promise": offer.promise,
        "cta": "Book a diagnostic call",
        "method_reference": offer.method_refs[0],
        "product_offer_id": offer.offer_id,
        "problem_hierarchy": (
            "no predictable referral flow",
            "referrals depend on luck",
        ),
        "desired_outcome": "a predictable referral engine",
        "proof_objections": (
            "proof: referral partner network",
            "objection: no time to build it",
        ),
        "story": "an owner-operator story",
        "method_explanation": "install the referral partner network in nine steps",
        "lead_magnet": "referral readiness checklist",
        "hook": "why referrals stall at four a month",
        "angles": ("referral drought", "referral engine"),
        "landing_message": "turn referrals into a system",
        "authority_amplifier_outline": (
            "Promise, Proof, Problems, Steps, Context, Action"
        ),
    }
    values.update(overrides)
    return CampaignMessage(**values)


def approved_campaign_message(
    offer: OfferVersion | None = None, **overrides
) -> CampaignMessage:
    """An approved stage 6 message congruent with the approved method and offer."""

    approved = approved_method()
    return campaign_message(offer=offer, **overrides).approve((approved,))
