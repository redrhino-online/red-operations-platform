"""Adapter contract tests for the PostgreSQL ``JourneyReleaseRepository``.

ADR 0003 makes RED's records durable in PostgreSQL, and SPEC.md section 6 says
infrastructure adapters implement ports. These tests exercise the real
``PostgresJourneyReleaseRepository`` against the local compose database: the
schema is created by the committed migration ``0015_journey_releases`` (SPEC.md
section 6), and an authorized release saved through the adapter is persisted and
reloaded as an aggregate with its grounding stage 9 QA, its exact released asset
versions, its routing, configuration digest and rollback reference (SPEC.md
sections 3 and 4).

They skip cleanly when no psycopg driver, no alembic or no ``DATABASE_URL`` is
present, so the domain-only test interpreter still runs the rest of the suite.
Run them with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/execution/test_journey_release_postgres.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from pathlib import Path

from redops.contexts.execution.domain.journey_release import JourneyRelease
from redops.contexts.governance.domain.value_objects import StageAssetVersion

from .fixtures import TENANT, ready_for_traffic

OTHER_TENANT = "client-other"
DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL adapter test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)


def asset(kind: str = "pages", **overrides) -> StageAssetVersion:
    values = {
        "asset_id": f"asset-{kind}",
        "tenant_id": TENANT,
        "kind": kind,
        "version": 1,
    }
    values.update(overrides)
    return StageAssetVersion(**values)


def release(**overrides) -> JourneyRelease:
    values = {
        "release_id": "release-1",
        "tenant_id": TENANT,
        "qa": ready_for_traffic(),
        "assets": (asset("pages"), asset("forms")),
        "routing": "route://3f/main",
        "configuration_digest": "sha256:config",
        "rollback_ref": "release://3f/previous",
    }
    values.update(overrides)
    return JourneyRelease(**values)


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresJourneyReleaseRepositoryTests(unittest.TestCase):
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
        from redops.contexts.execution.infrastructure.repositories import (
            PostgresJourneyReleaseRepository,
        )

        self.repository = PostgresJourneyReleaseRepository(self._connection)
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE journey_releases RESTART IDENTITY")
        self._connection.commit()

    def test_the_factory_builds_the_postgres_adapter_from_a_database_url(
        self,
    ) -> None:
        from redops.contexts.execution.infrastructure.repositories import (
            PostgresJourneyReleaseRepository,
            journey_release_repository_from_env,
        )

        repository = journey_release_repository_from_env(DATABASE_URL)
        try:
            self.assertIsInstance(repository, PostgresJourneyReleaseRepository)
            self.assertIsNone(repository.get(TENANT, "release-1"))
        finally:
            repository.close()

    def test_a_release_survives_a_reload_with_its_qa_and_assets(self) -> None:
        stored = release()
        self.repository.save(stored)

        reloaded = self.repository.get(TENANT, stored.release_id)

        self.assertEqual(stored, reloaded)
        self.assertTrue(reloaded.is_authorized)
        self.assertEqual({"pages", "forms"}, reloaded.released_kinds)

    def test_a_same_id_different_body_is_refused(self) -> None:
        from redops.contexts.execution.domain.errors import (
            JourneyReleaseVersionConflictError,
        )

        self.repository.save(release())

        with self.assertRaises(JourneyReleaseVersionConflictError):
            self.repository.save(release(routing="route://3f/changed"))

    def test_list_returns_only_the_tenant_releases_ordered_by_id(self) -> None:
        self.repository.save(release(release_id="release-b"))
        self.repository.save(release(release_id="release-a"))

        listed = self.repository.list(TENANT)

        self.assertEqual(
            ("release-a", "release-b"),
            tuple(item.release_id for item in listed),
        )
        self.assertEqual((), self.repository.list(OTHER_TENANT))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
