"""Behavioral tests for building a StageGate from the canonical template.

Rules under test come from SPEC.md section 4: the 0-10 pipeline is a gated
dependency graph, a gate pins the exact required asset versions and intended
downstream use, and a failed or missing prerequisite blocks dependent
authorization. Gate evidence must not be self-declared at the application
boundary, so a gate built from the template takes its dependencies, template
version and required asset package from the template rather than from the
caller (SPEC.md sections 3 and 4).
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import ApprovalRequest, StageGate
from redops.contexts.governance.domain.errors import (
    AssetPackageMismatchError,
    UnknownStageError,
)
from redops.contexts.governance.domain.policies import GateIntegrityPolicy
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateState,
)

VERSION = "2026.1"
TODAY = date(2026, 10, 2)


def approve(gate: StageGate) -> None:
    for asset in gate.required_assets:
        request = ApprovalRequest(
            asset=asset,
            scope="stage-downstream",
            requested_by="specialist-1",
            approver="client-approver-1",
        )
        request.approve(actor="client-approver-1", on=TODAY)
        gate.record_asset_approval(request)


class StageGateFromTemplateTests(unittest.TestCase):
    def setUp(self):
        self.template = stage_zero_to_ten_template(VERSION)

    def versions_for(self, stage_number, version=1):
        return {
            kind: version
            for kind in self.template.required_asset_kinds(stage_number)
        }

    def test_factory_pins_template_version_and_canonical_dependencies(self):
        gate = StageGate.from_template(self.template, 7, self.versions_for(7))

        self.assertEqual(VERSION, gate.template_version)
        self.assertEqual(frozenset({6}), gate.dependencies)
        self.assertEqual(7, gate.stage_number)

    def test_factory_builds_the_full_required_asset_package(self):
        gate = StageGate.from_template(self.template, 7, self.versions_for(7))

        declared_kinds = {asset.asset_id for asset in gate.required_assets}
        self.assertEqual(self.template.required_asset_kinds(7), declared_kinds)

    def test_factory_pins_the_version_supplied_for_each_asset_kind(self):
        gate = StageGate.from_template(self.template, 7, self.versions_for(7, 3))

        self.assertIn(
            AssetVersionRef("authority-amplifier-script", 3), gate.required_assets
        )

    def test_factory_requires_a_version_for_every_required_kind(self):
        incomplete = self.versions_for(7)
        incomplete.pop("authority-amplifier-script")
        with self.assertRaises(AssetPackageMismatchError):
            StageGate.from_template(self.template, 7, incomplete)

    def test_factory_rejects_an_asset_kind_outside_the_canonical_package(self):
        with self.assertRaises(AssetPackageMismatchError):
            StageGate.from_template(
                self.template, 7, {**self.versions_for(7), "unrelated-asset": 1}
            )

    def test_factory_rejects_a_stage_absent_from_the_template(self):
        with self.assertRaises(UnknownStageError):
            StageGate.from_template(self.template, 99, {})

    def test_factory_gate_passes_canonical_gate_integrity(self):
        gate = StageGate.from_template(self.template, 7, self.versions_for(7))
        gate.state = GateState.APPROVED
        gate.proposed_by = "specialist-1"
        gate.approver = "client-approver-1"
        approve(gate)

        result = GateIntegrityPolicy().evaluate(
            gate, {6: GateState.APPROVED}, template=self.template
        )

        self.assertTrue(result.approvable, result.reasons)
        self.assertTrue(gate.authorizes_downstream())


if __name__ == "__main__":
    unittest.main()
