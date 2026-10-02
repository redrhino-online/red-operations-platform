"""Behavioral tests for the stage 1 diagnosis assets (pure domain, Commercial).

Rules under test come from SPEC.md section 4, stage 1 "Diagnose": the required
asset package names the business snapshot and the offer and funnel audit in
addition to the avatar. The stage 1 checkpoint stays "Avatar Locked", but these
two assets are the diagnosis inputs the checkpoint depends on, so an asset that
leaves the current business state or the current offer and funnel unspecified
cannot be represented as a diagnosable asset. SPEC.md section 1 requires every
output to have a source, so each asset records the Knowledge claim ids that
evidence it and those claims must be known, directly sourced and belong to the
same client.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    InvalidBusinessSnapshotError,
    InvalidOfferFunnelAuditError,
    UnsourcedDiagnosisEvidenceError,
)
from redops.contexts.commercial.domain.policies import DiagnosisEvidencePolicy
from redops.contexts.commercial.domain.value_objects import (
    BusinessSnapshot,
    OfferFunnelAudit,
)
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.value_objects import (
    ProvenanceClass,
    SourceCitation,
)


def snapshot(**overrides) -> BusinessSnapshot:
    values = {
        "snapshot_id": "snapshot-3f",
        "tenant_id": "client-3f",
        "business_model": "project based service work billed hourly",
        "current_offers": ("hourly support retainer",),
        "lead_sources": ("referrals", "responds to inbound calls"),
        "constraints": ("two delivery people, no marketing owner",),
        "narrative": "Steady referrals but no predictable pipeline between projects",
        "evidence_claim_ids": ("claim-offer-1",),
    }
    values.update(overrides)
    return BusinessSnapshot(**values)


def audit(**overrides) -> OfferFunnelAudit:
    values = {
        "audit_id": "audit-3f",
        "tenant_id": "client-3f",
        "offer_findings": ("the retainer has no stated outcome",),
        "funnel_steps": ("referral", "call", "quote", "project"),
        "conversion_evidence": ("quotes are tracked in a spreadsheet",),
        "gaps": ("no qualification step before the call",),
        "narrative": "The funnel has no owner between referral and quote",
        "evidence_claim_ids": ("claim-offer-1",),
    }
    values.update(overrides)
    return OfferFunnelAudit(**values)


def sourced_claim(
    claim_id: str = "claim-offer-1",
    *,
    tenant_id: str = "client-3f",
    provenance: ProvenanceClass = ProvenanceClass.KNOWN,
    citations: frozenset[SourceCitation] | None = None,
) -> Claim:
    if citations is None:
        citations = (
            frozenset({SourceCitation("source-audit", "sha256:def", "p.2")})
            if provenance is ProvenanceClass.KNOWN
            else frozenset()
        )
    return Claim(
        claim_id=claim_id,
        tenant_id=tenant_id,
        statement="The retainer has no stated outcome",
        provenance=provenance,
        citations=citations,
        confidence_note="recorded during diagnosis",
    )


class BusinessSnapshotTests(unittest.TestCase):
    def test_a_complete_snapshot_records_the_current_business_state(self):
        profile = snapshot()

        self.assertEqual("project based service work billed hourly", profile.business_model)
        self.assertEqual(("hourly support retainer",), profile.current_offers)
        self.assertEqual(("referrals", "responds to inbound calls"), profile.lead_sources)
        self.assertEqual(
            ("two delivery people, no marketing owner",), profile.constraints
        )
        self.assertEqual(
            "Steady referrals but no predictable pipeline between projects",
            profile.narrative,
        )
        self.assertEqual(("claim-offer-1",), profile.evidence_claim_ids)

    def test_a_snapshot_without_identity_or_current_state_is_rejected(self):
        for override in (
            {"snapshot_id": ""},
            {"tenant_id": "   "},
            {"business_model": ""},
            {"narrative": "  "},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidBusinessSnapshotError):
                    snapshot(**override)

    def test_a_snapshot_missing_a_current_state_dimension_is_rejected(self):
        for override in (
            {"current_offers": ()},
            {"lead_sources": ()},
            {"constraints": ()},
            {"evidence_claim_ids": ()},
            {"lead_sources": ("   ",)},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidBusinessSnapshotError):
                    snapshot(**override)

    def test_a_snapshot_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            snapshot().narrative = "tampered"


class OfferFunnelAuditTests(unittest.TestCase):
    def test_a_complete_audit_records_the_current_offer_and_funnel(self):
        profile = audit()

        self.assertEqual(("the retainer has no stated outcome",), profile.offer_findings)
        self.assertEqual(("referral", "call", "quote", "project"), profile.funnel_steps)
        self.assertEqual(
            ("quotes are tracked in a spreadsheet",), profile.conversion_evidence
        )
        self.assertEqual(("no qualification step before the call",), profile.gaps)
        self.assertEqual(
            "The funnel has no owner between referral and quote", profile.narrative
        )
        self.assertEqual(("claim-offer-1",), profile.evidence_claim_ids)

    def test_an_audit_without_identity_or_narrative_is_rejected(self):
        for override in (
            {"audit_id": ""},
            {"tenant_id": "   "},
            {"narrative": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidOfferFunnelAuditError):
                    audit(**override)

    def test_an_audit_missing_an_audit_dimension_is_rejected(self):
        for override in (
            {"offer_findings": ()},
            {"funnel_steps": ()},
            {"conversion_evidence": ()},
            {"gaps": ()},
            {"evidence_claim_ids": ()},
            {"gaps": ("   ",)},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidOfferFunnelAuditError):
                    audit(**override)

    def test_an_audit_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            audit().narrative = "tampered"


class DiagnosisEvidencePolicyTests(unittest.TestCase):
    def test_a_snapshot_is_sourced_by_known_same_tenant_claims(self):
        DiagnosisEvidencePolicy().require_business_snapshot_sourced(
            snapshot(), (sourced_claim(),)
        )

    def test_an_unsourced_snapshot_cannot_be_represented_as_evidenced(self):
        with self.assertRaises(UnsourcedDiagnosisEvidenceError):
            DiagnosisEvidencePolicy().require_business_snapshot_sourced(
                snapshot(), (sourced_claim(provenance=ProvenanceClass.DERIVED),)
            )

    def test_a_snapshot_evidenced_by_another_client_cannot_be_used(self):
        with self.assertRaises(UnsourcedDiagnosisEvidenceError):
            DiagnosisEvidencePolicy().require_business_snapshot_sourced(
                snapshot(), (sourced_claim(tenant_id="client-other"),)
            )

    def test_an_audit_is_sourced_by_known_same_tenant_claims(self):
        DiagnosisEvidencePolicy().require_offer_funnel_audit_sourced(
            audit(), (sourced_claim(),)
        )

    def test_an_unsourced_audit_cannot_be_represented_as_evidenced(self):
        with self.assertRaises(UnsourcedDiagnosisEvidenceError):
            DiagnosisEvidencePolicy().require_offer_funnel_audit_sourced(
                audit(), (sourced_claim(provenance=ProvenanceClass.PROPOSED),)
            )

    def test_an_audit_evidenced_by_another_client_cannot_be_used(self):
        with self.assertRaises(UnsourcedDiagnosisEvidenceError):
            DiagnosisEvidencePolicy().require_offer_funnel_audit_sourced(
                audit(), (sourced_claim(tenant_id="client-other"),)
            )

    def test_an_audit_whose_evidence_claim_is_absent_cannot_be_used(self):
        with self.assertRaises(UnsourcedDiagnosisEvidenceError):
            DiagnosisEvidencePolicy().require_offer_funnel_audit_sourced(
                audit(), (sourced_claim("claim-other"),)
            )


if __name__ == "__main__":
    unittest.main()
