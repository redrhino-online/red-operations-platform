"""Behavioral tests for the stage 2 "Currency Locked" reviewed asset package.

Rules under test come from SPEC.md sections 3, 4 and 12.3. Stage 2 "Position"
requires the asset package "category, currency inventory and primary currency,
current and desired measures, horizon, qualifications, transformation statement,
core problem and Million Dollar Message", and its checkpoint is "Currency
Locked": "one primary outcome connects a specific person, measurable movement,
and distinct mechanism". The reference model canon that informs this stage is
files 04, 05 and 06 (SPEC.md section 12.3): the avatar goals grid feeds a
currency calculator that leaves the general category behind, lists the
currencies to increase and decrease, fixes a metric and timeline, and resolves
into the million dollar message formula (avatar x currency x metric x timeline
minus pain) with a stated transformation and an acceptance line.

Like the stage 1 ``DiagnosisPackage`` bridge (cycle 69), this package projects
the reviewed stage 2 values onto the ten canonical stage 2 asset kinds as exact
``StageAssetVersion`` evidence so a canonical gate can be assembled. It refuses
a blank identity, a versionless asset or a cross-tenant value rather than
silently pinning inexact or foreign evidence.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.commercial.domain.errors import (
    CurrencyTenantBoundaryError,
    InvalidCurrencyInventoryError,
    InvalidCurrencyPackageError,
    InvalidMillionDollarMessageError,
    InvalidPositioningDecisionError,
)
from redops.contexts.commercial.domain.value_objects import (
    CANONICAL_CURRENCY_KINDS,
    CurrencyInventory,
    CurrencyPackage,
    MillionDollarMessage,
    PositioningDecision,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.method.domain.value_objects import PrimaryCurrency

TENANT = "client-3f"
OTHER_TENANT = "client-other"


def inventory(**overrides) -> CurrencyInventory:
    values = {
        "inventory_id": "currency-inventory-3f",
        "tenant_id": TENANT,
        "category": "business consulting",
        "currencies_to_increase": ("leads", "sales", "profit"),
        "currencies_to_decrease": ("ad spend", "cancellations"),
    }
    values.update(overrides)
    return CurrencyInventory(**values)


def positioning(**overrides) -> PositioningDecision:
    values = {
        "decision_id": "positioning-3f",
        "tenant_id": TENANT,
        "core_problem": "unpredictable qualified demand",
        "transformation_statement": "a predictable pipeline that runs without the owner",
        "horizon": "90 days",
        "qualifications": ("runs a service firm with delivery capacity",),
        "disqualifications": ("no delivery capacity and no budget",),
    }
    values.update(overrides)
    return PositioningDecision(**values)


def primary_currency(**overrides) -> PrimaryCurrency:
    values = {
        "tenant_id": TENANT,
        "currency": "qualified referrals",
        "audience": "owner-operators of two to five person service firms",
        "current_measure": "4 qualified referrals per month",
        "desired_measure": "12 qualified referrals per month",
        "mechanism": "referral partner network",
    }
    values.update(overrides)
    return PrimaryCurrency(**values)


def million_dollar_message(**overrides) -> MillionDollarMessage:
    values = {
        "message_id": "mdm-3f",
        "tenant_id": TENANT,
        "avatar": "owner-operators of two to five person service firms",
        "currency": "qualified referrals",
        "metric": "12 qualified referrals per month",
        "timeline": "90 days",
        "pain": "feast and famine pipeline",
        "message": (
            "I help owner-operators of small service firms reach twelve "
            "qualified referrals a month in ninety days without relying on "
            "referral luck, so their pipeline stops deciding their payroll"
        ),
    }
    values.update(overrides)
    return MillionDollarMessage(**values)


def package(**overrides) -> CurrencyPackage:
    values = {
        "package_id": "currency-3f",
        "tenant_id": TENANT,
        "inventory": inventory(),
        "inventory_version": 1,
        "positioning": positioning(),
        "positioning_version": 1,
        "primary_currency": primary_currency(),
        "primary_currency_version": 1,
        "million_dollar_message": million_dollar_message(),
        "million_dollar_message_version": 1,
    }
    values.update(overrides)
    return CurrencyPackage(**values)


class CurrencyInventoryTests(unittest.TestCase):
    def test_a_category_with_increase_and_decrease_currencies_is_valid(self):
        value = inventory()

        self.assertEqual("business consulting", value.category)
        self.assertEqual(("leads", "sales", "profit"), value.currencies_to_increase)
        self.assertEqual(("ad spend", "cancellations"), value.currencies_to_decrease)

    def test_a_missing_identity_category_or_list_is_rejected(self):
        for override in (
            {"inventory_id": ""},
            {"tenant_id": "   "},
            {"category": ""},
            {"currencies_to_increase": ()},
            {"currencies_to_decrease": ()},
            {"currencies_to_increase": ("leads", "")},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidCurrencyInventoryError):
                    inventory(**override)

    def test_a_currency_inventory_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            inventory().category = "tampered"


class PositioningDecisionTests(unittest.TestCase):
    def test_a_positioning_decision_states_problem_transformation_and_line(self):
        value = positioning()

        self.assertEqual("unpredictable qualified demand", value.core_problem)
        self.assertEqual("90 days", value.horizon)
        self.assertEqual(
            ("runs a service firm with delivery capacity",), value.qualifications
        )
        self.assertEqual(
            ("no delivery capacity and no budget",), value.disqualifications
        )

    def test_a_missing_positioning_dimension_is_rejected(self):
        for override in (
            {"decision_id": ""},
            {"tenant_id": ""},
            {"core_problem": ""},
            {"transformation_statement": "   "},
            {"horizon": ""},
            {"qualifications": ()},
            {"disqualifications": ()},
            {"disqualifications": ("",)},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidPositioningDecisionError):
                    positioning(**override)

    def test_a_positioning_decision_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            positioning().core_problem = "tampered"


class MillionDollarMessageTests(unittest.TestCase):
    def test_the_message_carries_every_formula_component(self):
        value = million_dollar_message()

        self.assertEqual("qualified referrals", value.currency)
        self.assertEqual("12 qualified referrals per month", value.metric)
        self.assertEqual("90 days", value.timeline)
        self.assertEqual("feast and famine pipeline", value.pain)

    def test_a_missing_formula_component_is_rejected(self):
        for override in (
            {"message_id": ""},
            {"tenant_id": ""},
            {"avatar": ""},
            {"currency": "   "},
            {"metric": ""},
            {"timeline": ""},
            {"pain": ""},
            {"message": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidMillionDollarMessageError):
                    million_dollar_message(**override)

    def test_a_million_dollar_message_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            million_dollar_message().message = "tampered"


class CurrencyPackageProjectionTests(unittest.TestCase):
    def test_the_package_projects_all_ten_canonical_stage_two_kinds(self):
        assets = package().stage_asset_versions()

        kinds = {asset.kind for asset in assets}
        self.assertEqual(frozenset(CANONICAL_CURRENCY_KINDS), kinds)
        self.assertEqual(10, len(assets))

    def test_the_canonical_kinds_match_the_template_stage_two_package(self):
        template_kinds = stage_zero_to_ten_template().required_asset_kinds(2)

        self.assertEqual(template_kinds, frozenset(CANONICAL_CURRENCY_KINDS))

    def test_each_reviewed_asset_pins_its_own_exact_version(self):
        assets = package(
            inventory_version=2,
            positioning_version=3,
            primary_currency_version=4,
            million_dollar_message_version=5,
        ).stage_asset_versions()

        versions = {asset.kind: asset.version for asset in assets}
        self.assertEqual(2, versions["category"])
        self.assertEqual(2, versions["currency-inventory"])
        self.assertEqual(4, versions["primary-currency"])
        self.assertEqual(4, versions["current-measures"])
        self.assertEqual(4, versions["desired-measures"])
        self.assertEqual(3, versions["horizon"])
        self.assertEqual(3, versions["qualifications"])
        self.assertEqual(3, versions["transformation-statement"])
        self.assertEqual(3, versions["core-problem"])
        self.assertEqual(5, versions["million-dollar-message"])

    def test_each_kind_pins_the_reviewed_asset_identity(self):
        assets = package().stage_asset_versions()

        assets_by_kind = {asset.kind: asset for asset in assets}
        self.assertEqual(
            "currency-inventory-3f", assets_by_kind["category"].asset_id
        )
        self.assertEqual(
            "currency-inventory-3f", assets_by_kind["currency-inventory"].asset_id
        )
        self.assertEqual(
            "qualified referrals", assets_by_kind["primary-currency"].asset_id
        )
        self.assertEqual("positioning-3f", assets_by_kind["horizon"].asset_id)
        self.assertEqual(
            "mdm-3f", assets_by_kind["million-dollar-message"].asset_id
        )

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


class CurrencyPackageBoundaryTests(unittest.TestCase):
    def test_a_cross_tenant_inventory_is_refused(self):
        with self.assertRaises(CurrencyTenantBoundaryError):
            package(inventory=inventory(tenant_id=OTHER_TENANT))

    def test_a_cross_tenant_positioning_decision_is_refused(self):
        with self.assertRaises(CurrencyTenantBoundaryError):
            package(positioning=positioning(tenant_id=OTHER_TENANT))

    def test_a_cross_tenant_primary_currency_is_refused(self):
        with self.assertRaises(CurrencyTenantBoundaryError):
            package(primary_currency=primary_currency(tenant_id=OTHER_TENANT))

    def test_a_cross_tenant_million_dollar_message_is_refused(self):
        with self.assertRaises(CurrencyTenantBoundaryError):
            package(
                million_dollar_message=million_dollar_message(
                    tenant_id=OTHER_TENANT
                )
            )

    def test_a_blank_package_identity_is_refused(self):
        for override in ({"package_id": ""}, {"tenant_id": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidCurrencyPackageError):
                    package(**override)

    def test_a_versionless_reviewed_asset_is_refused(self):
        for override in (
            {"inventory_version": 0},
            {"positioning_version": -1},
            {"primary_currency_version": 0},
            {"million_dollar_message_version": 0},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidCurrencyPackageError):
                    package(**override)


if __name__ == "__main__":
    unittest.main()
