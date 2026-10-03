"""Behavioral tests for the stage 5 "Offer Locked" asset package.

Rules under test come from SPEC.md sections 3, 4 and 12.3. Stage 5 "Productize"
requires the asset package "delivery model, duration, modules, responsibilities,
support cadence, stage deliverables, outcome measures, pricing and payments,
scope, guarantee decision, eligibility and offer stack", and its checkpoint is
"Offer Locked": "every method step has an action, actor, deliverable, timing and
measure". The reference model canon that informs this stage is files 11 and 12
(SPEC.md section 12.3): the Perfect Product core training and the Product Matrix
choose one delivery model, outline a six-to-twelve week program that follows the
signature solution, price by outcome, and record eligibility and guarantee terms.

Like the stage 1 ``DiagnosisPackage`` (cycle 69), stage 2 ``CurrencyPackage``
(cycle 71), stage 3 ``DiagnosticPackage`` (cycle 73) and stage 4
``SignaturePackage`` (cycle 75) bridges, this package projects the reviewed
stage 5 ``DeliverySpecification`` onto the twelve canonical stage 5 asset kinds
as exact ``StageAssetVersion`` evidence so a canonical gate can be assembled. It
refuses a blank identity, a versionless delivery or a cross-tenant delivery
rather than silently pinning inexact or foreign evidence.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    InvalidOfferPackageError,
    OfferTenantBoundaryError,
)
from redops.contexts.commercial.domain.value_objects import (
    CANONICAL_OFFER_KINDS,
    OfferPackage,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.method.domain.entities import SignatureSolution

from ..method.fixtures import signature_solution
from .fixtures import TENANT, delivery_specification

OTHER_TENANT = "client-other"


def other_tenant_delivery():
    solution: SignatureSolution = signature_solution(tenant_id=OTHER_TENANT)
    return delivery_specification(signature_solution=solution)


def package(**overrides) -> OfferPackage:
    values = {
        "package_id": "offer-package-3f",
        "tenant_id": TENANT,
        "delivery": delivery_specification(),
        "delivery_version": 1,
    }
    values.update(overrides)
    return OfferPackage(**values)


class OfferPackageProjectionTests(unittest.TestCase):
    def test_the_package_projects_all_twelve_canonical_stage_five_kinds(self):
        assets = package().stage_asset_versions()

        kinds = {asset.kind for asset in assets}
        self.assertEqual(frozenset(CANONICAL_OFFER_KINDS), kinds)
        self.assertEqual(12, len(assets))

    def test_the_canonical_kinds_match_the_template_stage_five_package(self):
        template_kinds = stage_zero_to_ten_template().required_asset_kinds(5)

        self.assertEqual(template_kinds, frozenset(CANONICAL_OFFER_KINDS))

    def test_every_kind_pins_the_reviewed_delivery_at_its_exact_version(self):
        assets = package(delivery_version=4).stage_asset_versions()

        self.assertEqual(12, len(assets))
        for asset in assets:
            self.assertEqual(4, asset.version)

    def test_each_kind_pins_the_reviewed_delivery_identity(self):
        assets = package().stage_asset_versions()

        for asset in assets:
            self.assertEqual("delivery-3f", asset.asset_id)

    def test_the_projected_evidence_is_tenant_scoped(self):
        for asset in package().stage_asset_versions():
            self.assertEqual(TENANT, asset.tenant_id)

    def test_a_complete_package_reports_no_missing_kinds(self):
        value = package()

        self.assertTrue(value.is_complete)
        self.assertEqual((), value.missing_kinds())

    def test_the_package_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            package().package_id = "tampered"


class OfferPackageBoundaryTests(unittest.TestCase):
    def test_a_cross_tenant_delivery_is_refused(self):
        with self.assertRaises(OfferTenantBoundaryError):
            package(delivery=other_tenant_delivery())

    def test_a_blank_package_identity_is_refused(self):
        for override in ({"package_id": ""}, {"tenant_id": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidOfferPackageError):
                    package(**override)

    def test_a_versionless_reviewed_delivery_is_refused(self):
        for override in ({"delivery_version": 0}, {"delivery_version": -1}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidOfferPackageError):
                    package(**override)


if __name__ == "__main__":
    unittest.main()
