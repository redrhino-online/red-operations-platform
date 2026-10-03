"""Cross-tenant isolation for the Knowledge retrieval layer.

SPEC.md section 13 condition 3 requires the cross-tenant security suite to cover
the retrieval layer, and SPEC.md section 11 requires "a different client's
retrieval produces no result". These tests exercise the Knowledge
``KnowledgeRetriever`` port through its tenant-scoped reference adapter: a query
is always answered against exactly one client's knowledge, so another client's
material is invisible even when the query matches it exactly.

The durable PostgreSQL full-text adapter implements the same port and is
exercised with ``DATABASE_URL`` wherever a psycopg driver is available (see
``tests/unit/knowledge/test_source_record_store.py``).
"""

from __future__ import annotations

import unittest
from datetime import date

from redops.contexts.knowledge.domain.entities import Claim, SourceRecord
from redops.contexts.knowledge.domain.errors import UnscopedRetrievalError
from redops.contexts.knowledge.domain.value_objects import ProvenanceClass
from redops.contexts.knowledge.infrastructure.repositories import (
    InMemoryClaimStore,
    InMemoryKnowledgeRetriever,
    InMemorySourceRecordStore,
)

TENANT = "3fmindset"
OTHER_TENANT = "client-other"
ON = date(2026, 10, 3)


def source(source_id: str, tenant_id: str) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        tenant_id=tenant_id,
        locator=f"s3://redops-private/{tenant_id}/intake.pdf",
        checksum=f"sha256:{source_id}",
        captured_on=ON,
        access_rule=f"{tenant_id}-members",
    )


def claim(
    claim_id: str,
    tenant_id: str,
    statement: str,
    citations: frozenset = frozenset(),
) -> Claim:
    return Claim(
        claim_id=claim_id,
        tenant_id=tenant_id,
        statement=statement,
        provenance=ProvenanceClass.PROPOSED,
        citations=citations,
        confidence_note="seeded for retrieval isolation",
    )


class RetrievalIsolationTests(unittest.TestCase):
    def setUp(self):
        self.sources = InMemorySourceRecordStore()
        self.claims = InMemoryClaimStore()
        self.retriever = InMemoryKnowledgeRetriever(self.claims)
        self.original = source("src-3f", TENANT)
        self.sources.save(self.original)
        self.citation = self.original.cite("page 4, paragraph 2")
        self.claims.save(
            claim(
                "claim-3f",
                TENANT,
                "The 3F audience struggles to convert referrals into clients",
                frozenset({self.citation}),
            )
        )
        self.claims.save(
            claim(
                "claim-other",
                OTHER_TENANT,
                "The 3F audience struggles to convert referrals into clients",
            )
        )

    def test_a_client_retrieves_its_own_claims_with_source_attribution(self):
        hits = self.retriever.retrieve(TENANT, "referrals")

        self.assertEqual(("claim-3f",), tuple(hit.claim_id for hit in hits))
        self.assertEqual(frozenset({self.citation}), hits[0].citations)

    def test_another_clients_matching_claim_is_never_returned(self):
        hits = self.retriever.retrieve(TENANT, "referrals")

        self.assertEqual(("claim-3f",), tuple(hit.claim_id for hit in hits))

    def test_another_clients_matching_query_produces_no_result(self):
        self.claims.save(
            claim(
                "claim-other-unique",
                OTHER_TENANT,
                "A phrase only the other client's archive carries",
            )
        )

        self.assertEqual((), self.retriever.retrieve(TENANT, "phrase client archive"))

    def test_retrieval_is_scoped_to_the_requested_client(self):
        other_hits = self.retriever.retrieve(OTHER_TENANT, "referrals")

        self.assertEqual(
            ("claim-other",), tuple(hit.claim_id for hit in other_hits)
        )

    def test_a_blank_tenant_is_refused(self):
        with self.assertRaises(UnscopedRetrievalError):
            self.retriever.retrieve("   ", "referrals")

    def test_an_empty_query_returns_no_claims(self):
        self.assertEqual((), self.retriever.retrieve(TENANT, "   "))


if __name__ == "__main__":
    unittest.main()
