"""Behavioral tests for the stage 1 Avatar Locked rule (pure domain, Commercial).

Rules under test come from SPEC.md section 4, stage 1 "Diagnose" and its "Avatar
Locked" checkpoint: an avatar with demographics and psychographics, pains, goals,
consequences of inaction, awareness, customer evidence and voice notes, where "a
stranger can recognize who the customer is, what matters, and why now". The
product contract (SPEC.md section 1) also requires every output to have a source,
so customer evidence must be a known, directly sourced Knowledge claim of the
same client. An avatar that leaves any recognizability dimension unspecified, or
whose evidence is unsourced or belongs to another client, cannot be locked as
stage 1 gate evidence.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    AvatarLockedError,
    InvalidAvatarProfileError,
)
from redops.contexts.commercial.domain.policies import AvatarLockedPolicy
from redops.contexts.commercial.domain.value_objects import AvatarProfile
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.value_objects import (
    ProvenanceClass,
    SourceCitation,
)


def avatar(**overrides) -> AvatarProfile:
    values = {
        "avatar_id": "avatar-3f",
        "tenant_id": "client-3f",
        "name": "Owner-operator of a small service firm",
        "demographics": "35-50, runs a two to five person local service firm",
        "psychographics": "proud of craft, skeptical of marketing, time poor",
        "pains": ("feast and famine pipeline",),
        "goals": ("predictable qualified demand",),
        "consequences_of_inaction": ("hires then lays off as work dries up",),
        "awareness": "problem aware, not solution aware",
        "customer_evidence_claim_ids": ("claim-voice-1",),
        "voice_notes": ("I cannot plan payroll when the phone is quiet",),
    }
    values.update(overrides)
    return AvatarProfile(**values)


def sourced_claim(
    claim_id: str = "claim-voice-1",
    *,
    tenant_id: str = "client-3f",
    provenance: ProvenanceClass = ProvenanceClass.KNOWN,
    citations: frozenset[SourceCitation] | None = None,
) -> Claim:
    if citations is None:
        citations = (
            frozenset({SourceCitation("source-call", "sha256:abc", "00:14:03")})
            if provenance is ProvenanceClass.KNOWN
            else frozenset()
        )
    return Claim(
        claim_id=claim_id,
        tenant_id=tenant_id,
        statement="The phone goes quiet between projects",
        provenance=provenance,
        citations=citations,
        confidence_note="recorded from a discovery call",
    )


class AvatarProfileCheckpointTests(unittest.TestCase):
    def test_a_complete_avatar_records_who_what_matters_and_why_now(self):
        profile = avatar()

        self.assertEqual("Owner-operator of a small service firm", profile.name)
        self.assertEqual(
            "35-50, runs a two to five person local service firm",
            profile.demographics,
        )
        self.assertEqual("feast and famine pipeline", profile.pains[0])
        self.assertEqual("predictable qualified demand", profile.goals[0])
        self.assertEqual(
            "hires then lays off as work dries up",
            profile.consequences_of_inaction[0],
        )
        self.assertEqual("problem aware, not solution aware", profile.awareness)
        self.assertEqual(("claim-voice-1",), profile.customer_evidence_claim_ids)
        self.assertEqual(
            ("I cannot plan payroll when the phone is quiet",),
            profile.voice_notes,
        )

    def test_an_avatar_without_identity_or_person_is_rejected(self):
        for override in (
            {"avatar_id": ""},
            {"tenant_id": "   "},
            {"name": ""},
            {"demographics": ""},
            {"psychographics": "  "},
            {"awareness": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidAvatarProfileError):
                    avatar(**override)

    def test_an_avatar_missing_a_recognizability_dimension_is_rejected(self):
        for override in (
            {"pains": ()},
            {"goals": ()},
            {"consequences_of_inaction": ()},
            {"customer_evidence_claim_ids": ()},
            {"voice_notes": ()},
            {"pains": ("   ",)},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidAvatarProfileError):
                    avatar(**override)

    def test_a_locked_avatar_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            avatar().name = "tampered"


class AvatarLockedPolicyTests(unittest.TestCase):
    def test_a_locked_avatar_requires_sourced_same_tenant_evidence(self):
        AvatarLockedPolicy().require_locked(avatar(), (sourced_claim(),))

    def test_an_avatar_whose_evidence_is_unsourced_cannot_lock(self):
        for provenance in (
            ProvenanceClass.DERIVED,
            ProvenanceClass.PROPOSED,
            ProvenanceClass.UNKNOWN,
        ):
            with self.subTest(provenance=provenance):
                with self.assertRaises(AvatarLockedError):
                    AvatarLockedPolicy().require_locked(
                        avatar(), (sourced_claim(provenance=provenance),)
                    )

    def test_an_avatar_whose_evidence_belongs_to_another_client_cannot_lock(self):
        foreign = sourced_claim(tenant_id="client-other")

        with self.assertRaises(AvatarLockedError):
            AvatarLockedPolicy().require_locked(avatar(), (foreign,))

    def test_an_avatar_whose_evidence_claim_is_absent_cannot_lock(self):
        with self.assertRaises(AvatarLockedError):
            AvatarLockedPolicy().require_locked(
                avatar(), (sourced_claim("claim-other"),)
            )

    def test_an_avatar_locks_when_every_evidence_claim_is_sourced(self):
        profile = avatar(
            customer_evidence_claim_ids=("claim-voice-1", "claim-voice-2")
        )

        AvatarLockedPolicy().require_locked(
            profile,
            (sourced_claim("claim-voice-1"), sourced_claim("claim-voice-2")),
        )


if __name__ == "__main__":
    unittest.main()
