"""Configuration-selection tests for the gate ledger repository.

ADR 0003 makes RED's gate ledger durable in PostgreSQL, and SPEC.md sections 3,
4 and 9 require a recorded gate to survive a restart, stay client-scoped and be
shared across the API and worker processes. The API chooses its adapter from
configuration, so these tests pin that choice: absent a ``DATABASE_URL`` the
process-local adapter is used, and a set-but-unusable configuration is refused
rather than silently served as non-durable. No third-party package is needed,
so the domain-only interpreter runs them.
"""

from __future__ import annotations

import unittest

from redops.contexts.governance.infrastructure.repositories import (
    GateLedgerConfigurationError,
    InMemoryGateLedgerRepository,
    gate_ledger_repository_from_env,
    psycopg as _PSYCOPG,
)


class GateLedgerRepositorySelectionTests(unittest.TestCase):
    """The adapter is selected from configuration, never downgraded silently."""

    def test_an_absent_database_url_selects_the_process_local_adapter(self) -> None:
        for value in (None, "", "   "):
            with self.subTest(database_url=value):
                self.assertIsInstance(
                    gate_ledger_repository_from_env(value),
                    InMemoryGateLedgerRepository,
                )

    def test_a_database_url_without_a_driver_is_a_configuration_error(self) -> None:
        if _PSYCOPG is not None:
            self.skipTest(
                "psycopg is installed; the missing-driver branch runs on the "
                "domain-only interpreter"
            )
        with self.assertRaises(GateLedgerConfigurationError):
            gate_ledger_repository_from_env(
                "postgresql://redops:redops@localhost:5432/redops"
            )


if __name__ == "__main__":
    unittest.main()
