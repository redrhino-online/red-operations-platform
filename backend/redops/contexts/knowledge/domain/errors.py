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
