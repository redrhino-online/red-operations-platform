"""Contract tests for the programmatic migration runner.

ADR 0003 ships RED's schema as committed migrations and SPEC.md section 10 makes
applying them a distinct deployment step before the API serves. These tests pin
that step's command: a blank ``DATABASE_URL`` is a named configuration error and
never a silent no-op, and a configured database is migrated to ``head``
idempotently, leaving the ``gate_decisions`` table the durable ledger needs.

The database case skips cleanly when no psycopg driver, no alembic or no
``DATABASE_URL`` is present, so the domain-only interpreter still runs the rest
of the suite. Run it with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/shared/test_migrate.py -q
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import os
import unittest
from pathlib import Path

from redops.shared.persistence.migrate import (
    MigrationConfigurationError,
    run_migrations,
)

DATABASE_URL = os.environ.get("DATABASE_URL")
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "migration runner test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)


class MigrationConfigurationTests(unittest.TestCase):
    """The runner refuses a blank URL rather than silently skipping schema."""

    def test_blank_url_raises_named_error(self) -> None:
        for blank in ("", "   "):
            with self.subTest(blank=repr(blank)):
                with self.assertRaises(MigrationConfigurationError):
                    run_migrations(blank)

    def test_main_without_environment_raises(self) -> None:
        from redops.shared.persistence import migrate

        previous = os.environ.pop("DATABASE_URL", None)
        try:
            with self.assertRaises(MigrationConfigurationError):
                migrate.main()
        finally:
            if previous is not None:
                os.environ["DATABASE_URL"] = previous


@unittest.skipUnless(RUN, SKIP_REASON)
class MigrationRunnerTests(unittest.TestCase):
    """The runner applies the committed migration set to a live database."""

    def test_applies_head_idempotently(self) -> None:
        psycopg = importlib.import_module("psycopg")

        run_migrations(DATABASE_URL)
        run_migrations(DATABASE_URL)

        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT to_regclass('public.gate_decisions')")
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute("SELECT to_regclass('public.stage_runs')")
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute("SELECT to_regclass('public.method_versions')")
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute("SELECT to_regclass('public.offer_versions')")
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT to_regclass('public.campaign_messages')"
                )
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT to_regclass('public.authority_amplifiers')"
                )
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT to_regclass('public.funnel_integrations')"
                )
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute("SELECT to_regclass('public.launch_qas')")
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute("SELECT to_regclass('public.workflow_runs')")
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT to_regclass('public.client_workspaces')"
                )
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute("SELECT to_regclass('public.source_records')")
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute("SELECT to_regclass('public.claims')")
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute("SELECT to_regclass('public.build_objects')")
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT to_regclass('public.metric_definitions')"
                )
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT to_regclass('public.measurement_records')"
                )
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT to_regclass('public.journey_releases')"
                )
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT to_regclass('public.intervention_dismissals')"
                )
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute("SELECT to_regclass('public.opportunities')")
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute(
                    "SELECT to_regclass('public.external_operations')"
                )
                self.assertIsNotNone(cursor.fetchone()[0])
                cursor.execute("SELECT version_num FROM alembic_version")
                self.assertEqual(cursor.fetchone()[0], "0018_external_operations")


_REPO_ROOT = Path(__file__).resolve().parents[3]
_VERSIONS_DIR = (
    _REPO_ROOT
    / "backend"
    / "redops"
    / "shared"
    / "persistence"
    / "migrations"
    / "versions"
)
_MIGRATIONS_DIR = _VERSIONS_DIR.parent
_BACKEND_DIR = _MIGRATIONS_DIR.parents[3]


def _migration_source(path: Path) -> dict[str, object]:
    """Return the module-level ``revision``/``down_revision`` values and AST."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, object] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in ("revision", "down_revision")
            and isinstance(node.value, ast.Constant)
        ):
            values[node.targets[0].id] = node.value.value
    values["tree"] = tree
    return values


class MigrationReversibilityTests(unittest.TestCase):
    """Every committed migration is written for both directions (ADR 0010).

    SPEC.md section 6 requires migration scripts "written for both directions (a
    working downgrade that removes exactly what its upgrade created)" and SPEC.md
    section 10 makes the release rollback depend on it. These tests enforce the
    authoring rule per cycle without a database; the live ``upgrade -> downgrade
    -> upgrade`` round trip runs in the production-readiness rollback drill
    (``MigrationRoundTripTests``, opt-in).
    """

    def test_every_migration_defines_a_downgrade(self) -> None:
        files = sorted(_VERSIONS_DIR.glob("0*.py"))
        self.assertTrue(files, f"no migration files found in {_VERSIONS_DIR}")
        for path in files:
            with self.subTest(migration=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                downgrade = next(
                    (
                        node
                        for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == "downgrade"
                    ),
                    None,
                )
                self.assertIsNotNone(downgrade, f"{path.name} defines no downgrade()")
                body = [
                    stmt
                    for stmt in downgrade.body
                    if not (
                        isinstance(stmt, ast.Expr)
                        and isinstance(stmt.value, ast.Constant)
                        and isinstance(stmt.value.value, str)
                    )
                ]
                self.assertTrue(body, f"{path.name} downgrade() is empty")
                self.assertFalse(
                    all(isinstance(stmt, ast.Pass) for stmt in body),
                    f"{path.name} downgrade() only passes; it must reverse upgrade()",
                )

    def test_revision_chain_is_linear(self) -> None:
        entries = []
        for path in sorted(_VERSIONS_DIR.glob("0*.py")):
            values = _migration_source(path)
            entries.append((values.get("revision"), values.get("down_revision"), path.name))
        entries.sort(key=lambda entry: entry[0] or "")
        self.assertTrue(entries, f"no migration files found in {_VERSIONS_DIR}")
        self.assertIsNone(
            entries[0][1], f"{entries[0][2]} must be the base migration (down_revision None)"
        )
        for previous, current in zip(entries, entries[1:]):
            self.assertEqual(
                current[1],
                previous[0],
                f"{current[2]} down_revision {current[1]!r} does not chain from {previous[0]!r}",
            )


_ROUNDTRIP = RUN and os.environ.get("REDOP_MIGRATION_ROUNDTRIP") == "1"


@unittest.skipUnless(
    _ROUNDTRIP,
    "set REDOP_MIGRATION_ROUNDTRIP=1 (with DATABASE_URL) to run the reversibility drill",
)
class MigrationRoundTripTests(unittest.TestCase):
    """The live upgrade -> downgrade -> upgrade round trip (ADR 0010).

    Opt-in because ``downgrade base`` drops the schema of the target database;
    this is the drill the production-readiness phase runs, not a per-cycle test.
    """

    def test_upgrade_downgrade_upgrade(self) -> None:
        from alembic import command
        from alembic.config import Config

        url = DATABASE_URL
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]
        config = Config()
        config.set_main_option("script_location", str(_MIGRATIONS_DIR))
        config.set_main_option("prepend_sys_path", str(_BACKEND_DIR))
        config.set_main_option("path_separator", "os")
        config.set_main_option("sqlalchemy.url", url)

        psycopg = importlib.import_module("psycopg")

        command.upgrade(config, "head")
        command.downgrade(config, "base")
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT to_regclass('public.gate_decisions')")
                self.assertIsNone(cursor.fetchone()[0], "downgrade did not drop the schema")

        command.upgrade(config, "head")
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT to_regclass('public.gate_decisions')")
                self.assertIsNotNone(cursor.fetchone()[0], "re-upgrade did not restore the schema")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
