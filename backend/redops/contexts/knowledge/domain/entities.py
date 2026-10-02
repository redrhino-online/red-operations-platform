"""Aggregates for the Knowledge bounded context (pure domain).

SourceRecord preserves the immutable original a claim can point at, and Claim
carries a statement with an explicit provenance class and checksum and location
based citations (SPEC.md section 3). The central invariant is that a Known claim
must cite at least one SourceRecord and that Derived or Proposed claims cannot
silently become Known.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

from redops.contexts.knowledge.domain.errors import (
    ClaimProvenanceError,
    InvalidClaimError,
    InvalidSourceRecordError,
    UnsupportedClaimError,
)
from redops.contexts.knowledge.domain.value_objects import (
    ClaimRevision,
    ProvenanceClass,
    SourceCitation,
)


def _require_text(value: str, label: str) -> str:
    if not value or not value.strip():
        raise InvalidClaimError(f"{label} is required")
    return value


@dataclass(frozen=True)
class SourceRecord:
    """An immutable reference to original client material (SPEC.md section 3).

    Records the original bytes reference (locator), a checksum, the capture
    time, and an access rule. It is a frozen value: the original can never be
    rewritten after ingestion, and authorized retrieval is governed by the
    access rule. Claims cite it by checksum and exact location.
    """

    source_id: str
    tenant_id: str
    locator: str
    checksum: str
    captured_on: date
    access_rule: str

    def __post_init__(self) -> None:
        for label, value in (
            ("source id", self.source_id),
            ("source tenant id", self.tenant_id),
            ("source locator", self.locator),
            ("source checksum", self.checksum),
            ("source access rule", self.access_rule),
        ):
            if not value or not value.strip():
                raise InvalidSourceRecordError(f"{label} is required")
        if self.captured_on is None:
            raise InvalidSourceRecordError("source capture time is required")

    def cite(self, location: str) -> SourceCitation:
        """Reference an exact location inside this immutable original.

        The citation pins this source's id and checksum so retrieval can verify
        the bytes it opens are the ones recorded at ingestion.
        """
        return SourceCitation(
            source_id=self.source_id,
            checksum=self.checksum,
            location=location,
        )


@dataclass(frozen=True)
class Claim:
    """A statement with an explicit provenance class and citations.

    Required fields come from the SPEC.md section 3 aggregate table: statement,
    provenance class, citations and a confidence note. A Known claim must cite
    at least one direct source; a Derived, Proposed or Unknown claim may stand
    without one. Because the claim is frozen, provenance only changes through
    ``reclassify``, which demands a rationale and, for Known, a direct citation,
    so Derived and Proposed can never silently become Known.
    """

    claim_id: str
    tenant_id: str
    statement: str
    provenance: ProvenanceClass
    citations: frozenset[SourceCitation] = field(default_factory=frozenset)
    confidence_note: str = ""
    _revisions: tuple[ClaimRevision, ...] = field(
        default=(), repr=False, compare=False
    )

    def __post_init__(self) -> None:
        _require_text(self.claim_id, "claim id")
        _require_text(self.tenant_id, "claim tenant id")
        _require_text(self.statement, "claim statement")
        _require_text(self.confidence_note, "claim confidence note")
        if self.provenance.requires_direct_source and not self.citations:
            raise UnsupportedClaimError(
                "a Known claim must cite at least one direct source record"
            )

    @property
    def is_directly_sourced(self) -> bool:
        return bool(self.citations)

    @property
    def revisions(self) -> tuple[ClaimRevision, ...]:
        return self._revisions

    def reclassify(
        self,
        *,
        provenance: ProvenanceClass,
        actor: str,
        rationale: str,
        on: date,
        correlation_id: str,
        citations: frozenset[SourceCitation] = frozenset(),
    ) -> Claim:
        """Return a new claim with an explicitly justified provenance change.

        A promotion to Known requires at least one direct citation and a
        non-empty rationale, and every change records an actor and correlation
        ID. The original claim is left untouched, so history is preserved and
        the change is never silent (SPEC.md sections 3 and 4).
        """
        _require_text(actor, "claim revision actor")
        _require_text(correlation_id, "claim revision correlation id")
        if not rationale or not rationale.strip():
            raise ClaimProvenanceError(
                "a claim provenance change requires a rationale"
            )
        merged = self.citations | frozenset(citations)
        if provenance.requires_direct_source and not merged:
            raise UnsupportedClaimError(
                "a claim cannot be promoted to Known without a direct source "
                "citation"
            )
        revision = ClaimRevision(
            actor=actor,
            rationale=rationale,
            occurred_at=on,
            old_provenance=self.provenance,
            new_provenance=provenance,
            correlation_id=correlation_id,
        )
        return replace(
            self,
            provenance=provenance,
            citations=merged,
            _revisions=self._revisions + (revision,),
        )
