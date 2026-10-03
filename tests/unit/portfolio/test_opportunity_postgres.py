"""Adapter contract tests for the PostgreSQL portfolio opportunity store.

ADR 0003 makes RED's records durable in PostgreSQL, and SPEC.md section 6 says
infrastructure adapters implement ports. These tests exercise the real
``PostgresOpportunityRepository`` against the local compose database: the schema
is created by the committed migration ``0017_opportunities`` (SPEC.md section 6),
and a proposed opportunity saved through the adapter is persisted and reloaded as
a value object with its tenant, id, kind, exact source asset version, investment
case, owner and state (SPEC.md sections 7 and 9). A stored row that claims an
approved expansion is refused on load by the value object (SPEC.md sections 1
and 5).

They skip cleanly when no psycopg driver, no alembic or no ``DATABASE_URL`` is
present, so the domain-only test interpreter still runs the rest of the suite.
Run them with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/portfolio/test_opportunity_postgres.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from datetime import date
from pathlib import Path

from redops.contexts.governance.domain.value_objects import StageAssetVersion
from redops.contexts.portfolio.domain.value_objects import (
    Opportunity,
    OpportunityKind,
)

TENANT = "tenant-3f"
OTHER_TENANT = "tenant-other"
CAPTURED_ON = date(2026, 10, 3)
DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL adapter test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)


def opportunity(**overrides) -> Opportunity:
    tenant = overrides.get("tenant_id", TENANT)
    values = {
        "opportunity_id": "opp-1",
        "tenant_id": TENANT,
        "title": "a smaller entry point offer",
        "kind": OpportunityKind.ENTRY_POINT,
        "source": StageAssetVersion(
            asset_id="offer-3f",
            tenant_id=tenant,
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


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresOpportunityRepositoryTests(unittest.TestCase):
    """The port contract, exercised against the real PostgreSQL schema."""

    @classmethod
    def setUpClass(cls) -> None:
        from alembic import command
        from alembic.config import Config

        cls._psycopg = importlib.import_module("psycopg")
        config = Config(str(REPO_ROOT / "alembic.ini"))
        config.set_main_option(
            "script_location",
            str(REPO_ROOT / "backend/redops/shared/persistence/migrations"),
        )
        config.set_main_option("sqlalchemy.url", DATABASE_URL)
        command.upgrade(config, "head")
        cls._connection = cls._psycopg.connect(DATABASE_URL)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._connection.close()

    def setUp(self) -> None:
        from redops.contexts.portfolio.infrastructure.repositories import (
            PostgresOpportunityRepository,
        )

        self.repository = PostgresOpportunityRepository(self._connection)
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE opportunities RESTART IDENTITY")
        self._connection.commit()

    def test_the_factory_builds_the_postgres_adapter_from_a_database_url(
        self,
    ) -> None:
        from redops.contexts.portfolio.infrastructure.repositories import (
            PostgresOpportunityRepository,
            opportunity_repository_from_env,
        )

        repository = opportunity_repository_from_env(DATABASE_URL)
        try:
            self.assertIsInstance(repository, PostgresOpportunityRepository)
            self.assertEqual((), repository.list(TENANT))
        finally:
            repository.close()

    def test_an_opportunity_survives_a_reload(self) -> None:
        stored = opportunity()
        self.repository.save(stored)

        self.assertEqual((stored,), self.repository.list(TENANT))
        self.assertEqual(stored, self.repository.get(TENANT, "opp-1"))

    def test_a_same_id_different_body_is_refused(self) -> None:
        from redops.contexts.portfolio.domain.errors import (
            OpportunityConflictError,
        )

        self.repository.save(opportunity())

        with self.assertRaises(OpportunityConflictError):
            self.repository.save(opportunity(title="a different opportunity"))

    def test_list_returns_only_the_tenant_opportunities(self) -> None:
        self.repository.save(opportunity(opportunity_id="opp-1"))
        self.repository.save(opportunity(opportunity_id="opp-2"))
        self.repository.save(
            opportunity(tenant_id=OTHER_TENANT, opportunity_id="opp-3")
        )

        listed = self.repository.list(TENANT)

        self.assertEqual({"opp-1", "opp-2"}, {item.opportunity_id for item in listed})
        self.assertEqual(1, len(self.repository.list(OTHER_TENANT)))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
