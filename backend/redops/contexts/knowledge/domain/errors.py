"""Named domain errors for the Knowledge bounded context (pure domain)."""

from __future__ import annotations


class KnowledgeError(Exception):
    """Base class for knowledge domain rule violations."""


class InvalidSourceRecordError(KnowledgeError, ValueError):
    """A SourceRecord or source citation was built without required evidence."""


class InvalidClaimError(KnowledgeError, ValueError):
    """A Claim was constructed or changed in a way its invariants forbid."""


class UnsupportedClaimError(InvalidClaimError):
    """A claim was asserted as Known without a direct source citation.

    SPEC.md section 11: "Known cannot be set without direct source".
    """


class ClaimProvenanceError(InvalidClaimError):
    """A claim provenance change was attempted without explicit evidence.

    SPEC.md section 3: "Derived and Proposed cannot silently become Known".
    """


class UnscopedSourceRecordError(KnowledgeError):
    """A source record store was read or written without a tenant.

    SPEC.md sections 3 and 9 make a SourceRecord a client resource and require
    every tenant resource and query to carry ``tenant_id``. Storing or resolving
    one without a client would either leak across clients or create an orphaned
    record, so the store refuses an unscoped read or write.
    """


class SourceRecordImmutableError(InvalidSourceRecordError):
    """An immutable source record was re-stated with different contents.

    SPEC.md section 3: "Original is immutable and retrievable to authorized
    users." A source record pinned by a checksum cannot be rewritten under the
    same id; a corrected capture is a new record, so the stored original a claim
    points at is never silently replaced.
    """
