"""Behavioral tests for the SourceRecord aggregate (pure domain, Knowledge).

Rules under test come from SPEC.md sections 3 and 11:
- SourceRecord records an original bytes reference (locator), a checksum, a
  capture time and an access rule (SPEC.md section 3 aggregate table).
- The original is immutable and retrievable to authorized users.
- A citation is checksum and location based and opens the exact source
  location (SPEC.md section 2 fork matrix, section 11 acceptance tests).
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.knowledge.domain.entities import SourceRecord
from redops.contexts.knowledge.domain.errors import InvalidSourceRecordError

TODAY = date(2026, 10, 2)
CHECKSUM = "sha256:8f14e45fceea167a5a36dedd4bea2543"


def source_record(**overrides) -> SourceRecord:
    values = {
        "source_id": "source-1",
        "tenant_id": "client-3f",
        "locator": "s3://redops-private/client-3f/intake/questionnaire.pdf",
        "checksum": CHECKSUM,
        "captured_on": TODAY,
        "access_rule": "client-3f-members",
    }
    values.update(overrides)
    return SourceRecord(**values)


class SourceRecordInvariantTests(unittest.TestCase):
    def test_source_record_keeps_original_reference_and_metadata(self):
        source = source_record()

        self.assertEqual("source-1", source.source_id)
        self.assertEqual("client-3f", source.tenant_id)
        self.assertEqual(CHECKSUM, source.checksum)
        self.assertEqual(
            "s3://redops-private/client-3f/intake/questionnaire.pdf",
            source.locator,
        )
        self.assertEqual(TODAY, source.captured_on)
        self.assertEqual("client-3f-members", source.access_rule)

    def test_a_source_without_an_original_locator_is_rejected(self):
        with self.assertRaises(InvalidSourceRecordError):
            source_record(locator="")

    def test_a_source_without_a_checksum_is_rejected(self):
        with self.assertRaises(InvalidSourceRecordError):
            source_record(checksum="   ")

    def test_a_source_without_a_capture_time_is_rejected(self):
        with self.assertRaises(InvalidSourceRecordError):
            source_record(captured_on=None)

    def test_a_source_without_an_access_rule_is_rejected(self):
        with self.assertRaises(InvalidSourceRecordError):
            source_record(access_rule="")

    def test_the_original_record_cannot_be_mutated(self):
        source = source_record()

        with self.assertRaises(FrozenInstanceError):
            source.checksum = "sha256:tampered"


class SourceCitationTests(unittest.TestCase):
    def test_citation_pins_the_source_checksum_and_exact_location(self):
        source = source_record()

        citation = source.cite("page 4, paragraph 2")

        self.assertEqual("source-1", citation.source_id)
        self.assertEqual(CHECKSUM, citation.checksum)
        self.assertEqual("page 4, paragraph 2", citation.location)

    def test_citation_requires_a_location(self):
        with self.assertRaises(InvalidSourceRecordError):
            source_record().cite("  ")


if __name__ == "__main__":
    unittest.main()
