"""Row serialisation for the Operations dismissal store (SPEC.md section 6).

A stored dismissal is re-validated through the ``InterventionDismissal`` value
object on load rather than trusted as stored, so a malformed row cannot be read
back as an operator decision (SPEC.md sections 7 and 9). Keeping the mapping here
separates the durability concern from the pure domain value object.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from redops.contexts.operations.domain.value_objects import (
    InterventionDismissal,
    InterventionReason,
)


def intervention_dismissal_to_payload(
    dismissal: InterventionDismissal,
) -> dict[str, Any]:
    """Serialise a dismissal decision for durable storage."""

    return {
        "tenant_id": dismissal.tenant_id,
        "client": dismissal.client,
        "reason": dismissal.reason.value,
        "subject": dismissal.subject,
        "rationale": dismissal.rationale,
        "actor": dismissal.actor,
        "dismissed_on": dismissal.dismissed_on.isoformat(),
    }


def intervention_dismissal_from_payload(
    payload: Mapping[str, Any],
) -> InterventionDismissal:
    """Rebuild a dismissal decision from its stored payload."""

    return InterventionDismissal(
        tenant_id=payload["tenant_id"],
        client=payload["client"],
        reason=InterventionReason(payload["reason"]),
        subject=payload["subject"],
        rationale=payload["rationale"],
        actor=payload["actor"],
        dismissed_on=date.fromisoformat(payload["dismissed_on"]),
    )
