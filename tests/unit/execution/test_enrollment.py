"""Behavioral tests for the canon enrollment and sales call (Execution domain).

Rules under test come from SPEC.md section 12.5 (the enrollment and sales call --
the 10x Enrollment Call script, the medical-style frame/examine/prescribe/
prognosis, the pre-call homework qualifier, acceptance/rejection "red velvet
rope" criteria and live payment and checkout -- is a canon gap "between stages 8
and 10" whose intended use is to "convert an engaged prospect into a client with
a defined, authority-preserving process") and section 12.3 (canon files inform
stages 8 to 10). Section 12.5 permits the asset as an "explicit stage 8/9 asset",
which avoids a named-owner stage decision.

The artifact is shaped by the canon:

- Canon file 00 describes the "10x enrollment call" as a medical-office process:
  "there's analysis, there's kind of an examination, a prescription, and a
  prognosis", and warns "you're ... opting out people every step of the way" and
  "once I frame a conversation with someone, I don't go to discovery if there's a
  red flag".
- Canon file 21 requires a pre-call homework qualifier that draws on "a piece of
  my signature solution", schedules "hopefully within 72 hours. No more than
  that", and tells the closer to "always have the purse on the phone" and "accept
  their money live".
- Canon file 06 draws the "red velvet rope" of who is accepted and rejected, and
  canon files 13 and 14 place the enrollment/sales script after the Authority
  Amplifier and the scheduling step of the CAC funnel.

SPEC.md section 12.6 records that the dedicated sales/enrollment training and the
enumerated "six step process" are absent from the supplied canon, so this models
only the explicitly named frame, examine, prescribe and prognosis stages and
records the gap. The plan is a planning asset over the same-tenant stage 8
`FunnelIntegration`, not a new required gate kind (a methodology-owner decision),
it does not authorize spend, payment or external commitment (SPEC.md sections 4
and 9) and it is never an observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.execution.domain.entities import FunnelIntegration
from redops.contexts.execution.domain.enrollment import (
    ENROLLMENT_STEP_ORDER,
    EnrollmentHomework,
    EnrollmentPayment,
    EnrollmentPaymentMethod,
    EnrollmentPlan,
    EnrollmentQualification,
    EnrollmentStep,
    EnrollmentStepKind,
)
from redops.contexts.execution.domain.errors import (
    EnrollmentDependencyError,
    EnrollmentObservationError,
    EnrollmentTenantBoundaryError,
    InvalidEnrollmentError,
)
from redops.contexts.execution.domain.policies import EnrollmentReadinessPolicy

from .fixtures import TENANT, complete_funnel, funnel_integration

STEP_PURPOSES = {
    EnrollmentStepKind.FRAME: "set the two goals and learn why they booked",
    EnrollmentStepKind.EXAMINE: "gather the symptoms behind the problem",
    EnrollmentStepKind.PRESCRIBE: "render the signature solution prescription",
    EnrollmentStepKind.PROGNOSIS: "state the long-term transformation",
}


def step(
    step_kind: EnrollmentStepKind = EnrollmentStepKind.FRAME,
    **overrides,
) -> EnrollmentStep:
    values = {
        "step_kind": step_kind,
        "purpose": STEP_PURPOSES.get(step_kind, "state the purpose"),
        "opt_out_check": "confirm the prospect wants to solve this now",
    }
    values.update(overrides)
    return EnrollmentStep(**values)


def enrollment_steps() -> tuple[EnrollmentStep, ...]:
    return tuple(step(kind) for kind in ENROLLMENT_STEP_ORDER)


def homework(**overrides) -> EnrollmentHomework:
    values = {
        "signature_step": "positioning",
        "questions": (
            "what are your current sales?",
            "what is holding you back?",
        ),
        "max_days_to_call": 3,
    }
    values.update(overrides)
    return EnrollmentHomework(**values)


def qualification(**overrides) -> EnrollmentQualification:
    values = {
        "accept_criteria": ("established business at 10k per month",),
        "reject_criteria": ("still has a day job with no revenue",),
    }
    values.update(overrides)
    return EnrollmentQualification(**values)


def payment(**overrides) -> EnrollmentPayment:
    values = {
        "method": EnrollmentPaymentMethod.CARD,
        "deposit_amount": 2000,
        "collected_live": True,
    }
    values.update(overrides)
    return EnrollmentPayment(**values)


def enrollment_plan(**overrides) -> EnrollmentPlan:
    values = {
        "plan_id": "enrollment-3f",
        "tenant_id": TENANT,
        "owner": "journey-owner",
        "closer": "sales-closer",
        "funnel": complete_funnel(),
        "homework": homework(),
        "steps": enrollment_steps(),
        "qualification": qualification(),
        "payment": payment(),
    }
    values.update(overrides)
    return EnrollmentPlan(**values)


class EnrollmentStepKindTests(unittest.TestCase):
    def test_the_canon_enrollment_call_has_four_named_stages_in_order(self):
        self.assertEqual(
            (
                EnrollmentStepKind.FRAME,
                EnrollmentStepKind.EXAMINE,
                EnrollmentStepKind.PRESCRIBE,
                EnrollmentStepKind.PROGNOSIS,
            ),
            ENROLLMENT_STEP_ORDER,
        )


class EnrollmentStepTests(unittest.TestCase):
    def test_a_step_requires_its_purpose_and_opt_out_check(self):
        self.assertEqual(EnrollmentStepKind.FRAME, step().step_kind)
        for override in (
            {"purpose": ""},
            {"opt_out_check": "  "},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidEnrollmentError):
                    step(**override)

    def test_a_step_refuses_an_untyped_kind(self):
        with self.assertRaises(InvalidEnrollmentError):
            step(step_kind="frame")

    def test_a_step_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            step().purpose = "something else"


class EnrollmentHomeworkTests(unittest.TestCase):
    def test_homework_draws_on_a_signature_step_and_at_least_one_question(self):
        self.assertEqual("positioning", homework().signature_step)
        for override in (
            {"signature_step": ""},
            {"questions": ()},
            {"questions": ("",)},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidEnrollmentError):
                    homework(**override)

    def test_homework_refuses_duplicate_questions(self):
        with self.assertRaises(InvalidEnrollmentError):
            homework(questions=("what is holding you back?",) * 2)

    def test_homework_bounds_the_call_to_the_canon_window(self):
        self.assertEqual(3, homework().max_days_to_call)
        for days in (0, -1, 4, 5):
            with self.subTest(days=days):
                with self.assertRaises(InvalidEnrollmentError):
                    homework(max_days_to_call=days)


class EnrollmentQualificationTests(unittest.TestCase):
    def test_the_red_velvet_rope_needs_accept_and_reject_criteria(self):
        rope = qualification()

        self.assertEqual(("established business at 10k per month",), rope.accept_criteria)
        self.assertEqual(("still has a day job with no revenue",), rope.reject_criteria)
        for override in (
            {"accept_criteria": ()},
            {"reject_criteria": ()},
            {"accept_criteria": ("",)},
            {"reject_criteria": ("  ",)},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidEnrollmentError):
                    qualification(**override)

    def test_the_red_velvet_rope_refuses_duplicate_criteria(self):
        with self.assertRaises(InvalidEnrollmentError):
            qualification(
                accept_criteria=("same",),
                reject_criteria=("same",),
            )


class EnrollmentPaymentTests(unittest.TestCase):
    def test_payment_names_a_typed_method_positive_deposit_and_live_capture(self):
        terms = payment()

        self.assertIs(EnrollmentPaymentMethod.CARD, terms.method)
        self.assertEqual(2000, terms.deposit_amount)
        self.assertTrue(terms.collected_live)
        for override in (
            {"method": "card"},
            {"deposit_amount": 0},
            {"deposit_amount": -100},
            {"collected_live": False},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidEnrollmentError):
                    payment(**override)


class EnrollmentPlanTests(unittest.TestCase):
    def test_a_plan_requires_its_identity_owner_and_closer(self):
        for override in (
            {"plan_id": ""},
            {"tenant_id": "  "},
            {"owner": ""},
            {"closer": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidEnrollmentError):
                    enrollment_plan(**override)

    def test_a_plan_requires_a_typed_same_tenant_funnel(self):
        with self.assertRaises(EnrollmentDependencyError):
            enrollment_plan(funnel="funnel-3f")
        with self.assertRaises(EnrollmentTenantBoundaryError):
            enrollment_plan(tenant_id="client-other")

    def test_a_plan_requires_typed_component_value_objects(self):
        with self.assertRaises(InvalidEnrollmentError):
            enrollment_plan(homework="do the reading")
        with self.assertRaises(InvalidEnrollmentError):
            enrollment_plan(qualification=("yes", "no"))
        with self.assertRaises(InvalidEnrollmentError):
            enrollment_plan(payment="$2000")

    def test_a_plan_requires_exactly_the_canon_steps_in_order(self):
        self.assertEqual(ENROLLMENT_STEP_ORDER, enrollment_plan().step_kinds)
        for steps in (
            enrollment_steps()[:-1],
            enrollment_steps() + (step(),),
            tuple(reversed(enrollment_steps())),
            ("frame",),
        ):
            with self.subTest(steps=steps):
                with self.assertRaises(InvalidEnrollmentError):
                    enrollment_plan(steps=steps)

    def test_a_plan_is_a_plan_not_an_observation(self):
        self.assertTrue(enrollment_plan().is_plan)
        with self.assertRaises(EnrollmentObservationError):
            enrollment_plan().as_observation(claim_id="claim-1")

    def test_a_plan_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            enrollment_plan().closer = "someone-else"


class EnrollmentReadinessPolicyTests(unittest.TestCase):
    def test_a_plan_over_a_complete_funnel_is_ready(self):
        EnrollmentReadinessPolicy().require(enrollment_plan())

    def test_enrollment_cannot_run_before_the_funnel_is_complete(self):
        plan = enrollment_plan(funnel=funnel_integration())

        with self.assertRaises(EnrollmentDependencyError):
            EnrollmentReadinessPolicy().require(plan)

    def test_readiness_checks_a_typed_funnel(self):
        self.assertIsInstance(enrollment_plan().funnel, FunnelIntegration)


if __name__ == "__main__":
    unittest.main()
