"""Behavioral tests for assembling a stage gate from real assets (Governance).

Rules under test come from SPEC.md sections 3, 4 and 11:

- A GateDecision pins the exact required asset versions and a passing gate pins
  the exact evidence and intended downstream use.
- A stage is complete only when its required assets exist and pass a defined
  checkpoint; the checkpoint is a production gate, not activity.
- Every child resource belongs to exactly one client, so gate evidence may only
  pin assets owned by the workspace tenant.

The canonical required asset package is owned by the pipeline template, not by
the caller. The assembler turns real ``StageAssetVersion``s into the exact
version-per-kind mapping the gate factory consumes, so an incomplete package, an
unexpected kind, an ambiguous second version of one kind, or a cross-tenant asset
is refused rather than pinned. These tests never invent a named client approver.
"""

import unittest

from redops.contexts.governance.domain.entities import StageGate
from redops.contexts.governance.domain.errors import (
    AmbiguousAssetPackageError,
    AssetPackageMismatchError,
    CrossTenantAssetError,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import StageAssetVersion

TENANT = "client-3f"
OTHER_TENANT = "client-other"


def stage_asset(kind: str, *, version: int = 1, tenant_id: str = TENANT, asset_id: str | None = None):
    return StageAssetVersion(
        asset_id=asset_id or f"intake-3f-{kind}",
        tenant_id=tenant_id,
        kind=kind,
        version=version,
    )


def complete_stage_zero_assets(version: int = 1):
    template = stage_zero_to_ten_template()
    return tuple(
        stage_asset(kind, version=version)
        for kind in sorted(template.required_asset_kinds(0))
    )


class StageAssetPackageAssemblyTests(unittest.TestCase):
    def test_a_complete_tenant_package_builds_a_canonical_stage_gate(self):
        template = stage_zero_to_ten_template()

        gate = StageGate.from_assets(
            template, 0, tenant_id=TENANT, assets=complete_stage_zero_assets()
        )

        self.assertEqual(
            template.required_asset_kinds(0),
            {ref.asset_id for ref in gate.required_assets},
        )
        self.assertEqual(
            frozenset({1}), {ref.version for ref in gate.required_assets}
        )

    def test_the_gate_pins_the_exact_version_each_asset_carries(self):
        template = stage_zero_to_ten_template()
        assets = tuple(
            stage_asset(asset.kind, version=3, asset_id=asset.asset_id)
            for asset in complete_stage_zero_assets()
        )

        gate = StageGate.from_assets(
            template, 0, tenant_id=TENANT, assets=assets
        )

        self.assertEqual(
            frozenset({3}), {ref.version for ref in gate.required_assets}
        )

    def test_a_missing_canonical_kind_is_refused(self):
        template = stage_zero_to_ten_template()
        assets = complete_stage_zero_assets()[:-1]

        with self.assertRaises(AssetPackageMismatchError):
            StageGate.from_assets(template, 0, tenant_id=TENANT, assets=assets)

    def test_an_extra_non_canonical_kind_is_refused(self):
        template = stage_zero_to_ten_template()
        assets = complete_stage_zero_assets() + (stage_asset("rogue-asset"),)

        with self.assertRaises(AssetPackageMismatchError):
            StageGate.from_assets(template, 0, tenant_id=TENANT, assets=assets)

    def test_two_versions_of_one_kind_are_an_ambiguous_package(self):
        template = stage_zero_to_ten_template()
        assets = complete_stage_zero_assets() + (
            stage_asset("client-record", version=2, asset_id="intake-3f-client-record-v2"),
        )

        with self.assertRaises(AmbiguousAssetPackageError):
            StageGate.from_assets(template, 0, tenant_id=TENANT, assets=assets)

    def test_a_cross_tenant_asset_is_refused(self):
        template = stage_zero_to_ten_template()
        assets = complete_stage_zero_assets()[:-1] + (
            stage_asset("launch-definition", tenant_id=OTHER_TENANT),
        )

        with self.assertRaises(CrossTenantAssetError):
            StageGate.from_assets(template, 0, tenant_id=TENANT, assets=assets)

    def test_an_unknown_stage_is_refused(self):
        from redops.contexts.governance.domain.errors import UnknownStageError

        with self.assertRaises(UnknownStageError):
            StageGate.from_assets(
                stage_zero_to_ten_template(),
                99,
                tenant_id=TENANT,
                assets=complete_stage_zero_assets(),
            )


if __name__ == "__main__":
    unittest.main()
