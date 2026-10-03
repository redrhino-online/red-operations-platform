"""Behavioral tests for the approved method version store (Method application).

Rules under test come from SPEC.md sections 3, 4 and 9:
- Approval pins an exact version and intended use (SPEC.md section 3).
- A previous approved version stays historically identifiable, and a change
  advances the version rather than overwriting it (SPEC.md section 4).
- A method version is a client resource: it must carry its tenant on every read
  and write, and one client's method cannot be resolved for another (SPEC.md
  sections 3 and 9).

The stage 6 to 10 gates resolve the exact approved method a prior gate pinned
from this seam instead of trusting a repeated request body.
"""

from __future__ import annotations

import unittest
from datetime import date

from redops.contexts.method.domain.errors import (
    MethodApprovalError,
    MethodVersionConflictError,
    MethodVersionTenantBoundaryError,
)
from redops.contexts.method.domain.value_objects import SemanticVersion
from redops.contexts.method.infrastructure.repositories import (
    InMemoryMethodVersionRepository,
)

from .test_method_version import method_version

ON = date(2026, 10, 2)


def approved_method(method=None):
    return (method or method_version()).approve(
        approved_by="client-approver-1",
        intended_use="3f pilot campaign",
        on=ON,
    )


class MethodVersionRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryMethodVersionRepository()

    def test_a_saved_approved_method_is_resolved_by_its_exact_version(self):
        method = approved_method()

        self.repository.save(method)

        resolved = self.repository.get(
            "client-3f", "method-3f", method.semantic_version
        )
        self.assertEqual(method, resolved)

    def test_unknown_method_or_version_resolves_to_none(self):
        stored = approved_method()
        self.repository.save(stored)

        self.assertIsNone(
            self.repository.get("client-3f", "method-other", stored.semantic_version)
        )
        self.assertIsNone(
            self.repository.get("client-3f", "method-3f", SemanticVersion(2, 0, 0))
        )

    def test_a_different_body_under_the_same_version_is_refused(self):
        self.repository.save(approved_method())

        with self.assertRaises(MethodVersionConflictError):
            self.repository.save(
                approved_method(method_version(currency="monthly-revenue"))
            )

    def test_re_saving_the_identical_method_is_idempotent(self):
        method = approved_method()
        self.repository.save(method)

        self.repository.save(method)

        self.assertEqual(
            method,
            self.repository.get("client-3f", "method-3f", method.semantic_version),
        )

    def test_an_unapproved_draft_cannot_be_stored(self):
        with self.assertRaises(MethodApprovalError):
            self.repository.save(method_version())

    def test_a_blank_tenant_is_refused_on_read(self):
        method = approved_method()
        self.repository.save(method)

        for tenant in ("", "   "):
            with self.subTest(tenant=tenant):
                with self.assertRaises(MethodVersionTenantBoundaryError):
                    self.repository.get(tenant, "method-3f", method.semantic_version)

    def test_one_clients_method_is_not_visible_to_another(self):
        self.repository.save(approved_method())

        foreign = self.repository.get(
            "client-other", "method-3f", approved_method().semantic_version
        )

        self.assertIsNone(foreign)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
