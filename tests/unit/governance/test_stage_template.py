"""Behavioral tests for the versioned stage 0-10 pipeline template.

Rules under test come from SPEC.md section 4 (the RED production engagement
table): the pipeline is a gated dependency graph, a stage is complete only when
its required assets exist and pass a defined checkpoint, and an unapproved or
omitted prerequisite must not authorize downstream work.

The template is the canonical source of the 0-10 stage dependencies, required
asset packages, checkpoint and accountable/approver roles. GateIntegrityPolicy
must reject a gate that omits a canonical prerequisite, under-declares the
required asset kinds, or pins a different template version.
"""

import unittest

from redops.contexts.governance.domain.errors import InvalidStageTemplateError
from redops.contexts.governance.domain.policies import GateIntegrityPolicy
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.entities import StageGate
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateState,
    StageDefinition,
    StageTemplate,
)

VERSION = "2026.1"


def definition(**overrides) -> StageDefinition:
    values = {
        "stage_number": 1,
        "name": "Diagnose",
        "required_asset_kinds": frozenset({"avatar-profile"}),
        "checkpoint": "Avatar Locked",
        "accountable_role": "discovery-diagnosis",
        "approver_role": "client-designated-authority",
        "dependencies": frozenset({0}),
    }
    values.update(overrides)
    return StageDefinition(**values)


class SeedTemplateTests(unittest.TestCase):
    def test_seeded_template_has_all_eleven_stages_in_order(self):
        template = stage_zero_to_ten_template(VERSION)

        self.assertEqual(VERSION, template.version)
        self.assertEqual(list(range(11)), [s.stage_number for s in template.stages])

    def test_every_stage_names_its_assets_checkpoint_and_roles(self):
        template = stage_zero_to_ten_template(VERSION)

        for stage in template.stages:
            self.assertTrue(stage.required_asset_kinds, stage.name)
            self.assertTrue(stage.checkpoint.strip(), stage.name)
            self.assertTrue(stage.accountable_role.strip(), stage.name)
            self.assertTrue(stage.approver_role.strip(), stage.name)

    def test_stages_depend_on_their_immediate_predecessor(self):
        template = stage_zero_to_ten_template(VERSION)

        self.assertEqual(frozenset(), template.dependencies_of(0))
        for stage_number in range(1, 11):
            self.assertEqual(
                frozenset({stage_number - 1}),
                template.dependencies_of(stage_number),
            )

    def test_stage_seven_requires_an_approved_script_asset(self):
        template = stage_zero_to_ten_template(VERSION)

        self.assertIn(
            "authority-amplifier-script",
            template.required_asset_kinds(7),
        )

    def test_definition_for_returns_none_for_an_unknown_stage(self):
        template = stage_zero_to_ten_template(VERSION)

        self.assertIsNone(template.definition_for(99))


class TemplateIntegrityTests(unittest.TestCase):
    def test_forward_dependency_is_rejected(self):
        with self.assertRaises(InvalidStageTemplateError):
            StageTemplate(
                version=VERSION,
                stages=(
                    definition(stage_number=0, dependencies=frozenset({1})),
                    definition(stage_number=1, dependencies=frozenset({0})),
                ),
            )

    def test_non_contiguous_stage_numbers_are_rejected(self):
        with self.assertRaises(InvalidStageTemplateError):
            StageTemplate(
                version=VERSION,
                stages=(
                    definition(stage_number=0, dependencies=frozenset()),
                    definition(stage_number=2, dependencies=frozenset({0})),
                ),
            )

    def test_empty_required_asset_package_is_rejected(self):
        with self.assertRaises(InvalidStageTemplateError):
            StageTemplate(
                version=VERSION,
                stages=(definition(stage_number=0, required_asset_kinds=frozenset(), dependencies=frozenset()),),
            )

    def test_blank_template_version_is_rejected(self):
        with self.assertRaises(InvalidStageTemplateError):
            StageTemplate(
                version="  ",
                stages=(definition(stage_number=0, dependencies=frozenset()),),
            )


class GateIntegrityAgainstTemplateTests(unittest.TestCase):
    def setUp(self):
        self.policy = GateIntegrityPolicy()
        self.template = stage_zero_to_ten_template(VERSION)

    def canonical_gate(self, stage_number: int, **overrides) -> StageGate:
        kinds = self.template.required_asset_kinds(stage_number)
        values = {
            "stage_number": stage_number,
            "template_version": VERSION,
            "required_assets": frozenset(
                AssetVersionRef(kind, 1) for kind in kinds
            ),
            "approved_assets": frozenset(
                AssetVersionRef(kind, 1) for kind in kinds
            ),
            "dependencies": self.template.dependencies_of(stage_number),
            "state": GateState.APPROVED,
            "proposed_by": "specialist-1",
            "approver": "client-approver-1",
        }
        values.update(overrides)
        return StageGate(**values)

    def test_canonical_gate_is_approvable(self):
        gate = self.canonical_gate(7)

        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, template=self.template
        )

        self.assertTrue(result.approvable, result.reasons)
        self.assertTrue(gate.authorizes_downstream())

    def test_gate_omitting_a_canonical_prerequisite_is_rejected(self):
        gate = self.canonical_gate(7, dependencies=frozenset())

        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, template=self.template
        )

        self.assertFalse(result.approvable)
        self.assertIn("6", " ".join(result.reasons))

    def test_gate_under_declaring_required_asset_kinds_is_rejected(self):
        gate = self.canonical_gate(7)
        gate.required_assets = frozenset({AssetVersionRef("aa-storyboard", 1)})
        gate.approved_assets = gate.required_assets

        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, template=self.template
        )

        self.assertFalse(result.approvable)
        self.assertIn("authority-amplifier-script", " ".join(result.reasons))

    def test_gate_pinned_to_a_different_template_version_is_rejected(self):
        gate = self.canonical_gate(7, template_version="2025.9")

        result = self.policy.evaluate(
            gate, {6: GateState.APPROVED}, template=self.template
        )

        self.assertFalse(result.approvable)
        self.assertIn("template version", " ".join(result.reasons))

    def test_gate_for_a_stage_absent_from_the_template_is_rejected(self):
        gate = self.canonical_gate(11)

        result = self.policy.evaluate(gate, {}, template=self.template)

        self.assertFalse(result.approvable)
        self.assertIn("11", " ".join(result.reasons))

    def test_policy_without_a_template_preserves_prior_behavior(self):
        gate = self.canonical_gate(7)

        result = self.policy.evaluate(gate, {6: GateState.APPROVED})

        self.assertTrue(result.approvable, result.reasons)


if __name__ == "__main__":
    unittest.main()
