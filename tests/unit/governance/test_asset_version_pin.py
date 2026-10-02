"""Behavioral tests for pinning a real stage asset's exact version (Governance).

Rules under test come from SPEC.md sections 3, 4 and 11:

- The GateDecision aggregate pins "required asset versions" and a passing gate
  pins "the exact evidence and intended downstream use".
- Stage completion requires the stage's required assets to exist and pass a
  defined checkpoint; an unapproved dependency cannot authorize production.
- Approval is version specific, and every tenant resource belongs to exactly one
  client.

A real stage asset produced by a bounded context has a unique id, one owning
tenant, one canonical template kind and a positive version. A governance gate
pins an ``AssetVersionRef`` keyed by the asset *kind*, so the asset's tenant must
be checked against the owning workspace before it can be evidence: a cross-tenant
asset must never be pinnable, and an asset with no positive version must never be
representable as an exact version. These tests never invent a named client
approver; the governance template owns the canonical kinds.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.governance.domain.entities import StageGate
from redops.contexts.governance.domain.errors import (
    CrossTenantAssetError,
    VersionlessAssetError,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    StageAssetVersion,
    duplicate_asset_kinds,
)

TENANT = "client-3f"
KIND = "client-record"


def stage_asset(**overrides) -> StageAssetVersion:
    values = {
        "asset_id": "intake-3f-client-record",
        "tenant_id": TENANT,
        "kind": KIND,
        "version": 1,
    }
    values.update(overrides)
    return StageAssetVersion(**values)


class StageAssetVersionPinningTests(unittest.TestCase):
    def test_a_real_asset_pins_its_exact_version_by_kind(self):
        self.assertEqual(
            AssetVersionRef(KIND, 1),
            stage_asset().pin(tenant_id=TENANT),
        )

    def test_an_asset_without_a_positive_version_is_rejected(self):
        for version in (0, -1, None):
            with self.subTest(version=version):
                with self.assertRaises(VersionlessAssetError):
                    stage_asset(version=version)

    def test_an_asset_without_identity_tenant_or_kind_is_rejected(self):
        for override in (
            {"asset_id": ""},
            {"tenant_id": "   "},
            {"kind": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(VersionlessAssetError):
                    stage_asset(**override)

    def test_pinning_a_cross_tenant_asset_is_refused(self):
        with self.assertRaises(CrossTenantAssetError):
            stage_asset(tenant_id="client-other").pin(tenant_id=TENANT)

    def test_the_pin_distinguishes_versions_of_the_same_kind(self):
        self.assertNotEqual(
            stage_asset(version=1).pin(tenant_id=TENANT),
            stage_asset(version=2).pin(tenant_id=TENANT),
        )

    def test_two_pinned_versions_of_one_kind_remain_ambiguous(self):
        refs = frozenset(
            {
                stage_asset(version=1).pin(tenant_id=TENANT),
                stage_asset(
                    asset_id="intake-3f-client-record-v2", version=2
                ).pin(tenant_id=TENANT),
            }
        )

        self.assertEqual(frozenset({KIND}), duplicate_asset_kinds(refs))

    def test_an_asset_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            stage_asset().version = 2


class StageAssetVersionGateIntegrationTests(unittest.TestCase):
    def test_pinned_stage_zero_assets_build_a_canonical_stage_gate(self):
        template = stage_zero_to_ten_template()
        assets = tuple(
            stage_asset(asset_id=f"intake-3f-{kind}", kind=kind, version=1)
            for kind in sorted(template.required_asset_kinds(0))
        )

        versions = {
            asset.kind: asset.pin(tenant_id=TENANT).version for asset in assets
        }
        gate = StageGate.from_template(template, 0, versions)

        self.assertEqual(
            template.required_asset_kinds(0),
            {ref.asset_id for ref in gate.required_assets},
        )


if __name__ == "__main__":
    unittest.main()
