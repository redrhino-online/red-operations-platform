"""Behavioral tests for the AuthorityAmplifier aggregate (Production domain).

Rules under test come from SPEC.md sections 3 and 4, stage 7 "Produce":
- The required asset package is the approved Authority Amplifier script in
  Promise, Proof, Problems, Steps, Context, Action order, plus the storyboard,
  brand treatment, presentation, speaker notes, recording, edited and hosted
  video and player assets.
- Stage 7 has two distinct approvals: the script and its supported claims pass
  review before any visual or video production, and final creative acceptance is
  separate. Phase 4 TDD examples: "visual Authority Amplifier production cannot
  be authorized by an unapproved script" and "unsupported proof is flagged".
- The final asset gives a credible next action and the stage is grounded on the
  approved stage 6 message (SPEC.md section 3: production requires approved
  dependencies).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.value_objects import ProvenanceClass
from redops.contexts.production.domain.errors import (
    AuthorityAmplifierApprovalOrderError,
    AuthorityAmplifierDependencyError,
    InvalidAuthorityAmplifierError,
    UnsupportedProofError,
)
from redops.contexts.production.domain.value_objects import (
    AuthorityAmplifierState,
    ScriptSection,
    ScriptSectionKind,
)

from .fixtures import (
    TODAY,
    USE,
    authority_amplifier,
    known_claim,
    script,
    script_approved_amplifier,
    visual_package,
)
from ..commercial.fixtures import approved_method, campaign_message, production_ready_offer


def approve_script(amplifier, **overrides):
    values = {
        "approved_by": "production-manager",
        "intended_use": USE,
        "on": TODAY,
        "approved_methods": (approved_method(),),
        "claims": (known_claim(),),
    }
    values.update(overrides)
    return amplifier.approve_script(**values)


class AuthorityAmplifierScriptApprovalTests(unittest.TestCase):
    def test_a_grounded_amplifier_can_approve_its_script(self):
        amplifier = authority_amplifier()

        approved = approve_script(amplifier)

        self.assertIs(AuthorityAmplifierState.SCRIPT_APPROVED, approved.state)
        self.assertTrue(approved.is_script_approved)
        self.assertFalse(approved.is_approved)

    def test_a_script_cannot_be_approved_on_an_unapproved_message(self):
        draft = campaign_message(offer=production_ready_offer())

        with self.assertRaises(AuthorityAmplifierDependencyError):
            approve_script(authority_amplifier(message=draft))

    def test_a_script_cannot_be_approved_without_an_authorized_method(self):
        with self.assertRaises(AuthorityAmplifierDependencyError):
            approve_script(authority_amplifier(), approved_methods=())

    def test_proof_outside_the_approved_method_is_flagged(self):
        amplifier = authority_amplifier(proof_claim_ids=frozenset({"claim-made-up"}))

        with self.assertRaises(UnsupportedProofError):
            approve_script(amplifier)

    def test_proof_without_a_known_directly_sourced_claim_is_flagged(self):
        derived = Claim(
            claim_id="claim-1",
            tenant_id="client-3f",
            statement="an unverified statement",
            provenance=ProvenanceClass.DERIVED,
            confidence_note="interpretation only",
        )

        with self.assertRaises(UnsupportedProofError):
            approve_script(authority_amplifier(), claims=(derived,))

    def test_a_terminal_amplifier_cannot_approve_its_script(self):
        amplifier = authority_amplifier(state=AuthorityAmplifierState.SUPERSEDED)

        with self.assertRaises(AuthorityAmplifierDependencyError):
            approve_script(amplifier)


class AuthorityAmplifierCreativeApprovalTests(unittest.TestCase):
    def test_visual_production_cannot_be_authorized_by_an_unapproved_script(self):
        with self.assertRaises(AuthorityAmplifierApprovalOrderError):
            authority_amplifier().produce_visuals(package=visual_package())

    def test_creative_approval_cannot_precede_script_approval(self):
        with self.assertRaises(AuthorityAmplifierApprovalOrderError):
            authority_amplifier().approve_creative(
                approved_by="client-authority",
                intended_use=USE,
                on=TODAY,
            )

    def test_creative_approval_requires_the_complete_visual_package(self):
        amplifier = script_approved_amplifier()

        with self.assertRaises(AuthorityAmplifierDependencyError):
            amplifier.approve_creative(
                approved_by="client-authority",
                intended_use=USE,
                on=TODAY,
            )

    def test_a_produced_and_scripted_amplifier_can_receive_final_acceptance(self):
        amplifier = script_approved_amplifier().produce_visuals(
            package=visual_package()
        )

        approved = amplifier.approve_creative(
            approved_by="client-authority",
            intended_use=USE,
            on=TODAY,
        )

        self.assertIs(AuthorityAmplifierState.APPROVED, approved.state)
        self.assertTrue(approved.is_approved)
        self.assertTrue(approved.is_script_approved)

    def test_an_approved_amplifier_is_immutable(self):
        approved = script_approved_amplifier().produce_visuals(
            package=visual_package()
        ).approve_creative(
            approved_by="client-authority", intended_use=USE, on=TODAY
        )

        with self.assertRaises(FrozenInstanceError):
            approved.owner = "tampered"

    def test_an_approved_amplifier_can_be_marked_review_required(self):
        amplifier = script_approved_amplifier().produce_visuals(
            package=visual_package()
        )
        approved = amplifier.approve_creative(
            approved_by="client-authority", intended_use=USE, on=TODAY
        )

        marked = approved.mark_review_required(reason="message changed")

        self.assertIs(AuthorityAmplifierState.REVIEW_REQUIRED, marked.state)
        self.assertTrue(marked.review_reason)

    def test_marking_review_required_needs_a_reason(self):
        with self.assertRaises(InvalidAuthorityAmplifierError):
            authority_amplifier().mark_review_required(reason="  ")


class AuthorityAmplifierInvariantTests(unittest.TestCase):
    def test_the_script_must_follow_the_canonical_section_order(self):
        wrong = tuple(
            ScriptSection(kind, "content")
            for kind in (
                ScriptSectionKind.PROOF,
                ScriptSectionKind.PROMISE,
                ScriptSectionKind.PROBLEMS,
                ScriptSectionKind.STEPS,
                ScriptSectionKind.CONTEXT,
                ScriptSectionKind.ACTION,
            )
        )

        with self.assertRaises(InvalidAuthorityAmplifierError):
            authority_amplifier(script=wrong)

    def test_the_script_must_contain_every_section(self):
        with self.assertRaises(InvalidAuthorityAmplifierError):
            authority_amplifier(script=script()[:5])

    def test_a_blank_script_section_is_rejected(self):
        with self.assertRaises(InvalidAuthorityAmplifierError):
            authority_amplifier(
                script=script({ScriptSectionKind.PROMISE: "  "})
            )

    def test_an_amplifier_requires_its_identity_owner_and_proof(self):
        for override in (
            {"amplifier_id": "  "},
            {"owner": ""},
            {"proof_claim_ids": frozenset()},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidAuthorityAmplifierError):
                    authority_amplifier(**override)

    def test_an_amplifier_cannot_be_grounded_on_another_tenants_message(self):
        with self.assertRaises(AuthorityAmplifierDependencyError):
            authority_amplifier(tenant_id="client-other")

    def test_a_visual_package_requires_every_artifact(self):
        with self.assertRaises(InvalidAuthorityAmplifierError):
            visual_package(recording="  ")


if __name__ == "__main__":
    unittest.main()
