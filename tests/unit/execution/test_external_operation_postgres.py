"""Adapter contract tests for the PostgreSQL ``ExternalOperationStore``.

ADR 0003 makes RED's records durable in PostgreSQL, SPEC.md section 6 says
infrastructure adapters implement ports, and SPEC.md section 11 requires
"duplicate delivery creates one external operation". The process-local
``InMemoryExternalOperationStore`` cannot keep that guarantee across a process
restart, so this suite exercises the durable ``PostgresExternalOperationStore``
against the local compose database: the schema is created by the committed
migration ``0018_external_operations`` (SPEC.md section 6) and the unique
``(tenant_id, idempotency_key)`` key makes an already-recorded external
operation impossible to re-send after a restart (SPEC.md sections 9 and 11).

They skip cleanly when no psycopg driver, no alembic or no ``DATABASE_URL`` is
present, so the domain-only test interpreter still runs the rest of the suite.
Run them with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/execution/test_external_operation_postgres.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from datetime import date
from pathlib import Path

from redops.contexts.execution.domain.connector import (
    ConnectorEffect,
    ExternalOperation,
)
from redops.contexts.execution.domain.errors import (
    ConnectorIdempotencyConflictError,
    ConnectorTenantBoundaryError,
)

TENANT = "3fmindset"
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


def effect(**overrides: object) -> ConnectorEffect:
    values: dict[str, object] = {
        "tenant_id": TENANT,
        "idempotency_key": "key-1",
        "connector": "crm",
        "target": "contact-42",
        "payload_digest": "sha256:abc",
        "requested_on": TODAY,
    }
    values.update(overrides)
    return ConnectorEffect(**values)


def operation(**overrides: object) -> ExternalOperation:
    values: dict[str, object] = {
        "effect": effect(),
        "external_ref": "crm-op-1",
        "delivered_on": TODAY,
    }
    values.update(overrides)
    return ExternalOperation(**values)


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresExternalOperationStoreTests(unittest.TestCase):
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
        from redops.contexts.execution.infrastructure.connectors import (
            PostgresExternalOperationStore,
        )

        self.store = PostgresExternalOperationStore(self._connection)
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE external_operations RESTART IDENTITY")
        self._connection.commit()

    def test_the_factory_builds_the_postgres_adapter_from_a_database_url(
        self,
    ) -> None:
        from redops.contexts.execution.infrastructure.connectors import (
            PostgresExternalOperationStore,
            external_operation_store_from_env,
        )

        store = external_operation_store_from_env(DATABASE_URL)
        try:
            self.assertIsInstance(store, PostgresExternalOperationStore)
            self.assertIsNone(store.get(TENANT, "key-1"))
        finally:
            store.close()

    def test_a_recorded_operation_survives_a_reload(self) -> None:
        self.store.record(operation())

        reloaded = self.store.get(TENANT, "key-1")

        self.assertIsNotNone(reloaded)
        self.assertEqual(TENANT, reloaded.effect.tenant_id)
        self.assertEqual("crm-op-1", reloaded.external_ref)
        self.assertEqual(TODAY, reloaded.delivered_on)
        self.assertEqual("sha256:abc", reloaded.effect.payload_digest)

    def test_a_duplicate_record_is_idempotent(self) -> None:
        self.store.record(operation())
        self.store.record(operation())

        with self._connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM external_operations "
                "WHERE tenant_id = %s AND idempotency_key = %s",
                (TENANT, "key-1"),
            )
            self.assertEqual(1, cursor.fetchone()[0])

    def test_a_reused_key_with_different_content_is_refused(self) -> None:
        self.store.record(operation())

        with self.assertRaises(ConnectorIdempotencyConflictError):
            self.store.record(
                operation(
                    effect=effect(payload_digest="sha256:changed"),
                    external_ref="crm-op-2",
                )
            )

        reloaded = self.store.get(TENANT, "key-1")
        self.assertEqual("sha256:abc", reloaded.effect.payload_digest)
        self.assertEqual("crm-op-1", reloaded.external_ref)

    def test_the_same_key_for_another_tenant_is_independent(self) -> None:
        self.store.record(operation())
        self.store.record(
            operation(
                effect=effect(tenant_id=OTHER_TENANT),
                external_ref="crm-op-other",
            )
        )

        self.assertEqual(
            "crm-op-1", self.store.get(TENANT, "key-1").external_ref
        )
        self.assertEqual(
            "crm-op-other", self.store.get(OTHER_TENANT, "key-1").external_ref
        )

    def test_a_blank_tenant_is_refused_on_read_and_write(self) -> None:
        with self.assertRaises(ConnectorTenantBoundaryError):
            self.store.get("", "key-1")
        with self.assertRaises(ConnectorTenantBoundaryError):
            self.store.record(operation(effect=effect(tenant_id="  ")))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
