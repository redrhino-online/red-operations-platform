"""Behavioral tests for the canon delivery ladder (Portfolio domain).

Rules under test come from the canon's delivery material and the implementation
plan's canon gap backlog item G5 (SPEC.md section 12.5 records the delivery ladder
and ascension as a canon gap; the backlog names a typed artifact that "represents
the client's own delivery (Serve) and the next-offer path; never an observation").
The shape is extracted from:

- Canon files 11 and 12, the Certification series and Live Sessions 5 and 12: the
  delivery ladder -- start one to one, move to a live cohort, then record it as an
  evergreen program.
- Synthesized `ops/playbooks/delivery.md`: the 90-day roadmap audit (check the
  client against their own roadmap and find the missing step), one deliverable per
  step (every module gives the client a working tool), the success goals set at
  kickoff, the gate (results are measured against the goals; if they do not match,
  fix the plan before closing) and the ascension (turn each finished step into a
  small offer).

The ladder is a post-launch Portfolio planning asset, not a new required gate kind.
It does not authorize sending, spend, publishing or any client commitment (SPEC.md
sections 4 and 9) and it is never an observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date, timedelta

from redops.contexts.portfolio.domain.delivery import (
    DELIVERY_CANON_REFERENCE,
    DELIVERY_RUNG_ORDER,
    ROADMAP_AUDIT_DAYS,
    AscensionOffer,
    DeliveryGoal,
    DeliveryLadder,
    DeliveryResult,
    DeliveryRung,
    DeliveryStep,
    RoadmapAudit,
)
from redops.contexts.portfolio.domain.errors import (
    DeliveryAuditCadenceError,
    DeliveryAuditOrderError,
    DeliveryGateError,
    DeliveryLadderDependencyError,
    DeliveryLadderFormatError,
    DeliveryLadderObservationError,
    DeliveryLadderTenantBoundaryError,
    InvalidDeliveryLadderError,
)

from ..commercial.fixtures import product_program
from ..method.fixtures import TENANT, signature_solution

OTHER_TENANT = "client-other"
CREATED = date(2026, 10, 2)


def step(step_name: str, **overrides) -> DeliveryStep:
    values = {
        "step_name": step_name,
        "deliverable": f"the {step_name} working tool",
    }
    values.update(overrides)
    return DeliveryStep(**values)


def steps(program=None) -> tuple[DeliveryStep, ...]:
    source = program if program is not None else product_program()
    return tuple(step(module.signature_step) for module in source.modules)


def audit(**overrides) -> RoadmapAudit:
    values = {
        "audited_on": CREATED,
        "next_audit_on": CREATED + timedelta(days=ROADMAP_AUDIT_DAYS),
        "actor": "red-delivery-lead",
    }
    values.update(overrides)
    return RoadmapAudit(**values)


def goal(**overrides) -> DeliveryGoal:
    values = {
        "name": "qualified leads",
        "metric": "qualified leads per week",
        "target": "20 per week",
    }
    values.update(overrides)
    return DeliveryGoal(**values)


def result(goal_name: str = "qualified leads", **overrides) -> DeliveryResult:
    values = {
        "goal_name": goal_name,
        "observed": "22 per week",
        "met": True,
    }
    values.update(overrides)
    return DeliveryResult(**values)


def offer(step_name: str, **overrides) -> AscensionOffer:
    values = {
        "step_name": step_name,
        "offer_name": f"the {step_name} small offer",
    }
    values.update(overrides)
    return AscensionOffer(**values)


def ladder(**overrides) -> DeliveryLadder:
    program = overrides.pop("program", None)
    if program is None:
        program = product_program()
    tenant_id = overrides.pop("tenant_id", None)
    if tenant_id is None:
        tenant_id = getattr(program, "tenant_id", TENANT)
    values = {
        "ladder_id": "ladder-3f",
        "tenant_id": tenant_id,
        "owner": "red-delivery-lead",
        "program": program,
        "rungs": DELIVERY_RUNG_ORDER,
        "steps": steps(program) if hasattr(program, "modules") else (),
        "audits": (audit(),),
        "goals": (goal(),),
        "ascension_offers": (
            offer(program.modules[0].signature_step)
            if hasattr(program, "modules")
            else (),
        ),
        "created_on": CREATED,
    }
    values.update(overrides)
    return DeliveryLadder(**values)


class DeliveryRungTests(unittest.TestCase):
    def test_the_canon_delivery_ladder_has_three_rungs_in_order(self):
        self.assertEqual(
            (
                DeliveryRung.ONE_TO_ONE,
                DeliveryRung.LIVE_COHORT,
                DeliveryRung.EVERGREEN,
            ),
            DELIVERY_RUNG_ORDER,
        )

    def test_a_ladder_accepts_the_canon_rungs_in_order(self):
        self.assertEqual(DELIVERY_RUNG_ORDER, ladder().rung_kinds)

    def test_a_ladder_must_start_one_to_one(self):
        with self.assertRaises(DeliveryLadderFormatError):
            ladder(rungs=(DeliveryRung.LIVE_COHORT, DeliveryRung.EVERGREEN))

    def test_a_ladder_refuses_out_of_order_rungs(self):
        with self.assertRaises(DeliveryLadderFormatError):
            ladder(
                rungs=(
                    DeliveryRung.ONE_TO_ONE,
                    DeliveryRung.EVERGREEN,
                    DeliveryRung.LIVE_COHORT,
                )
            )

    def test_a_ladder_refuses_duplicate_rungs(self):
        with self.assertRaises(DeliveryLadderFormatError):
            ladder(rungs=(DeliveryRung.ONE_TO_ONE, DeliveryRung.ONE_TO_ONE))

    def test_a_ladder_requires_at_least_one_rung(self):
        with self.assertRaises(InvalidDeliveryLadderError):
            ladder(rungs=())

    def test_a_ladder_requires_a_typed_rung(self):
        with self.assertRaises(InvalidDeliveryLadderError):
            ladder(rungs=("one_to_one",))


class DeliveryStepTests(unittest.TestCase):
    def test_a_ladder_carries_one_deliverable_per_program_step(self):
        program = product_program()
        built = ladder(program=program)
        self.assertEqual(
            tuple(module.signature_step for module in program.modules),
            built.covered_steps,
        )

    def test_a_ladder_refuses_a_missing_step_deliverable(self):
        program = product_program()
        with self.assertRaises(DeliveryLadderFormatError):
            ladder(program=program, steps=steps(program)[:-1])

    def test_a_ladder_refuses_an_extra_step_deliverable(self):
        program = product_program()
        duplicate = step(program.modules[0].signature_step)
        with self.assertRaises(DeliveryLadderFormatError):
            ladder(program=program, steps=steps(program) + (duplicate,))

    def test_a_ladder_refuses_a_step_the_program_does_not_name(self):
        program = product_program()
        broken = list(steps(program))
        broken[0] = step("Unknown")
        with self.assertRaises(DeliveryLadderDependencyError):
            ladder(program=program, steps=tuple(broken))

    def test_a_ladder_refuses_a_blank_deliverable(self):
        with self.assertRaises(InvalidDeliveryLadderError):
            step("Diagnose", deliverable="  ")

    def test_a_ladder_requires_a_typed_step(self):
        program = product_program()
        broken = list(steps(program))
        broken[0] = "Diagnose"
        with self.assertRaises(InvalidDeliveryLadderError):
            ladder(program=program, steps=tuple(broken))


class RoadmapAuditTests(unittest.TestCase):
    def test_a_ladder_requires_a_90_day_roadmap_audit(self):
        self.assertEqual(90, ROADMAP_AUDIT_DAYS)
        self.assertEqual(
            CREATED + timedelta(days=ROADMAP_AUDIT_DAYS), ladder().next_audit_due
        )

    def test_a_ladder_refuses_an_audit_off_the_90_day_cadence(self):
        with self.assertRaises(DeliveryAuditCadenceError):
            audit(next_audit_on=CREATED + timedelta(days=30))

    def test_a_ladder_refuses_an_audit_before_creation(self):
        with self.assertRaises(DeliveryAuditOrderError):
            ladder(
                audits=(
                    audit(
                        audited_on=CREATED - timedelta(days=1),
                        next_audit_on=CREATED - timedelta(days=1)
                        + timedelta(days=ROADMAP_AUDIT_DAYS),
                    ),
                )
            )

    def test_a_ladder_refuses_out_of_order_audits(self):
        first = audit()
        second = audit(
            audited_on=first.next_audit_on - timedelta(days=1),
            next_audit_on=first.next_audit_on
            - timedelta(days=1)
            + timedelta(days=ROADMAP_AUDIT_DAYS),
        )
        with self.assertRaises(DeliveryAuditOrderError):
            ladder(audits=(first, second))

    def test_a_ladder_requires_at_least_one_audit(self):
        with self.assertRaises(InvalidDeliveryLadderError):
            ladder(audits=())

    def test_a_ladder_requires_a_typed_audit(self):
        with self.assertRaises(InvalidDeliveryLadderError):
            ladder(audits=("audit",))


class DeliveryGoalTests(unittest.TestCase):
    def test_a_ladder_requires_at_least_one_goal(self):
        with self.assertRaises(InvalidDeliveryLadderError):
            ladder(goals=())

    def test_a_ladder_refuses_a_blank_goal(self):
        with self.assertRaises(InvalidDeliveryLadderError):
            ladder(goals=(goal(name="  "),))

    def test_a_ladder_requires_a_typed_goal(self):
        with self.assertRaises(InvalidDeliveryLadderError):
            ladder(goals=("goal",))


class AscensionOfferTests(unittest.TestCase):
    def test_a_ladder_requires_at_least_one_ascension_offer(self):
        with self.assertRaises(InvalidDeliveryLadderError):
            ladder(ascension_offers=())

    def test_a_ladder_refuses_an_ascension_offer_for_an_unknown_step(self):
        with self.assertRaises(DeliveryLadderDependencyError):
            ladder(ascension_offers=(offer("Unknown"),))

    def test_a_ladder_refuses_duplicate_ascension_offers_for_a_step(self):
        program = product_program()
        name = program.modules[0].signature_step
        with self.assertRaises(DeliveryLadderFormatError):
            ladder(ascension_offers=(offer(name), offer(name)))

    def test_a_ladder_requires_a_typed_ascension_offer(self):
        with self.assertRaises(InvalidDeliveryLadderError):
            ladder(ascension_offers=("offer",))


class DeliveryLadderGroundingTests(unittest.TestCase):
    def test_a_ladder_grounds_on_a_same_tenant_program(self):
        self.assertEqual("program-3f", ladder().program.program_id)

    def test_a_ladder_refuses_a_program_from_another_tenant(self):
        foreign = product_program(solution=signature_solution(OTHER_TENANT))
        with self.assertRaises(DeliveryLadderTenantBoundaryError):
            ladder(program=foreign, tenant_id=TENANT)

    def test_a_ladder_requires_a_typed_program(self):
        with self.assertRaises(DeliveryLadderDependencyError):
            ladder(program="program")

    def test_a_ladder_requires_identity(self):
        for field in ("ladder_id", "tenant_id", "owner"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidDeliveryLadderError):
                    ladder(**{field: "  "})

    def test_a_ladder_requires_a_creation_date(self):
        with self.assertRaises(InvalidDeliveryLadderError):
            ladder(created_on="2026-10-02")


class DeliveryGateTests(unittest.TestCase):
    def test_close_accepts_results_that_meet_every_goal(self):
        built = ladder(goals=(goal(), goal(name="booked calls")))
        built.close(
            results=(
                result("qualified leads"),
                result("booked calls"),
            )
        )

    def test_close_refuses_when_a_goal_is_unmet(self):
        built = ladder()
        with self.assertRaises(DeliveryGateError):
            built.close(results=(result("qualified leads", met=False),))

    def test_close_refuses_when_a_goal_result_is_missing(self):
        built = ladder(goals=(goal(), goal(name="booked calls")))
        with self.assertRaises(DeliveryGateError):
            built.close(results=(result("qualified leads"),))

    def test_close_refuses_a_result_for_an_unknown_goal(self):
        built = ladder()
        with self.assertRaises(DeliveryGateError):
            built.close(results=(result("unknown goal"),))


class DeliveryLadderShapeTests(unittest.TestCase):
    def test_a_ladder_is_a_plan_not_an_observation(self):
        built = ladder()
        self.assertTrue(built.is_plan)
        with self.assertRaises(DeliveryLadderObservationError):
            built.as_observation(claim_id="claim-1")

    def test_a_ladder_is_frozen(self):
        built = ladder()
        with self.assertRaises(FrozenInstanceError):
            built.owner = "someone-else"

    def test_a_ladder_reports_its_canon_reference_and_post_launch_stage(self):
        built = ladder()
        self.assertEqual(DELIVERY_CANON_REFERENCE, built.canon_reference)
        self.assertTrue(built.is_post_launch)

    def test_a_ladder_reports_its_latest_audit(self):
        built = ladder()
        self.assertEqual(built.audits[-1], built.latest_audit)


if __name__ == "__main__":
    unittest.main()
