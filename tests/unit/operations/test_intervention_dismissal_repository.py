"""Adapter contract tests for the intervention dismissal store (SPEC.md section 6).

SPEC.md section 7 allows a command center card to be dismissed with rationale and
section 9 keeps the decision from being lost. These tests exercise the port
contract on the process-local reference adapter: a dismissal is append only,
scoped to one client under its tenant, idempotent on an exact replay and a named
conflict on a different same-key re-statement.
"""

from __future__ import annotations

import unittest
from datetime import date

from redops.contexts.operations.domain.errors import (
    InterventionDismissalConflictError,
    InterventionDismissalTenantBoundaryError,
)
from redops.contexts.operations.domain.value_objects import (
    InterventionDismissal,
    InterventionReason,
)
from redops.contexts.operations.infrastructure.repositories import (
    InMemoryInterventionDismissalRepository,
    intervention_dismissal_repository_from_env,
)

TENANT = "tenant-3f"
OTHER_TENANT = "tenant-other"
CLIENT = "engagement-3f"
DISMISSED_ON = date(2026, 10, 3)


def dismissal(**overrides) -> InterventionDismissal:
    values = {
        "tenant_id": TENANT,
        "client": CLIENT,
        "reason": InterventionReason.BLOCKED_CRITICAL_PATH,
        "subject": "stage-3",
        "rationale": "the blocker is being handled off-platform",
        "actor": "production-manager",
        "dismissed_on": DISMISSED_ON,
    }
    values.update(overrides)
    return InterventionDismissal(**values)


class InMemoryInterventionDismissalRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryInterventionDismissalRepository()

    def test_a_saved_dismissal_is_listed_for_its_client(self) -> None:
        self.repository.save(dismissal())

        self.assertEqual(
            (dismissal(),), self.repository.list(TENANT, CLIENT)
        )

    def test_list_is_scoped_by_tenant_and_client(self) -> None:
        self.repository.save(dismissal())
        self.repository.save(dismissal(subject="stage-4"))

        self.assertEqual((), self.repository.list(OTHER_TENANT, CLIENT))
        self.assertEqual((), self.repository.list(TENANT, "engagement-other"))

    def test_an_exact_replay_is_idempotent(self) -> None:
        self.repository.save(dismissal())
        self.repository.save(dismissal())

        self.assertEqual(1, len(self.repository.list(TENANT, CLIENT)))

    def test_a_same_key_different_body_is_refused(self) -> None:
        self.repository.save(dismissal())

        with self.assertRaises(InterventionDismissalConflictError):
            self.repository.save(dismissal(rationale="a different reason"))

    def test_an_unscoped_read_or_write_is_refused(self) -> None:
        with self.assertRaises(InterventionDismissalTenantBoundaryError):
            self.repository.list("   ", CLIENT)

    def test_the_factory_uses_the_process_local_store_without_a_url(self) -> None:
        self.assertIsInstance(
            intervention_dismissal_repository_from_env(None),
            InMemoryInterventionDismissalRepository,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
