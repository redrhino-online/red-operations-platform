"""Behavioral tests for the Claim aggregate (pure domain, Knowledge).

Rules under test come from SPEC.md sections 3 and 11:
- Claim records a statement, a Known/Derived/Proposed/Unknown class, citations
  and a confidence note (SPEC.md section 3 aggregate table).
- Derived and Proposed cannot silently become Known.
- "Known cannot be set without direct source" (SPEC.md section 11).
"""

import unittest
from datetime import date

from redops.contexts.knowledge.domain.entities import Claim, SourceRecord
from redops.contexts.knowledge.domain.errors import (
    ClaimProvenanceError,
    InvalidClaimError,
    UnsupportedClaimError,
)
from redops.contexts.knowledge.domain.value_objects import ProvenanceClass

TODAY = date(2026, 10, 2)
CORRELATION = "corr-claim-1"


def source_record() -> SourceRecord:
    return SourceRecord(
        source_id="source-1",
        tenant_id="client-3f",
        locator="s3://redops-private/client-3f/intake/questionnaire.pdf",
        checksum="sha256:8f14e45fceea167a5a36dedd4bea2543",
        captured_on=TODAY,
        access_rule="client-3f-members",
    )


def citation():
    return source_record().cite("page 4, paragraph 2")


def claim(**overrides) -> Claim:
    values = {
        "claim_id": "claim-1",
        "tenant_id": "client-3f",
        "statement": "The 3F audience struggles to convert referrals into clients",
        "provenance": ProvenanceClass.PROPOSED,
        "confidence_note": "extracted from intake call, unreviewed",
    }
    values.update(overrides)
    return Claim(**values)


class ClaimInvariantTests(unittest.TestCase):
    def test_a_proposed_claim_may_exist_without_a_citation(self):
        subject = claim()

        self.assertIs(ProvenanceClass.PROPOSED, subject.provenance)
        self.assertFalse(subject.is_directly_sourced)

    def test_a_known_claim_without_a_direct_source_is_rejected(self):
        with self.assertRaises(UnsupportedClaimError):
            claim(provenance=ProvenanceClass.KNOWN)

    def test_a_known_claim_with_a_citation_is_directly_sourced(self):
        subject = claim(provenance=ProvenanceClass.KNOWN, citations=frozenset({citation()}))

        self.assertTrue(subject.is_directly_sourced)

    def test_a_claim_without_a_statement_is_rejected(self):
        with self.assertRaises(InvalidClaimError):
            claim(statement="   ")

    def test_a_claim_without_a_confidence_note_is_rejected(self):
        with self.assertRaises(InvalidClaimError):
            claim(confidence_note="")


class ClaimReclassificationTests(unittest.TestCase):
    def test_a_proposed_claim_cannot_silently_become_known(self):
        subject = claim()

        with self.assertRaises(UnsupportedClaimError):
            subject.reclassify(
                provenance=ProvenanceClass.KNOWN,
                actor="analyst-1",
                rationale="reviewed the intake call",
                on=TODAY,
                correlation_id=CORRELATION,
            )

    def test_promotion_to_known_requires_a_rationale(self):
        with self.assertRaises(ClaimProvenanceError):
            claim().reclassify(
                provenance=ProvenanceClass.KNOWN,
                actor="analyst-1",
                rationale="   ",
                on=TODAY,
                correlation_id=CORRELATION,
                citations=frozenset({citation()}),
            )

    def test_promotion_to_known_with_evidence_returns_a_new_revised_claim(self):
        original = claim()

        promoted = original.reclassify(
            provenance=ProvenanceClass.KNOWN,
            actor="analyst-1",
            rationale="intake questionnaire states this directly",
            on=TODAY,
            correlation_id=CORRELATION,
            citations=frozenset({citation()}),
        )

        self.assertIs(ProvenanceClass.PROPOSED, original.provenance)
        self.assertFalse(original.revisions)
        self.assertIs(ProvenanceClass.KNOWN, promoted.provenance)
        self.assertTrue(promoted.is_directly_sourced)
        self.assertEqual(1, len(promoted.revisions))
        revision = promoted.revisions[0]
        self.assertEqual("analyst-1", revision.actor)
        self.assertIs(ProvenanceClass.PROPOSED, revision.old_provenance)
        self.assertIs(ProvenanceClass.KNOWN, revision.new_provenance)
        self.assertEqual(CORRELATION, revision.correlation_id)


if __name__ == "__main__":
    unittest.main()
