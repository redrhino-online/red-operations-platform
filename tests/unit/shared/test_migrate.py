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

import importlib
import importlib.util
import os
import unittest

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
                cursor.execute("SELECT version_num FROM alembic_version")
                self.assertEqual(cursor.fetchone()[0], "0007_funnel_integrations")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
