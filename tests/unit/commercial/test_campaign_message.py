"""Behavioral tests for the CampaignMessage aggregate (pure domain, Commercial).

Rules under test come from SPEC.md sections 3 and 4, stage 6 "Message":
- The required asset package is the promise, problem hierarchy, desired outcome,
  proof and objections, story, method explanation, CTA, lead magnet, hook,
  angles, landing message and Authority Amplifier outline.
- The "Campaign Message Approved" checkpoint requires that "avatar, currency,
  problem, promise, method, product and CTA agree".
- The message is grounded on the approved stage 5 offer ("Production requires
  approved dependencies", SPEC.md section 3), so a message that conflicts with
  the locked offer cannot be approved (Phase 4 TDD example: "campaign message
  conflicting with the offer blocks approval").
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    CampaignMessageAlignmentError,
    CampaignMessageDependencyError,
    InvalidCampaignMessageError,
)
from redops.contexts.commercial.domain.value_objects import (
    CampaignMessageState,
    MethodReference,
)
from redops.contexts.method.domain.value_objects import SemanticVersion

from .fixtures import (
    USE,
    approved_method,
    campaign_message,
    offer_version,
    production_ready_offer,
)


class CampaignMessageApprovalTests(unittest.TestCase):
    def test_a_congruent_message_grounded_on_the_approved_offer_is_approved(self):
        offer = production_ready_offer()

        approved = campaign_message(offer=offer).approve([approved_method()])

        self.assertIs(CampaignMessageState.APPROVED, approved.state)
        self.assertTrue(approved.is_approved)

    def test_a_message_cannot_be_approved_on_a_non_production_ready_offer(self):
        draft = offer_version()

        with self.assertRaises(CampaignMessageAlignmentError):
            campaign_message(offer=draft).approve([approved_method()])

    def test_a_promise_conflicting_with_the_offer_blocks_approval(self):
        with self.assertRaises(CampaignMessageAlignmentError):
            campaign_message(promise="triple your revenue").approve(
                [approved_method()]
            )

    def test_an_avatar_conflicting_with_the_offer_blocks_approval(self):
        with self.assertRaises(CampaignMessageAlignmentError):
            campaign_message(avatar="enterprise procurement teams").approve(
                [approved_method()]
            )

    def test_a_product_conflicting_with_the_offer_blocks_approval(self):
        with self.assertRaises(CampaignMessageAlignmentError):
            campaign_message(product_offer_id="some-other-offer").approve(
                [approved_method()]
            )

    def test_a_problem_not_in_the_approved_diagnosis_blocks_approval(self):
        with self.assertRaises(CampaignMessageAlignmentError):
            campaign_message(problem="a problem nobody diagnosed").approve(
                [approved_method()]
            )

    def test_a_method_conflicting_with_the_offer_blocks_approval(self):
        other = MethodReference(
            method_id="method-other",
            version=SemanticVersion(1, 0, 0),
            intended_use=USE,
        )

        with self.assertRaises(CampaignMessageAlignmentError):
            campaign_message(method_reference=other).approve([approved_method()])

    def test_a_currency_conflicting_with_the_approved_method_blocks_approval(self):
        with self.assertRaises(CampaignMessageAlignmentError):
            campaign_message(currency="inbound leads").approve([approved_method()])

    def test_a_message_cannot_be_approved_without_an_authorized_method(self):
        with self.assertRaises(CampaignMessageAlignmentError):
            campaign_message().approve([])

    def test_a_message_cannot_use_a_method_approved_for_a_different_version(self):
        with self.assertRaises(CampaignMessageAlignmentError):
            campaign_message(method_reference=offer_version().method_refs[0]).approve(
                [approved_method(version=SemanticVersion(9, 0, 0))]
            )

    def test_a_terminal_message_cannot_be_approved(self):
        message = campaign_message(state=CampaignMessageState.SUPERSEDED)

        with self.assertRaises(CampaignMessageAlignmentError):
            message.approve([approved_method()])

    def test_an_approved_message_is_immutable(self):
        approved = campaign_message().approve([approved_method()])

        with self.assertRaises(FrozenInstanceError):
            approved.promise = "tampered"

    def test_an_approved_message_can_be_marked_review_required_with_a_reason(self):
        approved = campaign_message().approve([approved_method()])

        marked = approved.mark_review_required(reason="offer advanced")

        self.assertIs(CampaignMessageState.REVIEW_REQUIRED, marked.state)
        self.assertTrue(marked.review_reason)

    def test_marking_review_required_needs_a_reason(self):
        with self.assertRaises(InvalidCampaignMessageError):
            campaign_message().mark_review_required(reason="  ")


class CampaignMessageInvariantTests(unittest.TestCase):
    def test_a_message_requires_its_identity_and_congruence_fields(self):
        for override in (
            {"message_id": "  "},
            {"owner": ""},
            {"avatar": ""},
            {"currency": ""},
            {"problem": ""},
            {"promise": ""},
            {"cta": ""},
            {"method_explanation": ""},
            {"landing_message": ""},
            {"authority_amplifier_outline": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidCampaignMessageError):
                    campaign_message(**override)

    def test_a_message_requires_a_problem_hierarchy_proof_and_angles(self):
        for override in (
            {"problem_hierarchy": ()},
            {"proof_objections": ()},
            {"angles": ()},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidCampaignMessageError):
                    campaign_message(**override)

    def test_a_message_cannot_pin_another_tenants_offer(self):
        with self.assertRaises(CampaignMessageDependencyError):
            campaign_message(tenant_id="client-other")


if __name__ == "__main__":
    unittest.main()
