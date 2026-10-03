"""Row serialisation for the Portfolio opportunity register (SPEC.md section 6).

A stored opportunity is re-validated through the ``Opportunity`` value object on
load rather than trusted as stored, so a malformed row -- including one recorded
as an already-approved expansion -- cannot be read back as a client fact (SPEC.md
sections 1 and 5). Keeping the mapping here separates the durability concern from
the pure domain value object.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from redops.contexts.governance.domain.value_objects import StageAssetVersion
from redops.contexts.portfolio.domain.value_objects import (
    Opportunity,
    OpportunityKind,
    OpportunityState,
)


def opportunity_to_payload(opportunity: Opportunity) -> dict[str, Any]:
    """Serialise an opportunity proposal for durable storage."""

    return {
        "opportunity_id": opportunity.opportunity_id,
        "tenant_id": opportunity.tenant_id,
        "title": opportunity.title,
        "kind": opportunity.kind.value,
        "source": {
            "asset_id": opportunity.source.asset_id,
            "tenant_id": opportunity.source.tenant_id,
            "kind": opportunity.source.kind,
            "version": opportunity.source.version,
        },
        "investment_case": opportunity.investment_case,
        "expected_outcome": opportunity.expected_outcome,
        "owner": opportunity.owner,
        "next_action": opportunity.next_action,
        "captured_on": opportunity.captured_on.isoformat(),
        "state": opportunity.state.value,
    }


def opportunity_from_payload(payload: Mapping[str, Any]) -> Opportunity:
    """Rebuild an opportunity proposal from its stored payload."""

    source = payload["source"]
    return Opportunity(
        opportunity_id=payload["opportunity_id"],
        tenant_id=payload["tenant_id"],
        title=payload["title"],
        kind=OpportunityKind(payload["kind"]),
        source=StageAssetVersion(
            asset_id=source["asset_id"],
            tenant_id=source["tenant_id"],
            kind=source["kind"],
            version=source["version"],
        ),
        investment_case=payload["investment_case"],
        expected_outcome=payload["expected_outcome"],
        owner=payload["owner"],
        next_action=payload["next_action"],
        captured_on=date.fromisoformat(payload["captured_on"]),
        state=OpportunityState(payload.get("state", "proposed")),
    )
