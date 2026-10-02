"""Behavioral tests for the stage 5 delivery specification (pure domain, Commercial).

Rules under test come from SPEC.md section 4, stage 5 "Productize" and its
"Offer Locked" checkpoint: "every method step has an action, actor, deliverable,
timing and measure". The required asset package is the delivery model, duration,
modules, responsibilities, support cadence, stage deliverables, outcome measures,
pricing and payments, scope, guarantee decision, eligibility and offer stack. The
delivery specification is grounded on the locked stage 4 `SignatureSolution`
(SPEC.md section 4 stage 4; Phase 3 TDD example: "offer cannot become production
ready without approved method"), so a specification that leaves a method step
without a delivery, or that names a step the method does not have, cannot
represent an approvable offer. It is frozen: an approval pins an exact asset
version rather than mutating it (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    InvalidDeliverySpecificationError,
)

from ..method.fixtures import signature_solution
from .fixtures import delivery_specification, step_deliveries, step_delivery


class StepDeliveryTests(unittest.TestCase):
    def test_a_step_delivery_records_action_actor_deliverable_timing_and_measure(self):
        candidate = step_delivery("step-1")

        self.assertEqual("step-1", candidate.step_id)
        self.assertEqual("deliver step-1", candidate.action)
        self.assertEqual("red-specialist", candidate.actor)
        self.assertEqual("step-1 artifact", candidate.deliverable)
        self.assertEqual("within the engagement phase", candidate.timing)
        self.assertEqual("step-1 outcome observed", candidate.measure)

    def test_a_step_delivery_missing_any_checkpoint_field_is_rejected(self):
        for override in (
            {"step_id": ""},
            {"tenant_id": "  "},
            {"action": ""},
            {"actor": ""},
            {"deliverable": ""},
            {"timing": ""},
            {"measure": "  "},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidDeliverySpecificationError):
                    step_delivery(**override)

    def test_a_step_delivery_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            step_delivery("step-1").action = "tampered"


class DeliverySpecificationCheckpointTests(unittest.TestCase):
    def test_a_delivery_spec_records_the_full_stage_5_asset_package(self):
        spec = delivery_specification()

        self.assertEqual("done-with-you implementation", spec.delivery_model)
        self.assertEqual("12 weeks", spec.duration)
        self.assertEqual(3, len(spec.modules))
        self.assertEqual(2, len(spec.responsibilities))
        self.assertEqual("weekly working session", spec.support_cadence)
        self.assertEqual(9, len(spec.step_deliveries))
        self.assertEqual("USD 7,500 in three instalments", spec.pricing_payments)
        self.assertEqual("one campaign, one offer, one avatar", spec.scope)
        self.assertEqual("no guarantee in the pilot", spec.guarantee_decision)
        self.assertEqual("service businesses with a proven offer", spec.eligibility)
        self.assertEqual(2, len(spec.offer_stack))

    def test_every_method_step_has_exactly_one_delivery(self):
        spec = delivery_specification()

        solution_steps = {step.step_id for step in spec.signature_solution.steps}
        delivered = {row.step_id for row in spec.step_deliveries}

        self.assertEqual(solution_steps, delivered)

    def test_a_method_step_without_a_delivery_is_rejected(self):
        solution = signature_solution()
        incomplete = tuple(
            row for row in step_deliveries(solution) if row.step_id != "step-5"
        )

        with self.assertRaises(InvalidDeliverySpecificationError):
            delivery_specification(
                signature_solution=solution, step_deliveries=incomplete
            )

    def test_a_delivery_for_a_step_the_method_does_not_have_is_rejected(self):
        solution = signature_solution()
        extra = step_deliveries(solution) + (step_delivery("step-10"),)

        with self.assertRaises(InvalidDeliverySpecificationError):
            delivery_specification(
                signature_solution=solution, step_deliveries=extra
            )

    def test_a_duplicate_delivery_for_one_step_is_rejected(self):
        solution = signature_solution()
        rows = step_deliveries(solution) + (step_delivery("step-1"),)

        with self.assertRaises(InvalidDeliverySpecificationError):
            delivery_specification(signature_solution=solution, step_deliveries=rows)

    def test_a_delivery_spec_missing_its_asset_package_is_rejected(self):
        for override in (
            {"delivery_model": ""},
            {"duration": "  "},
            {"modules": ()},
            {"responsibilities": ()},
            {"support_cadence": ""},
            {"step_deliveries": ()},
            {"outcome_measures": ()},
            {"pricing_payments": ""},
            {"scope": ""},
            {"guarantee_decision": ""},
            {"eligibility": ""},
            {"offer_stack": ()},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidDeliverySpecificationError):
                    delivery_specification(**override)

    def test_a_delivery_spec_cannot_cover_another_tenants_method(self):
        with self.assertRaises(InvalidDeliverySpecificationError):
            delivery_specification(
                tenant_id="client-3f",
                signature_solution=signature_solution(tenant_id="client-other"),
                step_deliveries=step_deliveries(signature_solution(), "client-3f"),
            )

    def test_a_step_delivery_from_another_tenant_is_rejected(self):
        solution = signature_solution()
        rows = step_deliveries(solution)
        rows = rows[:-1] + (step_delivery("step-9", tenant_id="client-other"),)

        with self.assertRaises(InvalidDeliverySpecificationError):
            delivery_specification(signature_solution=solution, step_deliveries=rows)

    def test_a_delivery_spec_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            delivery_specification().scope = "tampered"


if __name__ == "__main__":
    unittest.main()
