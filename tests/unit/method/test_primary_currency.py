"""Behavioral tests for the PrimaryCurrency value object (pure domain, Method).

Rules under test come from SPEC.md section 4, stage 2 "Position" and its
"Currency Locked" checkpoint: one primary outcome connects a specific person, a
measurable movement, and a distinct mechanism. Phase 3 TDD example: "currency
gate rejects an unspecified audience or unmeasured outcome". A currency that
leaves the person, the movement or the mechanism unspecified cannot exist, so an
unlocked currency can never be pinned to the stage 2 gate as approved evidence.
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.method.domain.errors import InvalidCurrencyError
from redops.contexts.method.domain.value_objects import PrimaryCurrency


def primary_currency(**overrides) -> PrimaryCurrency:
    values = {
        "tenant_id": "client-3f",
        "currency": "qualified referrals",
        "audience": "owner-operators of two to five person service firms",
        "current_measure": "4 qualified referrals per month",
        "desired_measure": "12 qualified referrals per month",
        "mechanism": "referral partner network",
    }
    values.update(overrides)
    return PrimaryCurrency(**values)


class PrimaryCurrencyCheckpointTests(unittest.TestCase):
    def test_a_locked_currency_connects_person_movement_and_mechanism(self):
        currency = primary_currency()

        self.assertEqual(
            "owner-operators of two to five person service firms",
            currency.audience,
        )
        self.assertEqual("12 qualified referrals per month", currency.desired_measure)
        self.assertEqual("referral partner network", currency.mechanism)

    def test_a_currency_without_a_specific_person_is_rejected(self):
        for override in ({"audience": ""}, {"audience": "   "}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidCurrencyError):
                    primary_currency(**override)

    def test_a_currency_without_a_name_or_mechanism_is_rejected(self):
        for override in (
            {"currency": "  "},
            {"mechanism": ""},
            {"tenant_id": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidCurrencyError):
                    primary_currency(**override)

    def test_a_currency_without_a_measurable_movement_is_rejected(self):
        for override in (
            {"current_measure": ""},
            {"desired_measure": "   "},
            {"desired_measure": "4 qualified referrals per month"},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidCurrencyError):
                    primary_currency(**override)

    def test_a_locked_currency_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            primary_currency().currency = "tampered"


if __name__ == "__main__":
    unittest.main()
