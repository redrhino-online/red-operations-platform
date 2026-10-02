"""Behavioral tests for the MethodVersion aggregate (pure domain, Method).

Rules under test come from SPEC.md sections 3 and 4:
- MethodVersion records the parent method, stages, currency, claims and a
  semantic version (SPEC.md section 3 aggregate table).
- "Approval pins an exact version and intended use" (SPEC.md section 3).
- A method change requires a new semantic version; the previous approved
  version stays historically identifiable (SPEC.md section 4).
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.method.domain.entities import MethodVersion
from redops.contexts.method.domain.errors import (
    InvalidMethodError,
    InvalidMethodVersionError,
    MethodApprovalError,
)
from redops.contexts.method.domain.value_objects import SemanticVersion

from .fixtures import diagnostic_model, primary_currency

TODAY = date(2026, 10, 2)


def method_version(**overrides) -> MethodVersion:
    values = {
        "method_id": "method-3f",
        "tenant_id": "client-3f",
        "parent_method": "signature-solution",
        "semantic_version": SemanticVersion(1, 0, 0),
        "stages": ("diagnose", "position", "model"),
        "currency": "qualified-referrals",
        "claims": frozenset({"claim-1"}),
        "primary_currency": primary_currency(),
        "diagnostic_model": diagnostic_model(),
    }
    values.update(overrides)
    return MethodVersion(**values)


class SemanticVersionTests(unittest.TestCase):
    def test_a_semantic_version_parses_and_formats(self):
        parsed = SemanticVersion.parse("2.4.1")

        self.assertEqual(SemanticVersion(2, 4, 1), parsed)
        self.assertEqual("2.4.1", str(parsed))

    def test_a_malformed_semantic_version_is_rejected(self):
        for text in ("1.2", "1.2.3.4", "1.x.0", "", "1.-2.0"):
            with self.subTest(text=text):
                with self.assertRaises(InvalidMethodVersionError):
                    SemanticVersion.parse(text)

    def test_a_negative_semantic_version_part_is_rejected(self):
        with self.assertRaises(InvalidMethodVersionError):
            SemanticVersion(1, -1, 0)


class MethodVersionInvariantTests(unittest.TestCase):
    def test_a_method_records_its_required_fields(self):
        version = method_version()

        self.assertEqual("signature-solution", version.parent_method)
        self.assertEqual(("diagnose", "position", "model"), version.stages)
        self.assertEqual("qualified-referrals", version.currency)
        self.assertEqual(frozenset({"claim-1"}), version.claims)
        self.assertFalse(version.is_approved)

    def test_a_method_without_a_parent_is_rejected(self):
        with self.assertRaises(InvalidMethodError):
            method_version(parent_method="")

    def test_a_method_without_stages_is_rejected(self):
        with self.assertRaises(InvalidMethodError):
            method_version(stages=())

    def test_a_method_without_a_currency_is_rejected(self):
        with self.assertRaises(InvalidMethodError):
            method_version(currency="   ")


class MethodApprovalTests(unittest.TestCase):
    def test_approval_pins_the_exact_version_and_intended_use(self):
        approved = method_version().approve(
            approved_by="client-authority",
            intended_use="3f pilot campaign",
            on=TODAY,
        )

        self.assertTrue(approved.is_approved)
        self.assertEqual(SemanticVersion(1, 0, 0), approved.approval.version)
        self.assertEqual("3f pilot campaign", approved.approval.intended_use)
        self.assertEqual("client-authority", approved.approval.approved_by)

    def test_an_approval_for_one_version_does_not_authorize_another(self):
        approved = method_version().approve(
            approved_by="client-authority",
            intended_use="3f pilot campaign",
            on=TODAY,
        )

        self.assertTrue(
            approved.authorizes(SemanticVersion(1, 0, 0), "3f pilot campaign")
        )
        self.assertFalse(
            approved.authorizes(SemanticVersion(1, 1, 0), "3f pilot campaign")
        )

    def test_an_approval_for_one_intended_use_does_not_authorize_another(self):
        approved = method_version().approve(
            approved_by="client-authority",
            intended_use="3f pilot campaign",
            on=TODAY,
        )

        self.assertFalse(
            approved.authorizes(SemanticVersion(1, 0, 0), "different engagement")
        )

    def test_approval_requires_an_intended_use(self):
        with self.assertRaises(MethodApprovalError):
            method_version().approve(
                approved_by="client-authority",
                intended_use="   ",
                on=TODAY,
            )

    def test_an_approved_method_is_immutable(self):
        approved = method_version().approve(
            approved_by="client-authority",
            intended_use="3f pilot campaign",
            on=TODAY,
        )

        with self.assertRaises(FrozenInstanceError):
            approved.currency = "tampered"

    def test_revising_a_method_requires_a_newer_version(self):
        approved = method_version().approve(
            approved_by="client-authority",
            intended_use="3f pilot campaign",
            on=TODAY,
        )

        with self.assertRaises(InvalidMethodVersionError):
            approved.revised(semantic_version=SemanticVersion(1, 0, 0))
        with self.assertRaises(InvalidMethodVersionError):
            approved.revised(semantic_version=SemanticVersion(0, 9, 0))

    def test_revising_an_approved_method_drops_the_approval_from_the_new_version(self):
        approved = method_version().approve(
            approved_by="client-authority",
            intended_use="3f pilot campaign",
            on=TODAY,
        )

        revised = approved.revised(
            semantic_version=SemanticVersion(1, 1, 0),
            currency="qualified-referrals-v2",
        )

        self.assertEqual("qualified-referrals-v2", revised.currency)
        self.assertFalse(revised.is_approved)
        self.assertTrue(approved.is_approved)
        self.assertEqual(SemanticVersion(1, 0, 0), approved.approval.version)


if __name__ == "__main__":
    unittest.main()
