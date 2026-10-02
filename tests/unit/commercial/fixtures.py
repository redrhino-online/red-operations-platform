"""Shared pure-domain fixtures for Commercial Design tests.

These build a valid stage 5 `DeliverySpecification` so tests that approve an
OfferVersion can pin its required stage 5 asset without restating the same
content in every file. They are test data only and carry no behavior.
"""

from __future__ import annotations

from redops.contexts.commercial.domain.value_objects import (
    DeliverySpecification,
    StepDelivery,
)
from redops.contexts.method.domain.entities import SignatureSolution

from ..method.fixtures import signature_solution

TENANT = "client-3f"


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
