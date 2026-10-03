"""Behavioral tests for the canon's invisible opt-in offer (Measurement domain).

Rules under test come from SPEC.md section 12.5 (the retargeting-system canon
gap) and SPEC.md section 4, stages 8 and 10 ("Funnel Complete" and "Performance
Baseline Established"), shaped by the canon's retargeting training (canon file
34). The canon describes an "invisible opt in offer": a prospect who reaches the
lead-magnet landing page but does not opt in is retargeted and given the lead
magnet "without requiring an opt in", and is pushed "all the way down the funnel
without ever needing an email address" (canon file 34). The offer therefore names
the non-converted visitor segment it recovers, the contact-free lead magnet it
delivers, the typed channel it runs on and the existing same-tenant retargeting
audience it advances, binds a named owner, refuses a contact-gated delivery, a
cross-tenant segment and an offer that does not move the prospect down the
funnel, and is never an observed result (SPEC.md section 3 keeps observations
distinct from conclusions).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.measurement.domain.errors import (
    InvalidInvisibleOptInError,
    InvisibleOptInContactGateError,
    InvisibleOptInDependencyError,
    InvisibleOptInObservationError,
    InvisibleOptInStepError,
    InvisibleOptInTenantBoundaryError,
)
from redops.contexts.measurement.domain.value_objects import (
    ConversionGoal,
    InvisibleOptInOffer,
    LeadMagnetAsset,
    MeasurementBasis,
    NonConvertedSegment,
    RetargetingAudience,
    RetargetingChannel,
    TrackingCode,
)

TENANT = "client-3f"


def tracking_code(**overrides) -> TrackingCode:
    values = {
        "code_id": "pixel-3f",
        "tenant_id": TENANT,
        "provider": "perfect-audience",
        "pages": ("/opt-in", "/authority-amplifier", "/booking"),
    }
    values.update(overrides)
    return TrackingCode(**values)


def conversion_goal(**overrides) -> ConversionGoal:
    values = {
        "goal_id": "goal-lead",
        "tenant_id": TENANT,
        "name": "lead magnet opt in",
        "url": "/thank-you",
        "value": 10.0,
        "basis": MeasurementBasis.OBSERVED,
        "tracking_code": tracking_code(),
        "funnel_step": "opt-in",
    }
    values.update(overrides)
    return ConversionGoal(**values)


def lead_magnet(**overrides) -> LeadMagnetAsset:
    values = {
        "asset_id": "magnet-cheat-sheet",
        "tenant_id": TENANT,
        "name": "authority cheat sheet",
        "delivery_locator": "https://cdn.example/cheat-sheet.pdf",
        "requires_contact_information": False,
    }
    values.update(overrides)
    return LeadMagnetAsset(**values)


def non_converted_segment(**overrides) -> NonConvertedSegment:
    values = {
        "segment_id": "segment-opt-in-drop",
        "tenant_id": TENANT,
        "name": "reached opt in but did not convert",
        "landing_step": "opt-in",
        "landing_page": "/opt-in",
        "unachieved_goal": conversion_goal(),
        "tracking_code": tracking_code(),
    }
    values.update(overrides)
    return NonConvertedSegment(**values)


def next_audience(**overrides) -> RetargetingAudience:
    values = {
        "audience_id": "list-authority-amplifier",
        "tenant_id": TENANT,
        "name": "watched the authority amplifier",
        "funnel_step": "authority-amplifier",
        "achieved_goal": conversion_goal(
            goal_id="goal-watch",
            name="authority amplifier watched",
            url="/watched",
            funnel_step="authority-amplifier",
        ),
        "lookback_days": 30,
        "tracking_code": tracking_code(),
    }
    values.update(overrides)
    return RetargetingAudience(**values)


def invisible_opt_in(**overrides) -> InvisibleOptInOffer:
    values = {
        "offer_id": "offer-invisible-opt-in",
        "tenant_id": TENANT,
        "owner": "campaign-operator",
        "name": "give the cheat sheet without an opt in",
        "segment": non_converted_segment(),
        "lead_magnet": lead_magnet(),
        "channel": RetargetingChannel.GOOGLE_DISPLAY,
        "advances": next_audience(),
    }
    values.update(overrides)
    return InvisibleOptInOffer(**values)


class LeadMagnetAssetTests(unittest.TestCase):
    def test_a_lead_magnet_names_its_delivery_without_contact(self):
        magnet = lead_magnet()

        self.assertEqual("authority cheat sheet", magnet.name)
        self.assertEqual(
            "https://cdn.example/cheat-sheet.pdf", magnet.delivery_locator
        )
        self.assertFalse(magnet.requires_contact_information)

    def test_a_lead_magnet_requires_its_identification_fields(self):
        for field in ("asset_id", "tenant_id", "name", "delivery_locator"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidInvisibleOptInError):
                    lead_magnet(**{field: "  "})

    def test_a_lead_magnet_gate_flag_must_be_a_bool(self):
        with self.assertRaises(InvalidInvisibleOptInError):
            lead_magnet(requires_contact_information="yes")

    def test_a_lead_magnet_is_immutable(self):
        magnet = lead_magnet()

        with self.assertRaises(FrozenInstanceError):
            magnet.requires_contact_information = True


class NonConvertedSegmentTests(unittest.TestCase):
    def test_a_segment_names_the_landing_page_and_unachieved_goal(self):
        segment = non_converted_segment()

        self.assertEqual("opt-in", segment.landing_step)
        self.assertEqual("/opt-in", segment.landing_page)
        self.assertEqual("lead magnet opt in", segment.unachieved_goal.name)

    def test_a_segment_requires_its_identification_fields(self):
        for field in (
            "segment_id",
            "tenant_id",
            "name",
            "landing_step",
            "landing_page",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidInvisibleOptInError):
                    non_converted_segment(**{field: "  "})

    def test_a_segment_needs_a_typed_unachieved_goal(self):
        with self.assertRaises(InvisibleOptInDependencyError):
            non_converted_segment(unachieved_goal="lead magnet opt in")

    def test_a_segment_needs_a_tracking_code(self):
        with self.assertRaises(InvisibleOptInDependencyError):
            non_converted_segment(tracking_code="pixel-3f")

    def test_a_segment_refuses_a_goal_from_another_tracking_code(self):
        with self.assertRaises(InvisibleOptInDependencyError):
            non_converted_segment(
                unachieved_goal=conversion_goal(
                    tracking_code=tracking_code(code_id="pixel-other")
                )
            )

    def test_a_segment_binds_its_goal_to_the_step_it_stalled_on(self):
        segment = non_converted_segment()

        self.assertEqual(segment.landing_step, segment.unachieved_goal.funnel_step)

    def test_a_segment_refuses_a_goal_recorded_at_another_step(self):
        with self.assertRaises(InvisibleOptInStepError):
            non_converted_segment(
                landing_step="authority-amplifier",
                unachieved_goal=conversion_goal(funnel_step="opt-in"),
            )

    def test_a_segment_cannot_cross_a_tenant_boundary(self):
        with self.assertRaises(InvisibleOptInTenantBoundaryError):
            non_converted_segment(
                tracking_code=tracking_code(tenant_id="other-client"),
                unachieved_goal=conversion_goal(
                    tenant_id="other-client",
                    tracking_code=tracking_code(tenant_id="other-client"),
                ),
            )

    def test_a_segment_is_immutable(self):
        segment = non_converted_segment()

        with self.assertRaises(FrozenInstanceError):
            segment.landing_step = "elsewhere"


class InvisibleOptInOfferTests(unittest.TestCase):
    def test_an_offer_recovers_a_segment_with_a_contact_free_magnet(self):
        offer = invisible_opt_in()

        self.assertEqual(
            "reached opt in but did not convert", offer.segment.name
        )
        self.assertTrue(offer.delivers_without_contact)
        self.assertIs(RetargetingChannel.GOOGLE_DISPLAY, offer.channel)

    def test_an_offer_advances_the_prospect_to_a_later_funnel_step(self):
        offer = invisible_opt_in()

        self.assertEqual("opt-in", offer.segment.landing_step)
        self.assertEqual("authority-amplifier", offer.advances.funnel_step)
        self.assertNotEqual(
            offer.segment.landing_step, offer.advances.funnel_step
        )

    def test_an_offer_requires_its_identity_and_owner(self):
        for field in ("offer_id", "tenant_id", "owner", "name"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidInvisibleOptInError):
                    invisible_opt_in(**{field: "  "})

    def test_an_offer_requires_a_typed_segment(self):
        with self.assertRaises(InvisibleOptInDependencyError):
            invisible_opt_in(segment="reached opt in")

    def test_an_offer_requires_a_typed_lead_magnet(self):
        with self.assertRaises(InvisibleOptInDependencyError):
            invisible_opt_in(lead_magnet="authority cheat sheet")

    def test_an_offer_requires_a_named_channel(self):
        with self.assertRaises(InvalidInvisibleOptInError):
            invisible_opt_in(channel="google")

    def test_an_offer_requires_a_typed_retargeting_audience(self):
        with self.assertRaises(InvisibleOptInDependencyError):
            invisible_opt_in(advances="list-authority-amplifier")

    def test_an_offer_refuses_a_contact_gated_lead_magnet(self):
        with self.assertRaises(InvisibleOptInContactGateError):
            invisible_opt_in(
                lead_magnet=lead_magnet(requires_contact_information=True)
            )

    def test_an_offer_refuses_a_cross_tenant_segment(self):
        with self.assertRaises(InvisibleOptInTenantBoundaryError):
            invisible_opt_in(
                segment=non_converted_segment(
                    tenant_id="other-client",
                    tracking_code=tracking_code(tenant_id="other-client"),
                    unachieved_goal=conversion_goal(
                        tenant_id="other-client",
                        tracking_code=tracking_code(tenant_id="other-client"),
                    ),
                )
            )

    def test_an_offer_refuses_a_cross_tenant_lead_magnet(self):
        with self.assertRaises(InvisibleOptInTenantBoundaryError):
            invisible_opt_in(
                lead_magnet=lead_magnet(tenant_id="other-client")
            )

    def test_an_offer_refuses_a_cross_tenant_audience(self):
        with self.assertRaises(InvisibleOptInTenantBoundaryError):
            invisible_opt_in(
                advances=next_audience(
                    tenant_id="other-client",
                    tracking_code=tracking_code(tenant_id="other-client"),
                    achieved_goal=conversion_goal(
                        tenant_id="other-client",
                        tracking_code=tracking_code(tenant_id="other-client"),
                        funnel_step="authority-amplifier",
                    ),
                )
            )

    def test_an_offer_requires_the_audience_on_the_segment_tracking_code(self):
        with self.assertRaises(InvisibleOptInDependencyError):
            invisible_opt_in(
                advances=next_audience(
                    tracking_code=tracking_code(code_id="pixel-other"),
                    achieved_goal=conversion_goal(
                        tracking_code=tracking_code(code_id="pixel-other"),
                        funnel_step="authority-amplifier",
                    ),
                )
            )

    def test_an_offer_must_move_the_prospect_past_the_stalled_step(self):
        with self.assertRaises(InvisibleOptInStepError):
            invisible_opt_in(
                advances=next_audience(
                    funnel_step="opt-in",
                    achieved_goal=conversion_goal(),
                )
            )

    def test_an_offer_is_never_an_observed_result(self):
        offer = invisible_opt_in()

        self.assertTrue(offer.is_offer)
        with self.assertRaises(InvisibleOptInObservationError):
            offer.as_observation(claim_id="claim-invisible-opt-in")

    def test_an_offer_is_immutable(self):
        offer = invisible_opt_in()

        with self.assertRaises(FrozenInstanceError):
            offer.owner = "other"


if __name__ == "__main__":
    unittest.main()
