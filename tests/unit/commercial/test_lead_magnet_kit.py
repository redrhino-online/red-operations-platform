"""Behavioral tests for the canon lead-magnet kit (Commercial domain).

Rules under test come from the canon's lead-magnet material and the
implementation plan's canon gap backlog item G1 (SPEC.md section 12.5 records the
lead-magnet kit as a canon gap; the backlog names a typed artifact that "reports
the solution step it is built from; refuses a lead magnet not grounded on a
same-tenant hot step"). The shape is extracted from:

- High Ticket Funnels 03, "The Ultimate Lead Magnet Clinic": the "Opt in method"
  five characteristics (one hot currency from the product roadmap, paired with
  the authority amplifier video, time friendly, solves one small problem,
  incomplete on purpose, one clear next step); the allowed formats (cheat sheet,
  template, checklist, script, roadmap) and the refused formats (ebook, webinar,
  mini course, strategy session, quiz, guide, white paper); the name must imply
  what it is; the seven-element PDF (title, proof, short bio, problem, the
  one-page cheat sheet, the steps, one clear action); the picture of the thing
  itself; the two-step opt in; delivery by email, not the thank-you page; and the
  ten-minute rule.
- High Ticket Funnels 04, Live Sessions 15 and 14D Step 7 deepen the same shape.
- Synthesized `ops/playbooks/lead-magnet.md` and
  `ops/checklists/lead-magnet-pdf.md` restate the gate: one step, one currency,
  paired with the authority video, one clear action, not an ebook/long course/quiz.

The kit is a stage 6/8 planning asset, not a new required gate kind. It does not
authorize publishing or spend (SPEC.md sections 4 and 9) and it is never an
observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    InvalidLeadMagnetKitError,
    LeadMagnetKitDependencyError,
    LeadMagnetKitFormatError,
    LeadMagnetKitObservationError,
    LeadMagnetKitTenantBoundaryError,
)
from redops.contexts.commercial.domain.value_objects import (
    LEAD_MAGNET_CANON_REFERENCE,
    LeadMagnetDelivery,
    LeadMagnetFormat,
    LeadMagnetKit,
    LeadMagnetPdfSection,
)
from redops.contexts.method.domain.entities import SignatureSolution

from .fixtures import TENANT
from ..method.fixtures import primary_currency, signature_solution


def lead_magnet_kit(**overrides) -> LeadMagnetKit:
    solution = overrides.pop("method", None) or signature_solution()
    currency = overrides.pop("currency", None) or primary_currency(TENANT)
    hot_step = overrides.pop("hot_step", None)
    if hot_step is None:
        hot_step = (
            solution.steps[0].name
            if isinstance(solution, SignatureSolution)
            else "Diagnose"
        )
    values = {
        "kit_id": "kit-3f",
        "tenant_id": TENANT,
        "owner": "red-delivery-lead",
        "method": solution,
        "currency": currency,
        "hot_step": hot_step,
        "name": "the one page referral cheat sheet",
        "format": LeadMagnetFormat.CHEAT_SHEET,
        "promise": "double qualified referrals without more ad spend",
        "timeline": "within 30 days",
        "pdf_sections": tuple(LeadMagnetPdfSection),
        "image_note": "a picture of the one page cheat sheet itself",
        "two_step_opt_in": True,
        "delivery": LeadMagnetDelivery.EMAIL,
        "minutes_to_use": 10,
        "next_action": "book the referral strategy call",
        "authority_video_ref": "asset://authority/3f-referral-video.mp4",
    }
    values.update(overrides)
    return LeadMagnetKit(**values)


class LeadMagnetKitTest(unittest.TestCase):
    def test_canon_reference_names_the_lead_magnet_sources(self) -> None:
        self.assertIn("High Ticket Funnels 03", LEAD_MAGNET_CANON_REFERENCE)
        self.assertIn("Live Sessions 15", LEAD_MAGNET_CANON_REFERENCE)

    def test_a_complete_kit_is_frozen_and_reports_its_hot_step(self) -> None:
        kit = lead_magnet_kit()
        self.assertEqual(kit.hot_step, "Diagnose")
        self.assertTrue(kit.is_plan)
        with self.assertRaises(FrozenInstanceError):
            kit.name = "changed"  # type: ignore[misc]

    def test_blank_identity_is_refused(self) -> None:
        for field in (
            "kit_id",
            "owner",
            "hot_step",
            "name",
            "promise",
            "timeline",
            "image_note",
            "next_action",
            "authority_video_ref",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidLeadMagnetKitError):
                    lead_magnet_kit(**{field: "  "})

    def test_kit_must_be_grounded_on_a_typed_signature_solution(self) -> None:
        with self.assertRaises(LeadMagnetKitDependencyError):
            lead_magnet_kit(method="not-a-solution")

    def test_kit_must_be_grounded_on_a_typed_primary_currency(self) -> None:
        with self.assertRaises(LeadMagnetKitDependencyError):
            lead_magnet_kit(currency="not-a-currency")

    def test_kit_refuses_a_cross_tenant_method_or_currency(self) -> None:
        foreign = signature_solution("client-other")
        with self.assertRaises(LeadMagnetKitTenantBoundaryError):
            lead_magnet_kit(method=foreign)
        with self.assertRaises(LeadMagnetKitTenantBoundaryError):
            lead_magnet_kit(currency=primary_currency("client-other"))

    def test_hot_step_must_be_a_step_the_solution_names(self) -> None:
        with self.assertRaises(LeadMagnetKitDependencyError):
            lead_magnet_kit(hot_step="Invent a new step")

    def test_format_must_be_a_typed_canon_format(self) -> None:
        with self.assertRaises(InvalidLeadMagnetKitError):
            lead_magnet_kit(format="ebook")

    def test_name_must_imply_the_chosen_format(self) -> None:
        with self.assertRaises(LeadMagnetKitFormatError):
            lead_magnet_kit(name="the ultimate sales hack")

    def test_pdf_requires_every_canon_section_exactly_once(self) -> None:
        with self.assertRaises(InvalidLeadMagnetKitError):
            lead_magnet_kit(pdf_sections=(LeadMagnetPdfSection.TITLE,))
        with self.assertRaises(InvalidLeadMagnetKitError):
            lead_magnet_kit(
                pdf_sections=tuple(LeadMagnetPdfSection)
                + (LeadMagnetPdfSection.TITLE,)
            )

    def test_two_step_opt_in_is_required(self) -> None:
        with self.assertRaises(LeadMagnetKitFormatError):
            lead_magnet_kit(two_step_opt_in=False)

    def test_delivery_must_be_email_not_a_thank_you_page(self) -> None:
        with self.assertRaises(InvalidLeadMagnetKitError):
            lead_magnet_kit(delivery="thank_you_page")
        with self.assertRaises(LeadMagnetKitFormatError):
            lead_magnet_kit(delivery=LeadMagnetDelivery.THANK_YOU_PAGE)

    def test_kit_must_fit_the_ten_minute_rule(self) -> None:
        with self.assertRaises(LeadMagnetKitFormatError):
            lead_magnet_kit(minutes_to_use=11)
        with self.assertRaises(LeadMagnetKitFormatError):
            lead_magnet_kit(minutes_to_use=0)

    def test_kit_is_never_an_observation(self) -> None:
        with self.assertRaises(LeadMagnetKitObservationError):
            lead_magnet_kit().as_observation(claim_id="claim-1")


if __name__ == "__main__":
    unittest.main()
