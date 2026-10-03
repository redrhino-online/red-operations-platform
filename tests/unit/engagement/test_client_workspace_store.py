"""Behavioral tests for the client workspace store (Engagement application).

Rules under test come from SPEC.md sections 3, 4 and 9:
- The ClientWorkspace is the tenant root; every child resource belongs to exactly
  one client, and every read and write carries ``tenant_id`` (SPEC.md section 3).
- A lifecycle advance and a new authority are persisted, and the append-only
  lifecycle transition log survives a reload (SPEC.md section 4).
- One client's workspace cannot be resolved or listed for another (SPEC.md
  sections 3 and 9).

The durable PostgreSQL case skips cleanly when no psycopg, alembic or
``DATABASE_URL`` is present:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/engagement/test_client_workspace_store.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from datetime import date
from pathlib import Path

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    UnscopedClientWorkspaceError,
)
from redops.contexts.engagement.domain.value_objects import (
    ClientAuthority,
    EngagementLifecycle,
)
from redops.contexts.engagement.infrastructure.mappers import (
    workspace_from_payload,
    workspace_to_payload,
)
from redops.contexts.engagement.infrastructure.repositories import (
    InMemoryClientWorkspaceStore,
)

TENANT = "3fmindset"
OTHER_TENANT = "client-other"
ON = date(2026, 10, 3)

DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL adapter test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)


def workspace(
    workspace_id: str = "3f-engagement",
    tenant_id: str = TENANT,
) -> ClientWorkspace:
    return ClientWorkspace(
        workspace_id=workspace_id,
        tenant_id=tenant_id,
        authorities=(
            ClientAuthority(actor="red-principal", authority="owner"),
            ClientAuthority(actor="3f-approver", authority="client-designated-authority"),
        ),
    )


class InMemoryClientWorkspaceStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryClientWorkspaceStore()

    def test_a_saved_workspace_is_resolved_by_workspace_id(self) -> None:
        stored = workspace()

        self.store.save(stored)

        self.assertEqual(stored, self.store.get(TENANT, "3f-engagement"))

    def test_an_unknown_workspace_resolves_to_none(self) -> None:
        self.store.save(workspace())

        self.assertIsNone(self.store.get(TENANT, "missing"))
        self.assertIsNone(self.store.get(OTHER_TENANT, "3f-engagement"))

    def test_list_is_tenant_scoped_and_ordered_by_workspace_id(self) -> None:
        self.store.save(workspace(workspace_id="b-engagement"))
        self.store.save(workspace(workspace_id="a-engagement"))
        self.store.save(workspace(workspace_id="other", tenant_id=OTHER_TENANT))

        listed = self.store.list(TENANT)

        self.assertEqual(
            ["a-engagement", "b-engagement"],
            [item.workspace_id for item in listed],
        )

    def test_a_lifecycle_advance_and_transitions_survive_a_reload(self) -> None:
        stored = workspace()
        stored.advance_to(
            EngagementLifecycle.DIAGNOSIS,
            actor="red-principal",
            reason="stage 0 accepted",
            on=ON,
            correlation_id="corr-1",
        )
        self.store.save(stored)

        reloaded = self.store.get(TENANT, "3f-engagement")

        self.assertEqual(EngagementLifecycle.DIAGNOSIS, reloaded.lifecycle)
        self.assertEqual(1, len(reloaded.transitions))
        self.assertEqual("corr-1", reloaded.transitions[0].correlation_id)

    def test_a_paused_workspace_remembers_the_state_to_resume_to(self) -> None:
        stored = workspace()
        stored.advance_to(
            EngagementLifecycle.DIAGNOSIS,
            actor="red-principal",
            reason="stage 0 accepted",
            on=ON,
            correlation_id="corr-1",
        )
        stored.pause(
            actor="red-principal",
            reason="client pause",
            on=ON,
            correlation_id="corr-2",
        )
        self.store.save(stored)

        reloaded = self.store.get(TENANT, "3f-engagement")
        reloaded.resume(
            actor="red-principal",
            reason="client resumed",
            on=ON,
            correlation_id="corr-3",
        )

        self.assertEqual(EngagementLifecycle.DIAGNOSIS, reloaded.lifecycle)

    def test_a_saved_workspace_is_independent_of_later_caller_mutation(self) -> None:
        stored = workspace()
        self.store.save(stored)

        stored.advance_to(
            EngagementLifecycle.DIAGNOSIS,
            actor="red-principal",
            reason="stage 0 accepted",
            on=ON,
            correlation_id="corr-1",
        )

        self.assertEqual(
            EngagementLifecycle.INTAKE,
            self.store.get(TENANT, "3f-engagement").lifecycle,
        )

    def test_an_unscoped_read_is_refused(self) -> None:
        for tenant in ("", "   "):
            with self.subTest(tenant=tenant):
                with self.assertRaises(UnscopedClientWorkspaceError):
                    self.store.list(tenant)
                with self.assertRaises(UnscopedClientWorkspaceError):
                    self.store.get(tenant, "3f-engagement")

    def test_a_workspace_without_a_tenant_cannot_be_built(self) -> None:
        from redops.contexts.engagement.domain.errors import (
            InvalidClientWorkspaceError,
        )

        with self.assertRaises(InvalidClientWorkspaceError):
            workspace(tenant_id="")


class ClientWorkspaceMapperTests(unittest.TestCase):
    def test_a_workspace_round_trips_with_its_registries(self) -> None:
        stored = workspace()
        stored.attach("source-1", TENANT)

        self.assertEqual(stored, workspace_from_payload(workspace_to_payload(stored)))

    def test_a_payload_the_domain_would_reject_raises(self) -> None:
        payload = workspace_to_payload(workspace())
        payload["authorities"] = []

        with self.assertRaises(ValueError):
            workspace_from_payload(payload)


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresClientWorkspaceStoreTests(unittest.TestCase):
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
        from redops.contexts.engagement.infrastructure.repositories import (
            PostgresClientWorkspaceStore,
        )

        self.repository = PostgresClientWorkspaceStore(self._connection)
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE client_workspaces RESTART IDENTITY")
        self._connection.commit()

    def test_a_workspace_survives_a_reload_with_its_authorities(self) -> None:
        stored = workspace()
        self.repository.save(stored)

        reloaded = self.repository.get(TENANT, "3f-engagement")

        self.assertEqual(stored, reloaded)
        self.assertTrue(reloaded.has_authority("3f-approver"))

    def test_resaving_updates_the_workspace_in_place(self) -> None:
        stored = workspace()
        self.repository.save(stored)
        stored.advance_to(
            EngagementLifecycle.DIAGNOSIS,
            actor="red-principal",
            reason="stage 0 accepted",
            on=ON,
            correlation_id="corr-1",
        )
        self.repository.save(stored)

        reloaded = self.repository.get(TENANT, "3f-engagement")

        self.assertEqual(EngagementLifecycle.DIAGNOSIS, reloaded.lifecycle)
        self.assertEqual(1, len(self.repository.list(TENANT)))

    def test_a_workspace_is_not_read_back_for_another_client(self) -> None:
        self.repository.save(workspace())

        self.assertIsNone(self.repository.get(OTHER_TENANT, "3f-engagement"))
        self.assertEqual((), self.repository.list(OTHER_TENANT))

    def test_a_blank_tenant_is_refused(self) -> None:
        with self.assertRaises(UnscopedClientWorkspaceError):
            self.repository.list("")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
