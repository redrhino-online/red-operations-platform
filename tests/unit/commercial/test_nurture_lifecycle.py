"""Behavioral tests for the follow-up and nurture lifecycle (Commercial domain).

Rules under test come from SPEC.md section 12.3 and section 12.5 (the follow-up
and nurture lifecycle is a canon gap that sits after stage 10) and section 3
(observations stay distinct from conclusions), shaped by the canon's follow-up
material (canon files 15, 24, 33 and 34):

- The Signature Solution Series takes each step of the Signature Solution and
  turns it into follow-up content sent over time (canon file 15: "when we teach
  you how to do your signature solution series... you're going to come up with
  tons of FAQs", "that lives inside this greater journey").
- Follow-up messaging uses the 5P modalities -- problem, promise, proof, ping and
  promotion (canon file 33: "these five Ps... a problem people have... the promise
  of what life or the outcome will be... demonstrate proof... ping them, ask them
  a question... or a promotion").
- The one-question survey asks a single qualifying question (canon file 24: "if
  I send a one question email to your list... which would it be?").
- Non-openers are re-engaged by resending the message with different headlines,
  not one identical copy (canon file 24: "I should still be sending that message
  to them two or three times over the next week... with maybe different
  headlines").
- No-shows and non-buyers still get a sequence after a booked call (canon file 24:
  "once someone's booked a call, whether they've showed up or not, if they haven't
  signed up, then I need to get a sequence going for them after that").

The lifecycle is a plan; it is not an observed result (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    InvalidNurtureError,
    NurtureDependencyError,
    NurtureObservationError,
    NurtureSequenceError,
    NurtureTenantBoundaryError,
)
from redops.contexts.commercial.domain.value_objects import (
    NURTURE_PLAN_KIND,
    NurtureAudienceState,
    NurtureMessage,
    NurtureModality,
    NurturePlan,
    NurtureSequence,
    REQUIRED_NURTURE_STATES,
)

from .fixtures import TENANT
from ..method.fixtures import signature_solution


def nurture_message(**overrides) -> NurtureMessage:
    values = {
        "message_id": "nurture-1",
        "tenant_id": TENANT,
        "name": "what stalls your referrals",
        "audience_state": NurtureAudienceState.OPTED_IN_NOT_BOOKED,
        "modality": NurtureModality.PROBLEM,
        "signature_step": "Diagnose",
        "subject": "the referral question you keep avoiding",
        "purpose": "name the problem so the lead recognizes it",
    }
    values.update(overrides)
    return NurtureMessage(**values)


def nurture_sequence(**overrides) -> NurtureSequence:
    values = {
        "sequence_id": "sequence-opted",
        "tenant_id": TENANT,
        "audience_state": NurtureAudienceState.OPTED_IN_NOT_BOOKED,
        "messages": (
            nurture_message(),
            nurture_message(
                message_id="nurture-2",
                name="book a referral diagnostic",
                modality=NurtureModality.PROMOTION,
                subject="your referral diagnostic is open",
                purpose="promote the next step",
            ),
        ),
    }
    values.update(overrides)
    return NurtureSequence(**values)


def nurture_plan(**overrides) -> NurturePlan:
    values = {
        "plan_id": "nurture-3f",
        "tenant_id": TENANT,
        "owner": "campaign-operator",
        "method": signature_solution(),
        "sequences": (nurture_sequence(),),
    }
    values.update(overrides)
    return NurturePlan(**values)


class NurtureModalityTests(unittest.TestCase):
    def test_the_five_canon_modalities_are_named(self):
        self.assertEqual(
            {
                "problem",
                "promise",
                "proof",
                "ping",
                "promotion",
            },
            {modality.value for modality in NurtureModality},
        )

    def test_the_canon_prospect_states_are_named(self):
        self.assertEqual(
            {
                "opted_in_not_booked",
                "booked_no_show",
                "attended_not_enrolled",
                "non_opener",
            },
            {state.value for state in NurtureAudienceState},
        )


class NurtureMessageTests(unittest.TestCase):
    def test_a_message_records_state_modality_step_subject_and_purpose(self):
        message = nurture_message()

        self.assertEqual(
            NurtureAudienceState.OPTED_IN_NOT_BOOKED, message.audience_state
        )
        self.assertEqual(NurtureModality.PROBLEM, message.modality)
        self.assertEqual("Diagnose", message.signature_step)
        self.assertEqual(
            "the referral question you keep avoiding", message.subject
        )
        self.assertEqual(
            "name the problem so the lead recognizes it", message.purpose
        )

    def test_a_message_is_frozen(self):
        message = nurture_message()

        with self.assertRaises(FrozenInstanceError):
            message.subject = "changed"

    def test_a_message_requires_a_subject(self):
        with self.assertRaises(InvalidNurtureError):
            nurture_message(subject="   ")

    def test_a_message_requires_a_purpose(self):
        with self.assertRaises(InvalidNurtureError):
            nurture_message(purpose="")

    def test_a_message_requires_a_signature_step(self):
        with self.assertRaises(InvalidNurtureError):
            nurture_message(signature_step="  ")

    def test_a_message_rejects_an_unknown_modality(self):
        with self.assertRaises(InvalidNurtureError):
            nurture_message(modality="upsell")

    def test_a_message_rejects_an_unknown_audience_state(self):
        with self.assertRaises(InvalidNurtureError):
            nurture_message(audience_state="cold")

    def test_a_ping_message_must_ask_exactly_one_question(self):
        message = nurture_message(
            modality=NurtureModality.PING,
            question="which of these would you fix first?",
        )

        self.assertEqual("which of these would you fix first?", message.question)

    def test_a_ping_message_without_a_question_is_refused(self):
        with self.assertRaises(NurtureSequenceError):
            nurture_message(modality=NurtureModality.PING)

    def test_a_ping_message_with_a_blank_question_is_refused(self):
        with self.assertRaises(NurtureSequenceError):
            nurture_message(modality=NurtureModality.PING, question="   ")

    def test_a_non_ping_message_cannot_carry_a_question(self):
        with self.assertRaises(NurtureSequenceError):
            nurture_message(
                modality=NurtureModality.PROOF,
                question="what is your biggest struggle?",
            )


class NurtureSequenceTests(unittest.TestCase):
    def test_a_sequence_orders_its_messages_for_one_state(self):
        sequence = nurture_sequence()

        self.assertEqual(
            NurtureAudienceState.OPTED_IN_NOT_BOOKED, sequence.audience_state
        )
        self.assertEqual(
            ("nurture-1", "nurture-2"),
            tuple(message.message_id for message in sequence.messages),
        )

    def test_a_sequence_requires_at_least_one_message(self):
        with self.assertRaises(NurtureSequenceError):
            nurture_sequence(messages=())

    def test_a_sequence_cannot_mix_messages_from_another_tenant(self):
        with self.assertRaises(NurtureTenantBoundaryError):
            nurture_sequence(
                messages=(
                    nurture_message(tenant_id="client-other"),
                )
            )

    def test_a_sequence_cannot_mix_audience_states(self):
        with self.assertRaises(NurtureSequenceError):
            nurture_sequence(
                messages=(
                    nurture_message(),
                    nurture_message(
                        message_id="nurture-2",
                        audience_state=NurtureAudienceState.NON_OPENER,
                    ),
                )
            )

    def test_a_sequence_rejects_duplicate_message_ids(self):
        with self.assertRaises(NurtureSequenceError):
            nurture_sequence(
                messages=(
                    nurture_message(),
                    nurture_message(
                        message_id="nurture-1",
                        subject="a different subject",
                    ),
                )
            )

    def test_a_non_opener_sequence_needs_distinct_subjects(self):
        with self.assertRaises(NurtureSequenceError):
            nurture_sequence(
                audience_state=NurtureAudienceState.NON_OPENER,
                messages=(
                    nurture_message(
                        audience_state=NurtureAudienceState.NON_OPENER
                    ),
                ),
            )

    def test_a_non_opener_sequence_with_repeated_subjects_is_refused(self):
        with self.assertRaises(NurtureSequenceError):
            nurture_sequence(
                audience_state=NurtureAudienceState.NON_OPENER,
                messages=(
                    nurture_message(
                        audience_state=NurtureAudienceState.NON_OPENER
                    ),
                    nurture_message(
                        message_id="nurture-2",
                        audience_state=NurtureAudienceState.NON_OPENER,
                    ),
                ),
            )

    def test_a_non_opener_sequence_with_different_headlines_is_accepted(self):
        sequence = nurture_sequence(
            audience_state=NurtureAudienceState.NON_OPENER,
            messages=(
                nurture_message(
                    audience_state=NurtureAudienceState.NON_OPENER
                ),
                nurture_message(
                    message_id="nurture-2",
                    audience_state=NurtureAudienceState.NON_OPENER,
                    subject="did this reach you?",
                ),
            ),
        )

        self.assertEqual(2, len(sequence.messages))


class NurturePlanTests(unittest.TestCase):
    def test_a_plan_binds_an_owner_method_and_sequences(self):
        plan = nurture_plan()

        self.assertEqual("campaign-operator", plan.owner)
        self.assertEqual("nurture-3f", plan.plan_id)
        self.assertEqual(("sequence-opted",), tuple(
            sequence.sequence_id for sequence in plan.sequences
        ))

    def test_a_plan_requires_a_named_owner(self):
        with self.assertRaises(InvalidNurtureError):
            nurture_plan(owner="  ")

    def test_a_plan_requires_a_signature_solution(self):
        with self.assertRaises(NurtureDependencyError):
            nurture_plan(method="signature solution")

    def test_a_plan_cannot_derive_from_another_tenants_method(self):
        with self.assertRaises(NurtureTenantBoundaryError):
            nurture_plan(method=signature_solution(tenant_id="client-other"))

    def test_a_message_step_the_method_does_not_have_is_refused(self):
        with self.assertRaises(NurtureDependencyError):
            nurture_plan(
                sequences=(
                    nurture_sequence(
                        messages=(
                            nurture_message(signature_step="Invent a tactic"),
                        )
                    ),
                )
            )

    def test_a_plan_cannot_cite_another_tenants_sequence(self):
        with self.assertRaises(NurtureTenantBoundaryError):
            nurture_plan(
                sequences=(
                    nurture_sequence(tenant_id="client-other"),
                )
            )

    def test_a_plan_rejects_duplicate_sequence_ids(self):
        with self.assertRaises(NurtureSequenceError):
            nurture_plan(
                sequences=(
                    nurture_sequence(),
                    nurture_sequence(
                        audience_state=NurtureAudienceState.NON_OPENER,
                        messages=(
                            nurture_message(
                                message_id="nurture-3",
                                audience_state=NurtureAudienceState.NON_OPENER,
                            ),
                            nurture_message(
                                message_id="nurture-4",
                                audience_state=NurtureAudienceState.NON_OPENER,
                                subject="a different headline",
                            ),
                        ),
                    ),
                )
            )

    def test_a_plan_reports_the_states_it_is_missing(self):
        plan = nurture_plan()

        self.assertEqual(
            (
                NurtureAudienceState.BOOKED_NO_SHOW,
                NurtureAudienceState.ATTENDED_NOT_ENROLLED,
                NurtureAudienceState.NON_OPENER,
            ),
            plan.missing_states(),
        )

    def test_a_plan_is_complete_when_every_canon_state_is_covered(self):
        plan = nurture_plan(
            sequences=(
                nurture_sequence(
                    audience_state=NurtureAudienceState.OPTED_IN_NOT_BOOKED
                ),
                nurture_sequence(
                    sequence_id="sequence-no-show",
                    audience_state=NurtureAudienceState.BOOKED_NO_SHOW,
                    messages=(
                        nurture_message(
                            message_id="no-show-1",
                            audience_state=NurtureAudienceState.BOOKED_NO_SHOW,
                        ),
                    ),
                ),
                nurture_sequence(
                    sequence_id="sequence-attended",
                    audience_state=NurtureAudienceState.ATTENDED_NOT_ENROLLED,
                    messages=(
                        nurture_message(
                            message_id="attended-1",
                            audience_state=(
                                NurtureAudienceState.ATTENDED_NOT_ENROLLED
                            ),
                        ),
                    ),
                ),
                nurture_sequence(
                    sequence_id="sequence-non-opener",
                    audience_state=NurtureAudienceState.NON_OPENER,
                    messages=(
                        nurture_message(
                            message_id="non-opener-1",
                            audience_state=NurtureAudienceState.NON_OPENER,
                        ),
                        nurture_message(
                            message_id="non-opener-2",
                            audience_state=NurtureAudienceState.NON_OPENER,
                            subject="a different headline",
                        ),
                    ),
                ),
            )
        )

        self.assertTrue(plan.is_complete)
        self.assertEqual((), plan.missing_states())

    def test_the_required_states_are_the_canon_prospect_states(self):
        self.assertEqual(
            (
                NurtureAudienceState.OPTED_IN_NOT_BOOKED,
                NurtureAudienceState.BOOKED_NO_SHOW,
                NurtureAudienceState.ATTENDED_NOT_ENROLLED,
                NurtureAudienceState.NON_OPENER,
            ),
            REQUIRED_NURTURE_STATES,
        )

    def test_a_plan_is_not_an_observation(self):
        plan = nurture_plan()

        self.assertTrue(plan.is_plan)
        with self.assertRaises(NurtureObservationError):
            plan.as_observation(claim_id="claim-nurture")


class NurturePlanStageAssetTests(unittest.TestCase):
    def test_the_plan_projects_the_nurture_plan_kind_at_its_own_identity(self):
        asset = nurture_plan().as_stage_asset(version=3)

        self.assertEqual(NURTURE_PLAN_KIND, asset.kind)
        self.assertEqual("nurture-3f", asset.asset_id)
        self.assertEqual(TENANT, asset.tenant_id)
        self.assertEqual(3, asset.version)

    def test_a_versionless_projection_is_refused(self):
        for version in (0, -1):
            with self.subTest(version=version):
                with self.assertRaises(InvalidNurtureError):
                    nurture_plan().as_stage_asset(version=version)


if __name__ == "__main__":
    unittest.main()
