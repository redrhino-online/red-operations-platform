"""Behavioral tests for the canon Product Matrix and product program.

Rules under test come from SPEC.md section 4, stage 5 "Productize" (the
"Offer Locked" checkpoint needs a delivery model, duration, pricing and a
deliverable for every method step) and section 12.3 (stage 5 is shaped by canon
files 11 and 12, the Perfect Product training and examples):

- Choose a delivery model from the product matrix, the canon's seven ways to
  monetize a signature solution: "the top seven business models that you can use
  to monetize your knowledge" (canon file 11), naming books and info products,
  training and memberships, software applications, live events and workshops,
  group coaching and consulting, one to one coaching and consulting, and the
  done for you agency. The canon recommends group consulting: "this is the model
  ... the best of both worlds" (canon files 11 and 12).
- Structure the program over six to twelve weeks: "how to deliver a world class
  6 to 12 week product" (canon file 12).
- Price on the outcome and value, never time and materials: "we're going to
  determine your program pricing based on outcomes and value to your clients,
  not time and materials" (canon file 11).
- Deliver on the Monday and Thursday cadence, one training and one coaching
  session a week: "the Monday Thursday method ... on Monday I'm going to offer a
  training and on Thursday I'm going to offer coaching" (canon file 12), so the
  program cannot pack more weekly modules than it has weeks.

The program is a stage 5 planning asset, not a new required gate kind (a
methodology-owner decision, SPEC.md section 12.5). It does not authorize
spending, publishing or client commitments (SPEC.md sections 4 and 9) and it is
never an observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    InvalidProductProgramError,
    ProductProgramDependencyError,
    ProductProgramObservationError,
    ProductProgramPricingError,
    ProductProgramTenantBoundaryError,
)
from redops.contexts.commercial.domain.value_objects import (
    MAXIMUM_PROGRAM_WEEKS,
    MINIMUM_PROGRAM_WEEKS,
    PRODUCT_MATRIX_MODELS,
    RECOMMENDED_PRODUCT_MODEL,
    ProductMatrixModel,
    ProductModule,
    ProductProgram,
    ProgramCadence,
    ProgramPricingBasis,
)

from .fixtures import TENANT
from ..method.fixtures import signature_solution
from redops.contexts.method.domain.entities import SignatureSolution


def product_module(step_name: str, position: int = 1, **overrides) -> ProductModule:
    values = {
        "module_id": f"module-{position}",
        "tenant_id": TENANT,
        "signature_step": step_name,
        "position": position,
        "outcome": f"the client reaches {step_name}",
        "deliverable": f"the {step_name} worksheet",
    }
    values.update(overrides)
    return ProductModule(**values)


def product_program(**overrides) -> ProductProgram:
    solution = overrides.pop("method", signature_solution())
    default_modules = (
        tuple(product_module(step.name, i + 1) for i, step in enumerate(solution.steps))
        if isinstance(solution, SignatureSolution)
        else ()
    )
    modules = overrides.pop("modules", default_modules)
    values = {
        "program_id": "program-3f",
        "tenant_id": TENANT,
        "owner": "red-offer-owner",
        "method": solution,
        "model": ProductMatrixModel.GROUP_CONSULTING,
        "pricing_basis": ProgramPricingBasis.OUTCOME_VALUE,
        "duration_weeks": 9,
        "cadence": ProgramCadence.MONDAY_TRAINING_THURSDAY_COACHING,
        "modules": modules,
    }
    values.update(overrides)
    return ProductProgram(**values)


class ProductMatrixTests(unittest.TestCase):
    def test_the_canon_names_seven_product_models(self) -> None:
        self.assertEqual(7, len(PRODUCT_MATRIX_MODELS))
        self.assertEqual(7, len(set(PRODUCT_MATRIX_MODELS)))

    def test_group_consulting_is_the_recommended_model(self) -> None:
        self.assertEqual(
            ProductMatrixModel.GROUP_CONSULTING, RECOMMENDED_PRODUCT_MODEL
        )

    def test_program_reports_its_model_recommendation(self) -> None:
        self.assertTrue(product_program().is_recommended_model)
        self.assertFalse(
            product_program(model=ProductMatrixModel.BOOKS_AND_INFO_PRODUCTS)
            .is_recommended_model
        )


class ProductModuleTests(unittest.TestCase):
    def test_module_is_frozen(self) -> None:
        module = product_module("Diagnose")
        with self.assertRaises(FrozenInstanceError):
            module.outcome = "changed"

    def test_module_requires_each_beat(self) -> None:
        for field in ("module_id", "tenant_id", "signature_step", "outcome", "deliverable"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidProductProgramError):
                    product_module("Diagnose", **{field: "  "})

    def test_module_requires_a_positive_integer_position(self) -> None:
        for position in (0, -1, "first", True):
            with self.subTest(position=position):
                with self.assertRaises(InvalidProductProgramError):
                    product_module("Diagnose", position=position)


class ProductProgramTests(unittest.TestCase):
    def test_program_is_frozen(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            product_program().owner = "changed"

    def test_program_requires_identity_and_owner(self) -> None:
        for field in ("program_id", "tenant_id", "owner"):
            with self.subTest(field=field):
                with self.assertRaises(InvalidProductProgramError):
                    product_program(**{field: "  "})

    def test_program_requires_a_typed_product_matrix_model(self) -> None:
        with self.assertRaises(InvalidProductProgramError):
            product_program(model="group_consulting")

    def test_program_requires_a_typed_pricing_basis(self) -> None:
        with self.assertRaises(InvalidProductProgramError):
            product_program(pricing_basis="outcome_value")

    def test_program_refuses_time_and_materials_pricing(self) -> None:
        with self.assertRaises(ProductProgramPricingError):
            product_program(pricing_basis=ProgramPricingBasis.TIME_AND_MATERIALS)

    def test_program_duration_is_six_to_twelve_weeks(self) -> None:
        solution = signature_solution()
        for weeks in (MINIMUM_PROGRAM_WEEKS, MAXIMUM_PROGRAM_WEEKS):
            with self.subTest(weeks=weeks):
                modules = tuple(
                    product_module(step.name, i + 1)
                    for i, step in enumerate(solution.steps[:weeks])
                )
                program = product_program(duration_weeks=weeks, modules=modules)
                self.assertEqual(weeks, program.duration_weeks)
        for weeks in (MINIMUM_PROGRAM_WEEKS - 1, MAXIMUM_PROGRAM_WEEKS + 1, "nine", True):
            with self.subTest(weeks=weeks):
                with self.assertRaises(InvalidProductProgramError):
                    product_program(duration_weeks=weeks, modules=(product_module("Diagnose"),))

    def test_program_requires_the_monday_thursday_cadence(self) -> None:
        with self.assertRaises(InvalidProductProgramError):
            product_program(cadence="monday_training")

    def test_program_cannot_pack_more_modules_than_weeks(self) -> None:
        solution = signature_solution()
        with self.assertRaises(InvalidProductProgramError):
            product_program(
                method=solution,
                duration_weeks=6,
                modules=tuple(
                    product_module(step.name, i + 1)
                    for i, step in enumerate(solution.steps)
                ),
            )

    def test_program_requires_a_typed_signature_solution(self) -> None:
        with self.assertRaises(ProductProgramDependencyError):
            product_program(method="solution-3f")

    def test_program_refuses_a_cross_tenant_method(self) -> None:
        with self.assertRaises(ProductProgramTenantBoundaryError):
            product_program(method=signature_solution(tenant_id="client-other"))

    def test_program_requires_at_least_one_module(self) -> None:
        with self.assertRaises(InvalidProductProgramError):
            product_program(modules=())

    def test_program_requires_typed_modules(self) -> None:
        with self.assertRaises(InvalidProductProgramError):
            product_program(modules=("module-1",))

    def test_program_refuses_a_cross_tenant_module(self) -> None:
        with self.assertRaises(ProductProgramTenantBoundaryError):
            product_program(
                modules=(product_module("Diagnose", 1, tenant_id="client-other"),)
            )

    def test_program_refuses_duplicate_module_ids(self) -> None:
        with self.assertRaises(InvalidProductProgramError):
            product_program(
                modules=(
                    product_module("Diagnose", 1, module_id="module-x"),
                    product_module("Position", 2, module_id="module-x"),
                )
            )

    def test_program_refuses_two_modules_for_one_step(self) -> None:
        with self.assertRaises(InvalidProductProgramError):
            product_program(
                modules=(
                    product_module("Diagnose", 1),
                    product_module("Diagnose", 2),
                )
            )

    def test_program_refuses_a_module_for_a_step_the_method_lacks(self) -> None:
        with self.assertRaises(ProductProgramDependencyError):
            product_program(modules=(product_module("Nonexistent Step", 1),))

    def test_program_reports_covered_and_missing_steps(self) -> None:
        program = product_program(modules=(product_module("Diagnose", 1),))
        self.assertEqual(("Diagnose",), program.covered_steps)
        self.assertIn("Position", program.missing_steps)
        self.assertFalse(program.is_complete)

    def test_complete_program_covers_every_step(self) -> None:
        program = product_program()
        self.assertTrue(program.is_complete)
        self.assertEqual((), program.missing_steps)

    def test_program_returns_the_module_for_a_step(self) -> None:
        module = product_program().module_for("Position")
        self.assertEqual("Position", module.signature_step)
        with self.assertRaises(ProductProgramDependencyError):
            product_program().module_for("Nonexistent Step")

    def test_program_is_a_plan(self) -> None:
        self.assertTrue(product_program().is_plan)

    def test_program_is_never_an_observation(self) -> None:
        with self.assertRaises(ProductProgramObservationError):
            product_program().as_observation(claim_id="claim-1")


if __name__ == "__main__":
    unittest.main()
