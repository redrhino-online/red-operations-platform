"""Reusable sourcing policy for the Knowledge bounded context (pure domain).

SPEC.md sections 1 and 4: every output has a source, and derived or proposed
material must never silently become known. A claim is usable as evidence only
when it is a Known claim with a direct source and belongs to the same client.
This is the one place that rule is expressed, so every context that checks an
asset's evidence grounding applies the same test.
"""

from __future__ import annotations

from typing import Iterable

from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.value_objects import ProvenanceClass


def sourced_claim_ids(tenant_id: str, claims: Iterable[Claim]) -> frozenset[str]:
    """Return the claim ids that are known, directly sourced and same-tenant.

    A claim qualifies only when it belongs to this client, carries the Known
    provenance class, and cites at least one immutable source record. Derived,
    Proposed and Unknown claims never qualify, so unsupported material cannot be
    represented as source evidence.
    """
    return frozenset(
        claim.claim_id
        for claim in claims
        if claim.tenant_id == tenant_id
        and claim.provenance is ProvenanceClass.KNOWN
        and claim.is_directly_sourced
    )
