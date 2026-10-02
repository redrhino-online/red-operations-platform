"""Behavioral tests for upstream stage 2/3 pins on a MethodVersion.

Rules under test come from SPEC.md sections 3 and 4:
- MethodVersion records its currency (SPEC.md section 3 aggregate table).
- "Production requires approved dependencies" (SPEC.md section 3): the stage 4
  Signature Solution is downstream of the stage 2 "Currency Locked" asset
  (`primary-currency`) and the stage 3 "Diagnostic Model Approved" asset
  (`profit-pyramid-levels`), so an approved Signature Solution must pin those
  exact upstream assets.
- The stage 4 "IP Architecture Locked" asset (`three-phases`, `nine-steps`) is
  itself the method's exact structure (SPEC.md section 4 stage 4), so an
  approved method must pin the locked `SignatureSolution` and cannot be approved
  without it.
- An unapproved dependency cannot be represented as approved (SPEC.md section 4),
  and a revision must not silently reuse an approval or its pinned dependencies
  (SPEC.md section 4; the revised version keeps a new exact version).
"""

import unittest
from datetime import date

from redops.contexts.method.domain.entities import (
    DiagnosticModel,
    MethodVersion,
    SignatureSolution,
)
from redops.contexts.method.domain.errors import MethodDependencyError
from redops.contexts.method.domain.value_objects import (
    PrimaryCurrency,
    SemanticVersion,
)

from .fixtures import diagnostic_model, primary_currency, signature_solution

TODAY = date(2026, 10, 2)
TENANT = "client-3f"


def method_version(**overrides) -> MethodVersion:
    values = {
        "method_id": "method-3f",
        "tenant_id": TENANT,
        "parent_method": "signature-solution",
        "semantic_version": SemanticVersion(1, 0, 0),
        "stages": ("diagnose", "position", "model"),
        "currency": "qualified-referrals",
        "claims": frozenset({"claim-1"}),
        "primary_currency": primary_currency(),
        "diagnostic_model": diagnostic_model(),
        "signature_solution": signature_solution(),
    }
    values.update(overrides)
    return MethodVersion(**values)


class MethodDependencyPinningTests(unittest.TestCase):
    def test_a_method_pins_its_exact_upstream_currency_and_diagnostic_model(self):
        currency = primary_currency()
        model = diagnostic_model()

        version = method_version(primary_currency=currency, diagnostic_model=model)

        self.assertIs(currency, version.primary_currency)
        self.assertIs(model, version.diagnostic_model)

    def test_a_method_pins_its_exact_stage_4_signature_solution(self):
        solution = signature_solution()

        version = method_version(signature_solution=solution)

        self.assertIs(solution, version.signature_solution)
        self.assertEqual(9, version.signature_solution.step_count)

    def test_a_draft_method_may_still_be_drafted_without_dependencies(self):
        version = method_version(
            primary_currency=None,
            diagnostic_model=None,
            signature_solution=None,
        )

        self.assertIsNone(version.primary_currency)
        self.assertIsNone(version.diagnostic_model)
        self.assertIsNone(version.signature_solution)
        self.assertFalse(version.is_approved)

    def test_a_method_cannot_pin_another_tenants_primary_currency(self):
        with self.assertRaises(MethodDependencyError):
            method_version(primary_currency=primary_currency(tenant_id="client-other"))

    def test_a_method_cannot_pin_another_tenants_diagnostic_model(self):
        with self.assertRaises(MethodDependencyError):
            method_version(diagnostic_model=diagnostic_model(tenant_id="client-other"))

    def test_a_method_cannot_pin_another_tenants_signature_solution(self):
        with self.assertRaises(MethodDependencyError):
            method_version(
                signature_solution=signature_solution(tenant_id="client-other")
            )

    def test_approving_a_method_without_a_pinned_currency_is_rejected(self):
        with self.assertRaises(MethodDependencyError):
            method_version(primary_currency=None).approve(
                approved_by="client-authority",
                intended_use="3f pilot campaign",
                on=TODAY,
            )

    def test_approving_a_method_without_a_pinned_diagnostic_model_is_rejected(self):
        with self.assertRaises(MethodDependencyError):
            method_version(diagnostic_model=None).approve(
                approved_by="client-authority",
                intended_use="3f pilot campaign",
                on=TODAY,
            )

    def test_approving_a_method_without_a_locked_signature_solution_is_rejected(self):
        with self.assertRaises(MethodDependencyError):
            method_version(signature_solution=None).approve(
                approved_by="client-authority",
                intended_use="3f pilot campaign",
                on=TODAY,
            )

    def test_an_approved_method_keeps_its_pinned_dependencies(self):
        approved = method_version().approve(
            approved_by="client-authority",
            intended_use="3f pilot campaign",
            on=TODAY,
        )

        self.assertTrue(approved.is_approved)
        self.assertIsInstance(approved.primary_currency, PrimaryCurrency)
        self.assertIsInstance(approved.diagnostic_model, DiagnosticModel)
        self.assertIsInstance(approved.signature_solution, SignatureSolution)


class MethodDependencyRevisionTests(unittest.TestCase):
    def test_revising_a_method_drops_the_pinned_dependencies(self):
        approved = method_version().approve(
            approved_by="client-authority",
            intended_use="3f pilot campaign",
            on=TODAY,
        )

        revised = approved.revised(semantic_version=SemanticVersion(1, 1, 0))

        self.assertIsNone(revised.primary_currency)
        self.assertIsNone(revised.diagnostic_model)
        self.assertIsNone(revised.signature_solution)
        self.assertFalse(revised.is_approved)

    def test_revising_a_method_can_re_pin_new_dependencies(self):
        approved = method_version().approve(
            approved_by="client-authority",
            intended_use="3f pilot campaign",
            on=TODAY,
        )
        new_currency = primary_currency()
        new_model = diagnostic_model()
        new_solution = signature_solution()

        revised = approved.revised(
            semantic_version=SemanticVersion(2, 0, 0),
            primary_currency=new_currency,
            diagnostic_model=new_model,
            signature_solution=new_solution,
        )

        self.assertIs(new_currency, revised.primary_currency)
        self.assertIs(new_model, revised.diagnostic_model)
        self.assertIs(new_solution, revised.signature_solution)
        self.assertEqual(SemanticVersion(1, 0, 0), approved.approval.version)


if __name__ == "__main__":
    unittest.main()
