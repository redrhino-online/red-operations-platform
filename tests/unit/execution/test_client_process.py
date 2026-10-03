"""Behavioral tests for the client-authored enrollment process (Execution domain).

Rules under test come from SPEC.md section 12.7 (RED helps each client design and
implement their own sales process, in the client's voice, using the enrollment
block, canon files 35-49, as a template rather than as copy; the result is a
versioned, client-approved stage 8/9 asset that feeds stage 10 measurement and is
never a new pipeline stage) and from the canon it is shaped by:

- Canon files 39-45 give the six part process in order (frame, discover problems,
  prescription, application, invitation, objection crusher).
- Canon files 39-43 give the five pass-or-fail checkpoints (intent, commitment,
  value, confidence, desire), each with the client's own question.
- Canon file 43 draws the acceptance and rejection line.
- Canon file 45 answers the common objections through clarity, commitment and
  confidence.
- Canon file 47 names the three strategy-session models, bounds the booking window
  to 72 hours and applies a strict no-show policy.

The process is a plan, not an observation, and it does not authorize spend,
sending, publishing, payment or a client commitment (SPEC.md sections 3, 4 and 9).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.execution.domain.client_process import (
    CANON_REFERENCE,
    CLIENT_CHECKPOINT_ORDER,
    CLIENT_PROCESS_STEP_ORDER,
    MAXIMUM_BOOKING_WINDOW_DAYS,
    ClientCheckpoint,
    ClientCheckpointKind,
    ClientObjectionAnswer,
    ClientProcess,
    ClientProcessCommitmentTerms,
    ClientProcessHomework,
    ClientProcessStep,
    ClientProcessStepKind,
    StrategySessionModel,
)
from redops.contexts.execution.domain.errors import (
    ClientProcessDependencyError,
    ClientProcessObservationError,
    ClientProcessTenantBoundaryError,
    InvalidClientProcessError,
)
from redops.contexts.execution.domain.policies import ClientProcessReadinessPolicy

from tests.unit.commercial.test_product_program import (
    product_module,
    product_program,
)
from ..method.fixtures import (
    diagnostic_model,
    primary_currency,
    signature_solution,
)
from .fixtures import TENANT

STEP_PURPOSES = {
    ClientProcessStepKind.FRAME: "set the frame, goals and decision maker",
    ClientProcessStepKind.DISCOVER_PROBLEMS: "audit them against the method",
    ClientProcessStepKind.PRESCRIPTION: "render the three-lever prescription",
    ClientProcessStepKind.APPLICATION: "test fit against the acceptance line",
    ClientProcessStepKind.INVITATION: "invite them without pressure or pitching",
    ClientProcessStepKind.OBJECTION_CRUSHER: "return every concern to clarity",
}


def step(
    step_kind: ClientProcessStepKind = ClientProcessStepKind.FRAME,
    **overrides,
) -> ClientProcessStep:
    values = {
        "step_kind": step_kind,
        "purpose": STEP_PURPOSES.get(step_kind, "state the purpose"),
        "prompt": f"the client's own wording for {step_kind.value}",
    }
    values.update(overrides)
    return ClientProcessStep(**values)


def process_steps() -> tuple[ClientProcessStep, ...]:
    return tuple(step(kind) for kind in CLIENT_PROCESS_STEP_ORDER)


def checkpoint(
    kind: ClientCheckpointKind = ClientCheckpointKind.INTENT,
    **overrides,
) -> ClientCheckpoint:
    values = {
        "kind": kind,
        "question": f"the client's question for {kind.value}",
        "on_fail_action": "step back and reset before continuing",
    }
    values.update(overrides)
    return ClientCheckpoint(**values)


def checkpoints() -> tuple[ClientCheckpoint, ...]:
    return tuple(checkpoint(kind) for kind in CLIENT_CHECKPOINT_ORDER)


def homework(**overrides) -> ClientProcessHomework:
    values = {
        "signature_step": "Position",
        "questions": (
            "what is your current measure?",
            "what is stopping you?",
        ),
        "booking_window_days": 3,
    }
    values.update(overrides)
    return ClientProcessHomework(**values)


def objection(**overrides) -> ClientObjectionAnswer:
    values = {
        "concern": "how much does it cost?",
        "answer": "the client asks how many clients would make it pay for itself",
    }
    values.update(overrides)
    return ClientObjectionAnswer(**values)


def terms(**overrides) -> ClientProcessCommitmentTerms:
    values = {
        "price_floor": 3000,
        "no_show_rules": ("confirm within the booking window",),
    }
    values.update(overrides)
    return ClientProcessCommitmentTerms(**values)


def client_process(**overrides) -> ClientProcess:
    values = {
        "process_id": "process-3f",
        "tenant_id": TENANT,
        "owner": "red-process-owner",
        "approver": "client-authority",
        "version": 1,
        "currency": primary_currency(),
        "model": diagnostic_model(),
        "method": signature_solution(),
        "program": product_program(),
        "strategy": StrategySessionModel.PAID_STRATEGY_SESSION,
        "homework": homework(),
        "steps": process_steps(),
        "checkpoints": checkpoints(),
        "acceptance_criteria": ("existing business with a delivered offer",),
        "rejection_criteria": ("no product and no revenue",),
        "objections": (objection(),),
        "terms": terms(),
    }
    values.update(overrides)
    return ClientProcess(**values)


class ClientProcessShapeTests(unittest.TestCase):
    def test_a_valid_process_is_a_plan_that_feeds_stages_nine_and_ten(self) -> None:
        process = client_process()
        self.assertTrue(process.is_plan)
        self.assertEqual((9, 10), process.feeds_stages)
        self.assertEqual(CANON_REFERENCE, process.canon_reference)
        self.assertEqual("35-49", process.canon_reference)

    def test_the_canon_parts_are_the_six_fixed_parts_in_order(self) -> None:
        self.assertEqual(
            (
                ClientProcessStepKind.FRAME,
                ClientProcessStepKind.DISCOVER_PROBLEMS,
                ClientProcessStepKind.PRESCRIPTION,
                ClientProcessStepKind.APPLICATION,
                ClientProcessStepKind.INVITATION,
                ClientProcessStepKind.OBJECTION_CRUSHER,
            ),
            CLIENT_PROCESS_STEP_ORDER,
        )
        self.assertEqual(
            CLIENT_PROCESS_STEP_ORDER, client_process().step_kinds
        )

    def test_the_checkpoints_are_the_five_fixed_checkpoints_in_order(self) -> None:
        self.assertEqual(
            (
                ClientCheckpointKind.INTENT,
                ClientCheckpointKind.COMMITMENT,
                ClientCheckpointKind.VALUE,
                ClientCheckpointKind.CONFIDENCE,
                ClientCheckpointKind.DESIRE,
            ),
            CLIENT_CHECKPOINT_ORDER,
        )
        self.assertEqual(
            CLIENT_CHECKPOINT_ORDER, client_process().checkpoint_kinds
        )

    def test_the_process_is_frozen(self) -> None:
        process = client_process()
        with self.assertRaises(FrozenInstanceError):
            process.owner = "someone-else"  # type: ignore[misc]

    def test_a_missing_part_is_refused(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            client_process(steps=process_steps()[:-1])

    def test_an_out_of_order_part_is_refused(self) -> None:
        reordered = tuple(reversed(process_steps()))
        with self.assertRaises(InvalidClientProcessError):
            client_process(steps=reordered)

    def test_a_duplicated_checkpoint_is_refused(self) -> None:
        duplicated = checkpoints()[:-1] + (checkpoint(ClientCheckpointKind.INTENT),)
        with self.assertRaises(InvalidClientProcessError):
            client_process(checkpoints=duplicated)

    def test_a_blank_step_prompt_or_purpose_is_refused(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            step(prompt="   ")
        with self.assertRaises(InvalidClientProcessError):
            step(purpose="")

    def test_a_blank_checkpoint_question_or_fail_action_is_refused(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            checkpoint(question="")
        with self.assertRaises(InvalidClientProcessError):
            checkpoint(on_fail_action="   ")

    def test_an_untyped_strategy_model_is_refused(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            client_process(strategy="single-call")

    def test_a_blank_approver_is_refused(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            client_process(approver="   ")

    def test_an_author_cannot_approve_their_own_process(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            client_process(owner="same-person", approver="same-person")

    def test_a_non_positive_or_missing_version_is_refused(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            client_process(version=0)
        with self.assertRaises(InvalidClientProcessError):
            client_process(version="1")


class ClientProcessQualificationTests(unittest.TestCase):
    def test_the_process_needs_both_an_accept_and_a_reject_line(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            client_process(acceptance_criteria=())
        with self.assertRaises(InvalidClientProcessError):
            client_process(rejection_criteria=())

    def test_a_criterion_cannot_be_both_accepted_and_rejected(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            client_process(
                acceptance_criteria=("has existing revenue",),
                rejection_criteria=("has existing revenue",),
            )

    def test_at_least_one_objection_must_be_answered(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            client_process(objections=())

    def test_a_duplicate_objection_concern_is_refused(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            client_process(objections=(objection(), objection()))

    def test_a_blank_objection_answer_is_refused(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            objection(answer="")

    def test_a_non_positive_price_floor_is_refused(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            terms(price_floor=0)

    def test_a_process_needs_at_least_one_no_show_rule(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            terms(no_show_rules=())


class ClientProcessHomeworkTests(unittest.TestCase):
    def test_the_booking_window_may_be_at_most_three_days(self) -> None:
        self.assertEqual(3, MAXIMUM_BOOKING_WINDOW_DAYS)
        self.assertEqual(3, homework().booking_window_days)
        with self.assertRaises(InvalidClientProcessError):
            homework(booking_window_days=4)
        with self.assertRaises(InvalidClientProcessError):
            homework(booking_window_days=0)

    def test_homework_needs_a_duplicate_free_question_set(self) -> None:
        with self.assertRaises(InvalidClientProcessError):
            homework(questions=("same question", "same question"))
        with self.assertRaises(InvalidClientProcessError):
            homework(questions=())

    def test_homework_must_draw_on_a_named_method_step(self) -> None:
        with self.assertRaises(ClientProcessDependencyError):
            client_process(homework=homework(signature_step="Not A Step"))


class ClientProcessGroundingTests(unittest.TestCase):
    def test_a_foreign_currency_is_refused(self) -> None:
        with self.assertRaises(ClientProcessTenantBoundaryError):
            client_process(currency=primary_currency("other-tenant"))

    def test_a_foreign_method_is_refused(self) -> None:
        with self.assertRaises(ClientProcessTenantBoundaryError):
            client_process(method=signature_solution("other-tenant"))

    def test_a_process_cannot_be_recorded_as_an_observation(self) -> None:
        with self.assertRaises(ClientProcessObservationError):
            client_process().as_observation(claim_id="claim-1")


class ClientProcessReadinessPolicyTests(unittest.TestCase):
    def test_a_program_that_delivers_every_step_passes(self) -> None:
        ClientProcessReadinessPolicy().require(client_process())

    def test_an_incomplete_program_blocks_the_process(self) -> None:
        solution = signature_solution()
        partial = product_program(
            method=solution,
            modules=tuple(
                product_module(item.name, index + 1)
                for index, item in enumerate(solution.steps[:-1])
            ),
        )
        with self.assertRaises(ClientProcessDependencyError):
            ClientProcessReadinessPolicy().require(
                client_process(program=partial)
            )


if __name__ == "__main__":
    unittest.main()
