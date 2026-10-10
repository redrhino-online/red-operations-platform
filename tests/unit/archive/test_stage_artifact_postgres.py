"""Behavioral tests for the PostgreSQL stage artifact store (Archive infrastructure).

docs/specs/stage-artifact-archive.md sections 1.2 and 4 (acceptance criterion
A4): the durable adapter proves the append-only immutability (an identical
same-key replay is idempotent and a different body under the same key is
refused), tenant isolation (one client's archive is unreadable for another),
blank-tenant refusal and ``next_version`` allocation against the real schema
created by migration ``0020_stage_artifacts``.

The case skips cleanly when no psycopg, alembic or ``DATABASE_URL`` is present:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/archive/test_stage_artifact_postgres.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from datetime import date
from pathlib import Path

from redops.contexts.archive.domain.entities import StageArtifact
from redops.contexts.archive.domain.errors import (
    StageArtifactVersionConflictError,
    UnscopedStageArtifactError,
)

TENANT = "3fmindset"
OTHER_TENANT = "client-other"
WORKSPACE = "ws-3f"
ON = date(2026, 10, 10)

DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL adapter test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)


def artifact(
    *,
    tenant_id: str = TENANT,
    version: int = 1,
    markdown: str = "Demo: signed scope\n\n## Scope\n\n- item one\n",
    kind: str = "signed-scope",
    asset_id: str = "signed-scope",
) -> StageArtifact:
    return StageArtifact(
        tenant_id=tenant_id,
        workspace_id=WORKSPACE,
        stage_number=0,
        kind=kind,
        asset_id=asset_id,
        version=version,
        markdown=markdown,
        owner="demo-red-principal",
        dropped_on=ON,
    )


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresStageArtifactStoreTests(unittest.TestCase):
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
        from redops.contexts.archive.infrastructure.repositories import (
            PostgresStageArtifactStore,
        )

        self.repository = PostgresStageArtifactStore(self._connection)
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE stage_artifacts RESTART IDENTITY")
        self._connection.commit()

    def test_an_artifact_survives_a_reload_with_its_markdown(self) -> None:
        stored = artifact()

        self.repository.save(stored)

        listed = self.repository.list(TENANT)
        self.assertEqual(1, len(listed))
        reloaded = listed[0]
        self.assertEqual(stored, reloaded)
        self.assertEqual(stored.markdown, reloaded.markdown)
        self.assertEqual(ON, reloaded.dropped_on)
        self.assertIsNone(reloaded.note)

    def test_an_identical_replay_is_idempotent(self) -> None:
        self.repository.save(artifact())
        self.repository.save(artifact())

        self.assertEqual(1, len(self.repository.list(TENANT)))

    def test_a_different_body_under_the_same_key_is_refused(self) -> None:
        self.repository.save(artifact())

        with self.assertRaises(StageArtifactVersionConflictError):
            self.repository.save(artifact(markdown="Demo: rewritten scope"))

        self.assertEqual(1, len(self.repository.list(TENANT)))

    def test_an_artifact_is_not_read_back_for_another_client(self) -> None:
        self.repository.save(artifact())

        self.assertEqual((), self.repository.list(OTHER_TENANT))

    def test_the_list_applies_the_optional_filters(self) -> None:
        self.repository.save(artifact())
        self.repository.save(artifact(version=2))
        self.repository.save(
            artifact(
                kind="intake-questionnaire",
                asset_id="intake-questionnaire",
                markdown="Demo: intake questionnaire",
            )
        )

        self.assertEqual(
            2,
            len(self.repository.list(TENANT, kind="signed-scope")),
        )
        self.assertEqual(
            (2, 1),
            tuple(
                item.version
                for item in self.repository.list(TENANT, asset_id="signed-scope")
            ),
        )
        self.assertEqual(
            1,
            len(
                self.repository.list(
                    TENANT,
                    workspace_id=WORKSPACE,
                    stage_number=0,
                    kind="intake-questionnaire",
                    asset_id="intake-questionnaire",
                )
            ),
        )

    def test_next_version_counts_the_stored_versions(self) -> None:
        self.assertEqual(
            1, self.repository.next_version(TENANT, WORKSPACE, "signed-scope")
        )

        self.repository.save(artifact(version=1))
        self.repository.save(artifact(version=2))

        self.assertEqual(
            3, self.repository.next_version(TENANT, WORKSPACE, "signed-scope")
        )
        self.assertEqual(
            1,
            self.repository.next_version(
                TENANT, WORKSPACE, "intake-questionnaire"
            ),
        )

    def test_a_blank_tenant_is_refused(self) -> None:
        with self.assertRaises(UnscopedStageArtifactError):
            self.repository.list("")

        with self.assertRaises(UnscopedStageArtifactError):
            self.repository.next_version("  ", WORKSPACE, "signed-scope")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
