"""Value objects for the Knowledge bounded context (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from redops.contexts.knowledge.domain.errors import (
    InvalidClaimError,
    InvalidSourceRecordError,
)


class ProvenanceClass(Enum):
    """How strongly a claim is supported (SPEC.md section 3 aggregate table).

    Only KNOWN asserts a fact as directly sourced. Derived and Proposed are
    interpretations or model output, and Unknown is an explicit gap; none of
    them may silently become Known.
    """

    KNOWN = "known"
    DERIVED = "derived"
    PROPOSED = "proposed"
    UNKNOWN = "unknown"

    @property
    def requires_direct_source(self) -> bool:
        return self is ProvenanceClass.KNOWN


@dataclass(frozen=True)
class SourceCitation:
    """A checksum and location based reference to an exact source location.

    It pins the source id, the checksum observed at ingestion, and the location
    within the source, so a citation opens the exact place a claim came from and
    can be verified against the immutable original (SPEC.md sections 2 and 11).
    """

    source_id: str
    checksum: str
    location: str

    def __post_init__(self) -> None:
        for label, value in (
            ("source id", self.source_id),
            ("checksum", self.checksum),
            ("location", self.location),
        ):
            if not value or not value.strip():
                raise InvalidSourceRecordError(f"citation {label} is required")


@dataclass(frozen=True)
class ClaimRevision:
    """One recorded change of a claim's provenance class (SPEC.md section 4).

    Records the actor, rationale, timestamp, old and new provenance, and a
    correlation ID, so a claim can never be promoted without an auditable
    reason (SPEC.md section 3: Derived and Proposed cannot silently become
    Known).
    """

    actor: str
    rationale: str
    occurred_at: date
    old_provenance: ProvenanceClass
    new_provenance: ProvenanceClass
    correlation_id: str

    def __post_init__(self) -> None:
        for label, value in (
            ("claim revision actor", self.actor),
            ("claim revision rationale", self.rationale),
            ("claim revision correlation id", self.correlation_id),
        ):
            if not value or not value.strip():
                raise InvalidClaimError(f"{label} is required")
