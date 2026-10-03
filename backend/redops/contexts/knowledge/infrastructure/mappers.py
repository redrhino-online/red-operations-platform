"""Row serialisation for the ``SourceRecordStore`` port (SPEC.md section 6).

The durable and process-local adapters share one payload shape so a reload is
re-validated through the ``SourceRecord`` value object rather than trusted as
stored: the locator, checksum, capture time and access rule all round-trip, and
a stored row the value object would reject raises on load instead of being read
back as a real source (SPEC.md section 3).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any

from redops.contexts.knowledge.domain.entities import Claim, SourceRecord
from redops.contexts.knowledge.domain.value_objects import (
    ClaimRevision,
    ProvenanceClass,
    SourceCitation,
)


def source_to_payload(source: SourceRecord) -> dict[str, Any]:
    """Serialise an immutable source record."""

    return {
        "source_id": source.source_id,
        "tenant_id": source.tenant_id,
        "locator": source.locator,
        "checksum": source.checksum,
        "captured_on": source.captured_on.isoformat(),
        "access_rule": source.access_rule,
    }


def source_from_payload(payload: dict[str, Any]) -> SourceRecord:
    """Rebuild a source record from a stored payload, re-validating its fields."""

    return SourceRecord(
        source_id=payload["source_id"],
        tenant_id=payload["tenant_id"],
        locator=payload["locator"],
        checksum=payload["checksum"],
        captured_on=date.fromisoformat(payload["captured_on"]),
        access_rule=payload["access_rule"],
    )


def claim_to_payload(claim: Claim) -> dict[str, Any]:
    """Serialise a claim, its citations and its append-only revision history."""

    return {
        "claim_id": claim.claim_id,
        "tenant_id": claim.tenant_id,
        "statement": claim.statement,
        "provenance": claim.provenance.value,
        "confidence_note": claim.confidence_note,
        "citations": [
            {
                "source_id": citation.source_id,
                "checksum": citation.checksum,
                "location": citation.location,
            }
            for citation in sorted(
                claim.citations,
                key=lambda item: (item.source_id, item.location, item.checksum),
            )
        ],
        "revisions": [
            {
                "actor": revision.actor,
                "rationale": revision.rationale,
                "occurred_at": revision.occurred_at.isoformat(),
                "old_provenance": revision.old_provenance.value,
                "new_provenance": revision.new_provenance.value,
                "correlation_id": revision.correlation_id,
            }
            for revision in claim.revisions
        ],
    }


def claim_from_payload(payload: dict[str, Any]) -> Claim:
    """Rebuild a claim from a stored payload, re-validating its fields.

    The provenance class and each citation and revision are rebuilt through their
    value objects, so a stored row the domain would reject (for example a Known
    claim with no direct citation) raises on load rather than being read back as a
    real claim (SPEC.md sections 3 and 11).
    """

    claim = Claim(
        claim_id=payload["claim_id"],
        tenant_id=payload["tenant_id"],
        statement=payload["statement"],
        provenance=ProvenanceClass(payload["provenance"]),
        citations=frozenset(
            SourceCitation(
                source_id=citation["source_id"],
                checksum=citation["checksum"],
                location=citation["location"],
            )
            for citation in payload.get("citations", [])
        ),
        confidence_note=payload["confidence_note"],
    )
    revisions = tuple(
        ClaimRevision(
            actor=revision["actor"],
            rationale=revision["rationale"],
            occurred_at=date.fromisoformat(revision["occurred_at"]),
            old_provenance=ProvenanceClass(revision["old_provenance"]),
            new_provenance=ProvenanceClass(revision["new_provenance"]),
            correlation_id=revision["correlation_id"],
        )
        for revision in payload.get("revisions", [])
    )
    return replace(claim, _revisions=revisions)
