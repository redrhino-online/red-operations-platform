"""Adapter contract tests for the PostgreSQL portfolio umbrella plan store.

ADR 0003 makes RED's records durable in PostgreSQL, and SPEC.md section 6 says
infrastructure adapters implement ports. These tests exercise the real
``PostgresUmbrellaPlanRepository`` against the local compose database: the schema
is created by the committed migration ``0019_umbrella_plans`` (SPEC.md section 6),
and a canon umbrella plan saved through the adapter is persisted and reloaded as a
value object with its tenant, id, owner, workspace, template version, launch-map
sections, targets and ordered review history (SPEC.md sections 7 and 9). A stored
row the aggregate would reject raises on load rather than being read back as a
client plan (SPEC.md sections 1 and 5).

They skip cleanly when no psycopg driver, no alembic or no ``DATABASE_URL`` is
present, so the domain-only test interpreter still runs the rest of the suite.
Run them with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/portfolio/test_umbrella_plan_postgres.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from datetime import date, timedelta
from pathlib import Path

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.value_objects import ClientAuthority
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.portfolio.domain.value_objects import (
    LAUNCH_MAP_SECTIONS,
    LAUNCH_MAP_SECTION_STAGES,
    QUARTERLY_REVIEW_DAYS,
    BusinessTarget,
    QuarterlyReview,
    UmbrellaPlan,
    UmbrellaSection,
)

TENANT = "tenant-3f"
OTHER_TENANT = "tenant-other"
CREATED = date(2026, 10, 2)
DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL adapter test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)


def umbrella_plan(**overrides) -> UmbrellaPlan:
    tenant = overrides.get("tenant_id", TENANT)
    values = {
        "plan_id": "umbrella-3f",
        "tenant_id": TENANT,
        "owner": "red-principal",
        "workspace": ClientWorkspace(
            workspace_id="ws-3f",
            tenant_id=tenant,
            authorities=(
                ClientAuthority(actor="red-owner", authority="production-owner"),
            ),
        ),
        "template": stage_zero_to_ten_template(),
        "sections": tuple(
            UmbrellaSection(
                section=kind,
                stages=LAUNCH_MAP_SECTION_STAGES[kind],
                objective=f"{kind.value} objective",
            )
            for kind in LAUNCH_MAP_SECTIONS
        ),
        "targets": (
            BusinessTarget(
                target_id="target-leads",
                name="qualified strategy calls",
                metric="booked strategy calls per week",
                goal="20 per week",
                due_on=date(2026, 12, 31),
            ),
        ),
        "reviews": (
            QuarterlyReview(
                reviewed_on=CREATED,
                next_review_on=CREATED + timedelta(days=QUARTERLY_REVIEW_DAYS),
                actor="red-principal",
            ),
        ),
        "created_on": CREATED,
    }
    values.update(overrides)
    return UmbrellaPlan(**values)


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresUmbrellaPlanRepositoryTests(unittest.TestCase):
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
            PostgresUmbrellaPlanRepository,
        )

        self.repository = PostgresUmbrellaPlanRepository(self._connection)
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE umbrella_plans RESTART IDENTITY")
        self._connection.commit()

    def test_the_factory_builds_the_postgres_adapter_from_a_database_url(
        self,
    ) -> None:
        from redops.contexts.portfolio.infrastructure.repositories import (
            PostgresUmbrellaPlanRepository,
            umbrella_plan_repository_from_env,
        )

        repository = umbrella_plan_repository_from_env(DATABASE_URL)
        try:
            self.assertIsInstance(repository, PostgresUmbrellaPlanRepository)
            self.assertEqual((), repository.list(TENANT))
        finally:
            repository.close()

    def test_a_plan_survives_a_reload(self) -> None:
        stored = umbrella_plan()
        self.repository.save(stored)

        self.assertEqual((stored,), self.repository.list(TENANT))
        self.assertEqual(stored, self.repository.get(TENANT, "umbrella-3f"))

    def test_a_same_id_different_body_is_refused(self) -> None:
        from redops.contexts.portfolio.domain.errors import (
            UmbrellaPlanConflictError,
        )

        self.repository.save(umbrella_plan())

        with self.assertRaises(UmbrellaPlanConflictError):
            self.repository.save(umbrella_plan(owner="someone-else"))

    def test_list_returns_only_the_tenant_plans(self) -> None:
        self.repository.save(umbrella_plan(plan_id="umbrella-1"))
        self.repository.save(umbrella_plan(plan_id="umbrella-2"))
        self.repository.save(
            umbrella_plan(tenant_id=OTHER_TENANT, plan_id="umbrella-3")
        )

        listed = self.repository.list(TENANT)

        self.assertEqual({"umbrella-1", "umbrella-2"}, {item.plan_id for item in listed})
        self.assertEqual(1, len(self.repository.list(OTHER_TENANT)))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
