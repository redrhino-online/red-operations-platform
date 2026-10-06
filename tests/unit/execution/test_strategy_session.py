"""Behavioral tests for the canon strategy-session kit (Execution domain).

Rules under test come from the canon's paid strategy-session material and the
implementation plan's canon gap backlog item G4 (SPEC.md section 12.5 records the
strategy-session kit as a canon gap; the backlog names a typed artifact that is "a
third enrollment model; refuses a price below the floor"). The shape is extracted
from:

- Canon file 47: the paid strategy session is the bridge between paying nothing
  and a high-ticket program, a 60 to 90 minute session that builds a 90-day
  roadmap, usually $1,000, gated by a short application, with the fee credited to
  the first month of the program ("I'll take the thousand dollars you paid. Now
  it's your first month of coaching").
- Synthesized `ops/playbooks/strategy-session.md`,
  `ops/checklists/strategy-session-call.md` and
  `ops/sops/strategy-session-run.md`: the $500 floor, the before-and-after map
  over the signature solution, the three calm questions asked in order (plan
  works, alone, want help), and the fee credit.

The kit is a stage 8/9 enrollment plan, not a new required gate kind. It does not
authorize sending, spend, payment or any client commitment (SPEC.md sections 4 and
9) and it is never an observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.execution.domain.client_process import StrategySessionModel
from redops.contexts.execution.domain.errors import (
    InvalidStrategySessionError,
    StrategySessionDependencyError,
    StrategySessionFormatError,
    StrategySessionObservationError,
    StrategySessionTenantBoundaryError,
)
from redops.contexts.execution.domain.strategy_session import (
    STRATEGY_SESSION_CANON_REFERENCE,
    STRATEGY_SESSION_DEFAULT_PRICE,
    STRATEGY_SESSION_PLAN_DAYS,
    STRATEGY_SESSION_PRICE_FLOOR,
    STRATEGY_SESSION_QUESTION_ORDER,
    StrategySessionApplication,
    StrategySessionFeeCredit,
    StrategySessionKit,
    StrategySessionQuestion,
    StrategySessionQuestionKind,
    StrategySessionRoadmap,
    StrategySessionRoadmapStep,
)

from tests.unit.commercial.test_product_program import (
    product_module,
    product_program,
)
from ..method.fixtures import signature_solution
from .fixtures import TENANT

OTHER_TENANT = "client-other"


def question(
    kind: StrategySessionQuestionKind = StrategySessionQuestionKind.CONFIDENCE,
    **overrides,
) -> StrategySessionQuestion:
    values = {
        "kind": kind,
        "question": f"the client's own wording for {kind.value}",
    }
    values.update(overrides)
    return StrategySessionQuestion(**values)


def questions() -> tuple[StrategySessionQuestion, ...]:
    return tuple(question(kind) for kind in STRATEGY_SESSION_QUESTION_ORDER)


def application(**overrides) -> StrategySessionApplication:
    values = {
        "application_id": "application-3f",
        "questions": (
            "what is your business doing in monthly sales?",
            "what is a new client worth to you?",
        ),
    }
    values.update(overrides)
    return StrategySessionApplication(**values)


def roadmap_step(step_name: str, **overrides) -> StrategySessionRoadmapStep:
    values = {
        "step_name": step_name,
        "has": f"what the lead already has for {step_name}",
        "missing": f"what the lead is missing for {step_name}",
    }
    values.update(overrides)
    return StrategySessionRoadmapStep(**values)


def roadmap(solution=None, **overrides) -> StrategySessionRoadmap:
    source = solution if solution is not None else signature_solution()
    values = {
        "tenant_id": TENANT,
        "steps": tuple(roadmap_step(step.name) for step in source.steps),
    }
    values.update(overrides)
    return StrategySessionRoadmap(**values)


def fee_credit(**overrides) -> StrategySessionFeeCredit:
    values = {
        "credited_to_month": 1,
        "note": "the session fee becomes the first month of the program",
    }
    values.update(overrides)
    return StrategySessionFeeCredit(**values)


def strategy_session(**overrides) -> StrategySessionKit:
    values = {
        "kit_id": "strategy-session-3f",
        "tenant_id": TENANT,
        "owner": "enrollment-specialist",
        "solution": signature_solution(),
        "program": product_program(),
        "session_price": STRATEGY_SESSION_DEFAULT_PRICE,
        "session_minutes": 75,
        "application": application(),
        "roadmap": roadmap(),
        "questions": questions(),
        "fee_credit": fee_credit(),
    }
    values.update(overrides)
    return StrategySessionKit(**values)


def other_tenant_program():
    solution = signature_solution(OTHER_TENANT)
    return product_program(
        method=solution,
        tenant_id=OTHER_TENANT,
        modules=tuple(
            product_module(step.name, index + 1, tenant_id=OTHER_TENANT)
            for index, step in enumerate(solution.steps)
        ),
    )


class StrategySessionShapeTests(unittest.TestCase):
    def test_canon_reference_names_the_strategy_session_sources(self) -> None:
        self.assertIn("47", STRATEGY_SESSION_CANON_REFERENCE)
        self.assertIn("Live Sessions 8", STRATEGY_SESSION_CANON_REFERENCE)

    def test_a_valid_kit_is_a_plan_that_feeds_stages_nine_and_ten(self) -> None:
        kit = strategy_session()
        self.assertTrue(kit.is_plan)
        self.assertEqual((9, 10), kit.feeds_stages)
        self.assertEqual(
            StrategySessionModel.PAID_STRATEGY_SESSION, kit.model
        )
        self.assertEqual(STRATEGY_SESSION_PLAN_DAYS, kit.plan_days)
        self.assertEqual(STRATEGY_SESSION_CANON_REFERENCE, kit.canon_reference)

    def test_the_kit_is_frozen(self) -> None:
        kit = strategy_session()
        with self.assertRaises(FrozenInstanceError):
            kit.owner = "someone-else"  # type: ignore[misc]

    def test_blank_identity_is_refused(self) -> None:
        for field in ("kit_id", "owner"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidStrategySessionError):
                    strategy_session(**{field: "  "})


class StrategySessionPriceTests(unittest.TestCase):
    def test_the_default_price_is_one_thousand_and_the_floor_is_five_hundred(
        self,
    ) -> None:
        self.assertEqual(1000, STRATEGY_SESSION_DEFAULT_PRICE)
        self.assertEqual(500, STRATEGY_SESSION_PRICE_FLOOR)
        self.assertEqual(1000, strategy_session().session_price)

    def test_a_price_below_the_floor_is_refused(self) -> None:
        with self.assertRaises(StrategySessionFormatError):
            strategy_session(session_price=STRATEGY_SESSION_PRICE_FLOOR - 1)

    def test_a_price_at_the_floor_is_accepted(self) -> None:
        self.assertEqual(
            STRATEGY_SESSION_PRICE_FLOOR,
            strategy_session(session_price=STRATEGY_SESSION_PRICE_FLOOR).session_price,
        )

    def test_a_price_must_be_a_whole_number(self) -> None:
        with self.assertRaises(InvalidStrategySessionError):
            strategy_session(session_price="1000")

    def test_the_session_must_run_sixty_to_ninety_minutes(self) -> None:
        with self.assertRaises(StrategySessionFormatError):
            strategy_session(session_minutes=59)
        with self.assertRaises(StrategySessionFormatError):
            strategy_session(session_minutes=91)


class StrategySessionApplicationTests(unittest.TestCase):
    def test_the_application_gate_is_required_and_typed(self) -> None:
        with self.assertRaises(InvalidStrategySessionError):
            strategy_session(application="not-an-application")

    def test_the_application_needs_a_duplicate_free_question_set(self) -> None:
        with self.assertRaises(InvalidStrategySessionError):
            application(questions=())
        with self.assertRaises(InvalidStrategySessionError):
            application(questions=("same question", "same question"))

    def test_a_blank_application_id_is_refused(self) -> None:
        with self.assertRaises(InvalidStrategySessionError):
            application(application_id="   ")


class StrategySessionRoadmapTests(unittest.TestCase):
    def test_the_roadmap_covers_every_solution_step_exactly_once(self) -> None:
        solution = signature_solution()
        missing = tuple(roadmap_step(step.name) for step in solution.steps[:-1])
        with self.assertRaises(StrategySessionFormatError):
            strategy_session(roadmap=roadmap(solution, steps=missing))
        extra = tuple(roadmap_step(step.name) for step in solution.steps) + (
            roadmap_step("Invent a new step"),
        )
        with self.assertRaises(StrategySessionDependencyError):
            strategy_session(roadmap=roadmap(solution, steps=extra))
        duplicate = tuple(roadmap_step(step.name) for step in solution.steps[:-1]) + (
            roadmap_step(solution.steps[0].name),
        )
        with self.assertRaises(StrategySessionFormatError):
            strategy_session(roadmap=roadmap(solution, steps=duplicate))

    def test_a_roadmap_step_must_name_a_step_the_solution_names(self) -> None:
        solution = signature_solution()
        steps = tuple(roadmap_step(step.name) for step in solution.steps[:-1]) + (
            roadmap_step("Invent a new step"),
        )
        with self.assertRaises(StrategySessionDependencyError):
            strategy_session(roadmap=roadmap(solution, steps=steps))

    def test_a_blank_roadmap_step_field_is_refused(self) -> None:
        with self.assertRaises(InvalidStrategySessionError):
            roadmap_step("Diagnose", has="   ")
        with self.assertRaises(InvalidStrategySessionError):
            roadmap_step("Diagnose", missing="")


class StrategySessionQuestionTests(unittest.TestCase):
    def test_the_three_questions_are_asked_in_order(self) -> None:
        self.assertEqual(
            (
                StrategySessionQuestionKind.CONFIDENCE,
                StrategySessionQuestionKind.ALONE,
                StrategySessionQuestionKind.HELP,
            ),
            STRATEGY_SESSION_QUESTION_ORDER,
        )
        self.assertEqual(
            STRATEGY_SESSION_QUESTION_ORDER,
            tuple(item.kind for item in strategy_session().questions),
        )

    def test_a_missing_or_out_of_order_question_is_refused(self) -> None:
        with self.assertRaises(StrategySessionFormatError):
            strategy_session(questions=questions()[:-1])
        with self.assertRaises(StrategySessionFormatError):
            strategy_session(questions=tuple(reversed(questions())))

    def test_a_blank_question_is_refused(self) -> None:
        with self.assertRaises(InvalidStrategySessionError):
            question(question="   ")


class StrategySessionFeeCreditTests(unittest.TestCase):
    def test_the_fee_is_credited_to_the_first_month(self) -> None:
        self.assertEqual(1, fee_credit().credited_to_month)
        with self.assertRaises(StrategySessionFormatError):
            strategy_session(fee_credit=fee_credit(credited_to_month=2))

    def test_a_blank_credit_note_is_refused(self) -> None:
        with self.assertRaises(InvalidStrategySessionError):
            fee_credit(note="   ")


class StrategySessionGroundingTests(unittest.TestCase):
    def test_the_kit_must_be_grounded_on_a_typed_solution_and_program(self) -> None:
        with self.assertRaises(StrategySessionDependencyError):
            strategy_session(solution="not-a-solution")
        with self.assertRaises(StrategySessionDependencyError):
            strategy_session(program="not-a-program")

    def test_a_foreign_solution_or_program_is_refused(self) -> None:
        with self.assertRaises(StrategySessionTenantBoundaryError):
            strategy_session(solution=signature_solution(OTHER_TENANT))
        with self.assertRaises(StrategySessionTenantBoundaryError):
            strategy_session(program=other_tenant_program())

    def test_a_kit_cannot_be_recorded_as_an_observation(self) -> None:
        with self.assertRaises(StrategySessionObservationError):
            strategy_session().as_observation(claim_id="claim-1")


if __name__ == "__main__":
    unittest.main()
