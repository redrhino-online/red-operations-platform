"""Behavioral tests for the stage 4 Signature Solution rule (pure domain, Method).

Rules under test come from SPEC.md section 4, stage 4 "Package IP" and its "IP
Architecture Locked" checkpoint: the required asset package is the transformation
map, process inventory, three phases, nine steps, named stages, starting and
final states, stage inputs/actions/outputs, narrative and visual. The checkpoint
requires that "the transformation is coherent and explainable without listing
every tactic". The canonical template seeds exactly `three-phases` and
`nine-steps` (Governance `templates.py`), so a structure that is not the three
phase, nine step shape is trying to list every tactic rather than describe the
transformation. Continuity is the coherence rule: each named stage must begin
where the previous stage ended, and the declared starting and final states must
be the ends of that single chain.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.method.domain.entities import SignatureSolution
from redops.contexts.method.domain.errors import (
    InvalidSignatureSolutionError,
    InvalidSignatureStepError,
    InvalidTransformationPhaseError,
)
from redops.contexts.method.domain.value_objects import (
    SignatureStep,
    TransformationPhase,
)

TENANT = "client-3f"


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


class SignatureStepTests(unittest.TestCase):
    def test_a_step_records_its_name_states_and_inputs_actions_outputs(self):
        candidate = step()

        self.assertEqual("Diagnose", candidate.name)
        self.assertEqual("chaotic", candidate.starting_state)
        self.assertEqual("diagnosed", candidate.final_state)
        self.assertEqual(("intake notes",), candidate.inputs)
        self.assertEqual(("facilitate the stage",), candidate.actions)
        self.assertEqual(("stage artifact",), candidate.outputs)

    def test_a_step_missing_any_structural_field_is_rejected(self):
        for override in (
            {"step_id": ""},
            {"name": "  "},
            {"tenant_id": ""},
            {"starting_state": ""},
            {"final_state": "  "},
            {"inputs": ()},
            {"actions": ("  ",)},
            {"outputs": ()},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidSignatureStepError):
                    step(**override)

    def test_a_step_that_does_not_move_the_client_is_rejected(self):
        with self.assertRaises(InvalidSignatureStepError):
            step(starting_state="chaotic", final_state="chaotic")

    def test_a_step_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            step().name = "tampered"


class TransformationPhaseTests(unittest.TestCase):
    def test_a_phase_records_its_name_and_steps(self):
        candidate = phase()

        self.assertEqual("Diagnose and Position", candidate.name)
        self.assertEqual(1, len(candidate.steps))

    def test_a_phase_without_a_step_is_rejected(self):
        with self.assertRaises(InvalidTransformationPhaseError):
            phase(steps=())

    def test_a_phase_without_an_identity_or_name_is_rejected(self):
        for override in ({"phase_id": ""}, {"name": "  "}, {"tenant_id": ""}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidTransformationPhaseError):
                    phase(**override)

    def test_a_phase_cannot_mix_steps_from_another_tenant(self):
        with self.assertRaises(InvalidTransformationPhaseError):
            phase(steps=(step(tenant_id="client-other"),))

    def test_a_phase_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            phase().name = "tampered"


class SignatureSolutionCheckpointTests(unittest.TestCase):
    def test_a_solution_records_the_full_stage_4_asset_package(self):
        solution = signature_solution()

        self.assertEqual("from chaotic delivery to a launched campaign", solution.transformation_map)
        self.assertEqual(5, len(solution.process_inventory))
        self.assertEqual(3, len(solution.phases))
        self.assertEqual(9, solution.step_count)
        self.assertEqual("chaotic", solution.starting_state)
        self.assertEqual("launched", solution.final_state)
        self.assertTrue(solution.narrative)
        self.assertTrue(solution.visual)

    def test_a_solution_requires_exactly_three_phases(self):
        phases = nine_step_phases()
        candidates = (
            phases[:2],
            phases
            + (phase(phase_id="phase-4", name="Extra", steps=(step(step_id="step-10", starting_state="launched", final_state="overextended"),)),),
        )
        for candidate in candidates:
            with self.subTest(phase_count=len(candidate)):
                with self.assertRaises(InvalidSignatureSolutionError):
                    signature_solution(phases=candidate)

    def test_a_solution_requires_exactly_nine_steps(self):
        phases = nine_step_phases()
        too_few = phases[:2] + (
            phase(phase_id="phase-3", name="Produce", steps=(step(step_id="step-7", name="Produce", starting_state="messaged", final_state="launched"),)),
        )
        too_many = phases[:2] + (
            phase(
                phase_id="phase-3",
                name="Produce and Launch",
                steps=phases[2].steps
                + (step(step_id="step-10", name="Extra", starting_state="launched", final_state="overextended"),),
            ),
        )
        for candidate in (too_few, too_many):
            with self.subTest(step_count=sum(len(p.steps) for p in candidate)):
                with self.assertRaises(InvalidSignatureSolutionError):
                    signature_solution(phases=candidate)

    def test_a_solution_with_a_discontinuous_step_is_rejected(self):
        phases = nine_step_phases()
        broken = step(step_id="step-3", name="Model", starting_state="somewhere-else", final_state="modeled")
        candidate = (
            phase(phase_id="phase-1", name="Diagnose and Position", steps=(phases[0].steps[0], phases[0].steps[1], broken)),
            phases[1],
            phases[2],
        )

        with self.assertRaises(InvalidSignatureSolutionError):
            signature_solution(phases=candidate)

    def test_a_solution_whose_declared_ends_do_not_match_the_chain_is_rejected(self):
        with self.assertRaises(InvalidSignatureSolutionError):
            signature_solution(starting_state="not-chaotic")
        with self.assertRaises(InvalidSignatureSolutionError):
            signature_solution(final_state="not-launched")

    def test_a_solution_missing_its_narrative_visual_or_inventory_is_rejected(self):
        for override in (
            {"transformation_map": ""},
            {"process_inventory": ()},
            {"narrative": "  "},
            {"visual": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidSignatureSolutionError):
                    signature_solution(**override)

    def test_a_solution_cannot_mix_phases_from_another_tenant(self):
        phases = nine_step_phases()
        foreign = phase(
            phase_id="phase-foreign",
            tenant_id="client-other",
            name="Foreign",
            steps=(step(step_id="fs", name="Foreign", starting_state="chaotic", final_state="diagnosed", tenant_id="client-other"),),
        )
        candidate = (phases[0], foreign, phases[2])

        with self.assertRaises(InvalidSignatureSolutionError):
            signature_solution(phases=candidate)

    def test_a_solution_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            signature_solution().narrative = "tampered"


if __name__ == "__main__":
    unittest.main()
