"""Behavioral tests for the canon thirteen transformations (Method domain).

Rules under test come from SPEC.md section 12.5 (the canon's thirteen
transformations -- "the overall shift, three phase shifts and nine step-level
from/to pairs, titled from the million dollar message" -- is a canon gap at stage
4) and section 12.3 (canon files 09 and 10 inform stage 4), shaped by the canon:

- Canon file 09 (Signature Solution Core Training): the whole solution "is one
  transformation ... your whole million dollar message is one transformation",
  then three mini transformations and "nine more. So that's 13", and "there
  should be a from and a to for each step in your signature solution. 13
  transformations".
- Canon file 10 (Signature Solution Examples): each shift is the move "from point
  A to point B", chosen around the target market's most important problem.

The set is a stage 4 method structure asset over the same-tenant `SignatureSolution`.
It is a planning decision, not a new required gate kind (a methodology-owner
decision, SPEC.md section 12.5), it does not authorize production, publishing or
traffic (SPEC.md sections 4 and 9) and it is never an observation (SPEC.md
section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.method.domain.entities import SignatureSolution
from redops.contexts.method.domain.errors import (
    InvalidTransformationError,
    TransformationCoverageError,
    TransformationDependencyError,
    TransformationMismatchError,
    TransformationObservationError,
    TransformationTenantBoundaryError,
)
from redops.contexts.method.domain.transformations import (
    PHASE_TRANSFORMATION_COUNT,
    STEP_TRANSFORMATION_COUNT,
    TRANSFORMATION_COUNT,
    ThirteenTransformations,
    Transformation,
    TransformationScope,
)
from redops.contexts.method.domain.value_objects import (
    SignatureStep,
    TransformationPhase,
)

TENANT = "client-3f"
MDM = "from zero to six figures in 90 days without a bigger ad budget"


def step(**overrides) -> SignatureStep:
    values = {
        "step_id": "step-1",
        "tenant_id": TENANT,
        "name": "Diagnose",
        "starting_state": "chaotic",
        "final_state": "diagnosed",
        "inputs": ("intake notes",),
        "actions": ("facilitate the stage",),
        "outputs": ("stage artifact",),
    }
    values.update(overrides)
    return SignatureStep(**values)


def phase(**overrides) -> TransformationPhase:
    values = {
        "phase_id": "phase-1",
        "tenant_id": TENANT,
        "name": "Diagnose and Position",
        "steps": (step(),),
    }
    values.update(overrides)
    return TransformationPhase(**values)


def nine_step_phases() -> tuple[TransformationPhase, ...]:
    return (
        phase(
            phase_id="phase-1",
            name="Diagnose and Position",
            steps=(
                step(step_id="step-1", name="Diagnose", starting_state="chaotic", final_state="diagnosed"),
                step(step_id="step-2", name="Position", starting_state="diagnosed", final_state="positioned"),
                step(step_id="step-3", name="Model", starting_state="positioned", final_state="modeled"),
            ),
        ),
        phase(
            phase_id="phase-2",
            name="Package and Productize",
            steps=(
                step(step_id="step-4", name="Package IP", starting_state="modeled", final_state="packaged"),
                step(step_id="step-5", name="Productize", starting_state="packaged", final_state="productized"),
                step(step_id="step-6", name="Message", starting_state="productized", final_state="messaged"),
            ),
        ),
        phase(
            phase_id="phase-3",
            name="Produce and Launch",
            steps=(
                step(step_id="step-7", name="Produce", starting_state="messaged", final_state="produced"),
                step(step_id="step-8", name="Integrate", starting_state="produced", final_state="integrated"),
                step(step_id="step-9", name="Launch", starting_state="integrated", final_state="launched"),
            ),
        ),
    )


def signature_solution(**overrides) -> SignatureSolution:
    values = {
        "solution_id": "solution-3f",
        "tenant_id": TENANT,
        "transformation_map": "from chaotic delivery to a launched campaign",
        "process_inventory": ("diagnose", "position", "model", "package", "productize"),
        "phases": nine_step_phases(),
        "starting_state": "chaotic",
        "final_state": "launched",
        "narrative": "the client moves from unpredictable work to a repeatable growth system",
        "visual": "asset://transformations/3f-map.png",
    }
    values.update(overrides)
    return SignatureSolution(**values)


def shift(
    scope: TransformationScope,
    scope_id: str,
    from_state: str,
    to_state: str,
    **overrides,
) -> Transformation:
    values = {
        "transformation_id": f"shift-{scope_id}",
        "tenant_id": TENANT,
        "scope": scope,
        "scope_id": scope_id,
        "title": "a relevant shift",
        "from_state": from_state,
        "to_state": to_state,
    }
    values.update(overrides)
    return Transformation(**values)


def overall_shift(**overrides) -> Transformation:
    values = {
        "scope_id": "solution-3f",
        "from_state": "chaotic",
        "to_state": "launched",
        "title": MDM,
    }
    values.update(overrides)
    return shift(TransformationScope.OVERALL, **values)


def phase_shifts() -> tuple[Transformation, ...]:
    return (
        shift(TransformationScope.PHASE, "phase-1", "chaotic", "modeled", title="foundation"),
        shift(TransformationScope.PHASE, "phase-2", "modeled", "messaged", title="funnel"),
        shift(TransformationScope.PHASE, "phase-3", "messaged", "launched", title="floodgates"),
    )


_STEP_STATES = (
    ("step-1", "chaotic", "diagnosed"),
    ("step-2", "diagnosed", "positioned"),
    ("step-3", "positioned", "modeled"),
    ("step-4", "modeled", "packaged"),
    ("step-5", "packaged", "productized"),
    ("step-6", "productized", "messaged"),
    ("step-7", "messaged", "produced"),
    ("step-8", "produced", "integrated"),
    ("step-9", "integrated", "launched"),
)


def step_shifts() -> tuple[Transformation, ...]:
    return tuple(
        shift(TransformationScope.STEP, step_id, from_state, to_state, title=f"shift {step_id}")
        for step_id, from_state, to_state in _STEP_STATES
    )


def thirteen(**overrides) -> ThirteenTransformations:
    values = {
        "transformations_id": "transformations-3f",
        "tenant_id": TENANT,
        "million_dollar_message": MDM,
        "solution": signature_solution(),
        "overall": overall_shift(),
        "phase_transformations": phase_shifts(),
        "step_transformations": step_shifts(),
    }
    values.update(overrides)
    return ThirteenTransformations(**values)


class TransformationTests(unittest.TestCase):
    def test_a_shift_records_its_scope_title_and_from_to_states(self):
        candidate = shift(TransformationScope.STEP, "step-1", "chaotic", "diagnosed")

        self.assertIs(TransformationScope.STEP, candidate.scope)
        self.assertEqual("step-1", candidate.scope_id)
        self.assertEqual("chaotic", candidate.from_state)
        self.assertEqual("diagnosed", candidate.to_state)

    def test_a_shift_missing_any_field_is_rejected(self):
        base = {
            "transformation_id": "shift-1",
            "tenant_id": TENANT,
            "scope": TransformationScope.STEP,
            "scope_id": "step-1",
            "title": "a relevant shift",
            "from_state": "chaotic",
            "to_state": "diagnosed",
        }
        for override in (
            {"transformation_id": ""},
            {"tenant_id": "  "},
            {"scope_id": ""},
            {"title": "  "},
            {"from_state": ""},
            {"to_state": " "},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidTransformationError):
                    Transformation(**{**base, **override})

    def test_a_shift_that_does_not_move_the_client_is_rejected(self):
        with self.assertRaises(InvalidTransformationError):
            shift(TransformationScope.STEP, "step-1", "chaotic", "chaotic")

    def test_a_shift_must_name_one_of_the_canon_scopes(self):
        with self.assertRaises(InvalidTransformationError):
            shift("phase", "phase-1", "chaotic", "modeled")

    def test_a_shift_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            shift(TransformationScope.STEP, "step-1", "chaotic", "diagnosed").title = "tampered"


class ThirteenTransformationsShapeTests(unittest.TestCase):
    def test_the_set_records_the_canon_thirteen_shifts(self):
        candidate = thirteen()

        self.assertEqual(TRANSFORMATION_COUNT, candidate.count)
        self.assertEqual(PHASE_TRANSFORMATION_COUNT, len(candidate.phase_transformations))
        self.assertEqual(STEP_TRANSFORMATION_COUNT, len(candidate.step_transformations))
        self.assertEqual(13, len(candidate.all_transformations))

    def test_the_overall_shift_is_titled_with_the_million_dollar_message(self):
        candidate = thirteen()

        self.assertEqual(MDM, candidate.overall.title)
        self.assertEqual("solution-3f", candidate.overall.scope_id)
        self.assertEqual("chaotic", candidate.overall.from_state)
        self.assertEqual("launched", candidate.overall.to_state)

    def test_each_phase_shift_moves_between_that_phase_start_and_final_state(self):
        candidate = thirteen()
        by_id = {s.scope_id: s for s in candidate.phase_transformations}

        self.assertEqual(("chaotic", "modeled"), (by_id["phase-1"].from_state, by_id["phase-1"].to_state))
        self.assertEqual(("modeled", "messaged"), (by_id["phase-2"].from_state, by_id["phase-2"].to_state))
        self.assertEqual(("messaged", "launched"), (by_id["phase-3"].from_state, by_id["phase-3"].to_state))

    def test_each_step_shift_moves_between_that_step_start_and_final_state(self):
        candidate = thirteen()
        by_id = {s.scope_id: s for s in candidate.step_transformations}

        for step_id, from_state, to_state in _STEP_STATES:
            with self.subTest(step=step_id):
                self.assertEqual((from_state, to_state), (by_id[step_id].from_state, by_id[step_id].to_state))

    def test_the_set_exposes_each_shift_by_scope_id(self):
        candidate = thirteen()

        self.assertEqual("phase-2", candidate.transformation_for("phase-2").scope_id)
        self.assertEqual("step-9", candidate.transformation_for("step-9").scope_id)
        self.assertEqual("solution-3f", candidate.transformation_for("solution-3f").scope_id)
        with self.assertRaises(TransformationCoverageError):
            candidate.transformation_for("missing")

    def test_the_set_is_a_method_structure_and_is_immutable(self):
        candidate = thirteen()

        self.assertTrue(candidate.is_method_structure)
        with self.assertRaises(FrozenInstanceError):
            candidate.million_dollar_message = "tampered"

    def test_the_set_refuses_to_be_recorded_as_an_observation(self):
        with self.assertRaises(TransformationObservationError):
            thirteen().as_observation(claim_id="obs-1")


class ThirteenTransformationsDependencyTests(unittest.TestCase):
    def test_the_set_requires_identity_tenant_and_a_titled_overall_shift(self):
        for override in (
            {"transformations_id": ""},
            {"tenant_id": "  "},
            {"million_dollar_message": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidTransformationError):
                    thirteen(**override)

    def test_the_set_must_be_grounded_on_a_typed_stage_4_solution(self):
        with self.assertRaises(TransformationDependencyError):
            thirteen(solution="solution-3f")

    def test_the_set_cannot_describe_another_tenant_solution(self):
        with self.assertRaises(TransformationTenantBoundaryError):
            thirteen(tenant_id="client-other")

    def test_a_shift_from_another_tenant_is_rejected(self):
        foreign = shift(
            TransformationScope.PHASE,
            "phase-1",
            "chaotic",
            "modeled",
            tenant_id="client-other",
        )
        phases = (foreign,) + phase_shifts()[1:]

        with self.assertRaises(TransformationTenantBoundaryError):
            thirteen(phase_transformations=phases)


class ShiftTypingTests(unittest.TestCase):
    def test_a_non_typed_shift_is_rejected(self):
        phases = ("not-a-shift",) + phase_shifts()[1:]

        with self.assertRaises(InvalidTransformationError):
            thirteen(phase_transformations=phases)


class OverallShiftTests(unittest.TestCase):
    def test_the_overall_shift_must_use_the_overall_scope(self):
        bad = shift(TransformationScope.STEP, "solution-3f", "chaotic", "launched", title=MDM)

        with self.assertRaises(TransformationCoverageError):
            thirteen(overall=bad)

    def test_the_overall_shift_must_describe_this_solution(self):
        bad = overall_shift(scope_id="solution-other")

        with self.assertRaises(TransformationCoverageError):
            thirteen(overall=bad)

    def test_the_overall_shift_title_must_be_the_million_dollar_message(self):
        with self.assertRaises(TransformationMismatchError):
            thirteen(overall=overall_shift(title="a generic roadmap"))

    def test_the_overall_shift_states_must_be_the_solution_ends(self):
        with self.assertRaises(TransformationMismatchError):
            thirteen(overall=overall_shift(from_state="somewhere-else"))
        with self.assertRaises(TransformationMismatchError):
            thirteen(overall=overall_shift(to_state="nowhere"))


class PhaseCoverageTests(unittest.TestCase):
    def test_the_set_requires_exactly_three_phase_shifts(self):
        phases = phase_shifts()
        with self.assertRaises(TransformationCoverageError):
            thirteen(phase_transformations=phases[:2])
        with self.assertRaises(TransformationCoverageError):
            thirteen(phase_transformations=phases + (
                shift(TransformationScope.PHASE, "phase-4", "launched", "overextended"),
            ))

    def test_a_duplicated_phase_shift_leaves_a_phase_uncovered(self):
        phases = phase_shifts()
        duplicate = shift(TransformationScope.PHASE, "phase-1", "chaotic", "modeled")
        candidate = (phases[0], duplicate, phases[1])

        with self.assertRaises(TransformationCoverageError):
            thirteen(phase_transformations=candidate)

    def test_a_phase_shift_naming_a_non_phase_is_rejected(self):
        phases = phase_shifts()
        unknown = shift(TransformationScope.PHASE, "step-1", "chaotic", "diagnosed")
        candidate = (phases[0], unknown, phases[2])

        with self.assertRaises(TransformationCoverageError):
            thirteen(phase_transformations=candidate)

    def test_a_phase_shift_must_use_the_phase_scope(self):
        phases = phase_shifts()
        wrong = shift(TransformationScope.STEP, "phase-1", "chaotic", "modeled")
        candidate = (phases[0], wrong, phases[2])

        with self.assertRaises(TransformationCoverageError):
            thirteen(phase_transformations=candidate)

    def test_a_phase_shift_state_that_does_not_match_the_phase_is_rejected(self):
        phases = phase_shifts()
        broken = shift(TransformationScope.PHASE, "phase-1", "chaotic", "overextended")
        candidate = (broken, phases[1], phases[2])

        with self.assertRaises(TransformationMismatchError):
            thirteen(phase_transformations=candidate)


class StepCoverageTests(unittest.TestCase):
    def test_the_set_requires_exactly_nine_step_shifts(self):
        steps = step_shifts()
        with self.assertRaises(TransformationCoverageError):
            thirteen(step_transformations=steps[:-1])
        with self.assertRaises(TransformationCoverageError):
            thirteen(step_transformations=steps + (
                shift(TransformationScope.STEP, "step-10", "launched", "overextended"),
            ))

    def test_a_duplicated_step_shift_leaves_a_step_uncovered(self):
        steps = step_shifts()
        candidate = (steps[0], steps[0]) + steps[2:]

        with self.assertRaises(TransformationCoverageError):
            thirteen(step_transformations=candidate)

    def test_a_step_shift_naming_a_non_step_is_rejected(self):
        steps = step_shifts()
        unknown = shift(TransformationScope.STEP, "phase-1", "chaotic", "modeled")
        candidate = (unknown,) + steps[1:]

        with self.assertRaises(TransformationCoverageError):
            thirteen(step_transformations=candidate)

    def test_a_step_shift_must_use_the_step_scope(self):
        steps = step_shifts()
        wrong = shift(TransformationScope.PHASE, "step-1", "chaotic", "diagnosed")
        candidate = (wrong,) + steps[1:]

        with self.assertRaises(TransformationCoverageError):
            thirteen(step_transformations=candidate)

    def test_a_step_shift_state_that_does_not_match_the_step_is_rejected(self):
        steps = step_shifts()
        broken = shift(TransformationScope.STEP, "step-1", "chaotic", "overextended")
        candidate = (broken,) + steps[1:]

        with self.assertRaises(TransformationMismatchError):
            thirteen(step_transformations=candidate)


if __name__ == "__main__":
    unittest.main()
