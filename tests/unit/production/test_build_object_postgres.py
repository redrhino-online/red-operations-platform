"""Adapter contract tests for the PostgreSQL ``BuildObjectRepository``.

ADR 0003 makes RED's records durable in PostgreSQL, and SPEC.md section 6 says
infrastructure adapters implement ports. These tests exercise the real
``PostgresBuildObjectRepository`` against the local compose database: the schema
is created by the committed migration ``0013_build_objects`` (SPEC.md section 6),
and a build saved through the adapter is persisted and reloaded as an aggregate
with its identity, owner, next action, state and append-only transition history
(SPEC.md sections 3 and 4).

They skip cleanly when no psycopg driver, no alembic or no ``DATABASE_URL`` is
present, so the domain-only test interpreter still runs the rest of the suite.
Run them with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/production/test_build_object_postgres.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from datetime import date
from pathlib import Path

from redops.contexts.production.domain.entities import BuildObject
from redops.contexts.production.domain.errors import BuildTenantBoundaryError
from redops.contexts.production.domain.value_objects import BuildState

TENANT = "client-3f"
OTHER_TENANT = "client-other"
TODAY = date(2026, 10, 3)
DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL adapter test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)


def build_object(**overrides) -> BuildObject:
    values = {
        "build_id": "build-1",
        "tenant_id": TENANT,
        "build_type": "authority-amplifier-video",
        "purpose": "stage 7 creative",
        "audience": "3f prospects",
        "owner": "production-manager",
        "next_action": "record the video",
        "refs": frozenset({"authority-amplifier-script@1"}),
    }
    values.update(overrides)
    return BuildObject(**values)


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresBuildObjectRepositoryTests(unittest.TestCase):
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
        from redops.contexts.production.infrastructure.repositories import (
            PostgresBuildObjectRepository,
        )

        self.repository = PostgresBuildObjectRepository(self._connection)
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE build_objects RESTART IDENTITY")
        self._connection.commit()

    def test_the_factory_builds_the_postgres_adapter_from_a_database_url(
        self,
    ) -> None:
        from redops.contexts.production.infrastructure.repositories import (
            PostgresBuildObjectRepository,
            build_object_repository_from_env,
        )

        repository = build_object_repository_from_env(DATABASE_URL)
        try:
            self.assertIsInstance(repository, PostgresBuildObjectRepository)
            self.assertIsNone(repository.get(TENANT, "build-1"))
        finally:
            repository.close()

    def test_a_build_survives_a_reload_with_its_transition_history(self) -> None:
        build = build_object()
        build.mark_ready(
            actor="production-manager",
            reason="sources delivered",
            on=TODAY,
            correlation_id="corr-1",
        )
        self.repository.save(build)

        reloaded = self.repository.get(TENANT, build.build_id)

        self.assertEqual(build.build_id, reloaded.build_id)
        self.assertIs(BuildState.READY, reloaded.state)
        self.assertEqual(1, len(reloaded.transitions))
        self.assertEqual("corr-1", reloaded.transitions[0].correlation_id)

    def test_a_later_snapshot_replaces_the_stored_build(self) -> None:
        build = build_object()
        self.repository.save(build)
        build.mark_ready(
            actor="production-manager",
            reason="sources delivered",
            on=TODAY,
            correlation_id="corr-1",
        )
        self.repository.save(build)

        self.assertIs(
            BuildState.READY, self.repository.get(TENANT, "build-1").state
        )

    def test_list_returns_only_the_tenant_builds_ordered_by_id(self) -> None:
        self.repository.save(build_object(build_id="build-b"))
        self.repository.save(build_object(build_id="build-a"))
        self.repository.save(
            build_object(build_id="build-x", tenant_id=OTHER_TENANT)
        )

        listed = self.repository.list(TENANT)

        self.assertEqual(("build-a", "build-b"), tuple(b.build_id for b in listed))

    def test_a_blank_tenant_is_refused_on_read(self) -> None:
        with self.assertRaises(BuildTenantBoundaryError):
            self.repository.get("", "build-1")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
