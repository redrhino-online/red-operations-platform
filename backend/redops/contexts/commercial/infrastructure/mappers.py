"""Map the Commercial ``OfferVersion`` aggregate to and from a durable payload.

SPEC.md section 6 keeps mapping in the infrastructure layer: the domain must not
know about JSONB or table columns. The PostgreSQL adapter stores a production
ready ``OfferVersion`` as a JSONB payload plus a few indexed columns, and
rebuilds the aggregate on load by going through ``OfferVersion.__post_init__``.
Serialising every authority-bearing field -- the exact pinned ``MethodReference``
tuple and the complete stage 5 ``DeliverySpecification`` grounded on the locked
Signature Solution -- is what lets a reloaded offer re-validate rather than trust
what storage claims (SPEC.md sections 3 and 4: a passing gate pins the exact
approved asset versions and intended use, and a previous approved version stays
historically identifiable). A round trip that silently dropped a method
reference or the delivery specification would turn a stale or incomplete offer
back into a production ready one on reload.

The stage 4 Signature Solution inside the delivery specification is serialised
with the Method context's own mapper helper so the two contexts cannot drift on
the shape of that shared asset.

Canon: not applicable. This is a persistence mapper for an offer aggregate, not a
method artifact, so no reference-model file informs its shape.
"""

from __future__ import annotations

from typing import Any, Mapping

from redops.contexts.commercial.domain.entities import OfferVersion
from redops.contexts.commercial.domain.value_objects import (
    DeliverySpecification,
    MethodReference,
    OfferState,
    StepDelivery,
)
from redops.contexts.method.domain.value_objects import SemanticVersion
from redops.contexts.method.infrastructure.mappers import (
    signature_solution_from_payload,
    signature_solution_to_payload,
)


def _method_ref_to_payload(reference: MethodReference) -> dict[str, Any]:
    return {
        "method_id": reference.method_id,
        "version": str(reference.version),
        "intended_use": reference.intended_use,
    }


def _method_ref_from_payload(payload: Mapping[str, Any]) -> MethodReference:
    return MethodReference(
        method_id=str(payload["method_id"]),
        version=SemanticVersion.parse(str(payload["version"])),
        intended_use=str(payload["intended_use"]),
    )


def _step_delivery_to_payload(row: StepDelivery) -> dict[str, Any]:
    return {
        "step_id": row.step_id,
        "tenant_id": row.tenant_id,
        "action": row.action,
        "actor": row.actor,
        "deliverable": row.deliverable,
        "timing": row.timing,
        "measure": row.measure,
    }


def _step_delivery_from_payload(payload: Mapping[str, Any]) -> StepDelivery:
    return StepDelivery(
        step_id=str(payload["step_id"]),
        tenant_id=str(payload["tenant_id"]),
        action=str(payload["action"]),
        actor=str(payload["actor"]),
        deliverable=str(payload["deliverable"]),
        timing=str(payload["timing"]),
        measure=str(payload["measure"]),
    )


def _delivery_to_payload(
    delivery: DeliverySpecification,
) -> dict[str, Any]:
    return {
        "delivery_id": delivery.delivery_id,
        "tenant_id": delivery.tenant_id,
        "signature_solution": signature_solution_to_payload(
            delivery.signature_solution
        ),
        "delivery_model": delivery.delivery_model,
        "duration": delivery.duration,
        "modules": list(delivery.modules),
        "responsibilities": list(delivery.responsibilities),
        "support_cadence": delivery.support_cadence,
        "step_deliveries": [
            _step_delivery_to_payload(row) for row in delivery.step_deliveries
        ],
        "outcome_measures": list(delivery.outcome_measures),
        "pricing_payments": delivery.pricing_payments,
        "scope": delivery.scope,
        "guarantee_decision": delivery.guarantee_decision,
        "eligibility": delivery.eligibility,
        "offer_stack": list(delivery.offer_stack),
    }


def _delivery_from_payload(
    payload: Mapping[str, Any],
) -> DeliverySpecification:
    return DeliverySpecification(
        delivery_id=str(payload["delivery_id"]),
        tenant_id=str(payload["tenant_id"]),
        signature_solution=signature_solution_from_payload(
            payload["signature_solution"]
        ),
        delivery_model=str(payload["delivery_model"]),
        duration=str(payload["duration"]),
        modules=tuple(str(entry) for entry in payload["modules"]),
        responsibilities=tuple(
            str(entry) for entry in payload["responsibilities"]
        ),
        support_cadence=str(payload["support_cadence"]),
        step_deliveries=tuple(
            _step_delivery_from_payload(row)
            for row in payload["step_deliveries"]
        ),
        outcome_measures=tuple(
            str(entry) for entry in payload["outcome_measures"]
        ),
        pricing_payments=str(payload["pricing_payments"]),
        scope=str(payload["scope"]),
        guarantee_decision=str(payload["guarantee_decision"]),
        eligibility=str(payload["eligibility"]),
        offer_stack=tuple(str(entry) for entry in payload["offer_stack"]),
    )


def offer_to_payload(offer: OfferVersion) -> dict[str, Any]:
    """Serialise a production ready offer into the JSONB payload the table stores.

    The method references keep their declared order (the offer pins them as a
    tuple), and the optional delivery specification is emitted as ``None`` rather
    than dropped, so a reload cannot confuse an absent asset with a malformed one.
    """

    return {
        "offer_id": offer.offer_id,
        "tenant_id": offer.tenant_id,
        "audience": offer.audience,
        "promise": offer.promise,
        "eligibility": offer.eligibility,
        "price_hypothesis": offer.price_hypothesis,
        "owner": offer.owner,
        "state": offer.state.value,
        "review_reason": offer.review_reason,
        "method_refs": [
            _method_ref_to_payload(reference)
            for reference in offer.method_refs
        ],
        "delivery_specification": (
            _delivery_to_payload(offer.delivery_specification)
            if offer.delivery_specification is not None
            else None
        ),
    }


def offer_from_payload(payload: Mapping[str, Any]) -> OfferVersion:
    """Rebuild an offer from a stored payload for re-validation.

    Construction re-runs the aggregate invariants. A payload that storage cannot
    legally hold (a blank identity, no method reference, a delivery specification
    from another tenant) raises here rather than being read back as a production
    ready offer.
    """

    delivery = payload.get("delivery_specification")
    return OfferVersion(
        offer_id=str(payload["offer_id"]),
        tenant_id=str(payload["tenant_id"]),
        audience=str(payload["audience"]),
        promise=str(payload["promise"]),
        eligibility=str(payload["eligibility"]),
        price_hypothesis=str(payload["price_hypothesis"]),
        method_refs=tuple(
            _method_ref_from_payload(reference)
            for reference in payload["method_refs"]
        ),
        owner=str(payload["owner"]),
        state=OfferState(str(payload["state"])),
        delivery_specification=(
            _delivery_from_payload(delivery) if delivery is not None else None
        ),
        review_reason=payload.get("review_reason"),
    )
