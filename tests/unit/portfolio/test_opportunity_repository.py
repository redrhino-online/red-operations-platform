"""Adapter contract tests for the portfolio opportunity store (SPEC.md section 6).

SPEC.md section 7 lists ``/opportunities`` and section 9 keeps a tenant's
portfolio record from being lost. These tests exercise the port contract on the
process-local reference adapter: an opportunity is append-only, scoped to one
tenant, idempotent on an exact replay and a named conflict on a different same-id
re-statement.
"""

from __future__ import annotations

import unittest
from datetime import date

from redops.contexts.governance.domain.value_objects import StageAssetVersion
from redops.contexts.portfolio.domain.errors import (
    OpportunityConflictError,
    OpportunityTenantBoundaryError,
)
from redops.contexts.portfolio.domain.value_objects import (
    Opportunity,
    OpportunityKind,
)
from redops.contexts.portfolio.infrastructure.repositories import (
    InMemoryOpportunityRepository,
    opportunity_repository_from_env,
)

TENANT = "tenant-3f"
OTHER_TENANT = "tenant-other"
CAPTURED_ON = date(2026, 10, 3)


def opportunity(**overrides) -> Opportunity:
    values = {
        "opportunity_id": "opp-1",
        "tenant_id": TENANT,
        "title": "a smaller entry point offer",
        "kind": OpportunityKind.ENTRY_POINT,
        "source": StageAssetVersion(
            asset_id="offer-3f",
            tenant_id=TENANT,
            kind="offer-version",
            version=3,
        ),
        "investment_case": "the warmed audience already converts on the core offer",
        "expected_outcome": "a lower priced entry point that raises qualified leads",
        "owner": "portfolio-lead",
        "next_action": "size the offer and price it against the primary currency",
        "captured_on": CAPTURED_ON,
    }
    values.update(overrides)
    return Opportunity(**values)


class InMemoryOpportunityRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryOpportunityRepository()

    def test_a_saved_opportunity_is_listed_and_resolved(self) -> None:
        self.repository.save(opportunity())

        self.assertEqual((opportunity(),), self.repository.list(TENANT))
        self.assertEqual(
            opportunity(), self.repository.get(TENANT, "opp-1")
        )

    def test_an_unknown_opportunity_is_none(self) -> None:
        self.assertIsNone(self.repository.get(TENANT, "opp-missing"))

    def test_reads_are_scoped_by_tenant(self) -> None:
        self.repository.save(opportunity())

        self.assertEqual((), self.repository.list(OTHER_TENANT))
        self.assertIsNone(self.repository.get(OTHER_TENANT, "opp-1"))

    def test_an_exact_replay_is_idempotent(self) -> None:
        self.repository.save(opportunity())
        self.repository.save(opportunity())

        self.assertEqual(1, len(self.repository.list(TENANT)))

    def test_a_same_id_different_body_is_refused(self) -> None:
        self.repository.save(opportunity())

        with self.assertRaises(OpportunityConflictError):
            self.repository.save(opportunity(title="a different opportunity"))

    def test_an_unscoped_read_or_write_is_refused(self) -> None:
        with self.assertRaises(OpportunityTenantBoundaryError):
            self.repository.list("   ")

    def test_the_factory_uses_the_process_local_store_without_a_url(self) -> None:
        self.assertIsInstance(
            opportunity_repository_from_env(None),
            InMemoryOpportunityRepository,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
