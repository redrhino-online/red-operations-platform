"""Adapter contract tests for the workflow ``WorkflowRunStore`` (SPEC.md 7, 11).

SPEC.md section 7 requires durable run state persisted before side effects so a
worker can resume from committed steps, and section 11 requires a restarting
worker to preserve a waiting workflow. ADR 0005 adds idempotent resumption.
These tests exercise the ``InMemoryWorkflowRunStore`` reference adapter and the
``PostgresWorkflowRunStore`` durable adapter against the same port contract: a
reloaded run keeps its pinned definition version, completed steps, in-progress
step, pending approval and append-only transition log, is tenant scoped, and
refuses an unscoped read or write.

The PostgreSQL cases skip cleanly without a driver, alembic or ``DATABASE_URL``.
Run them with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/workflows/test_workflow_run_store.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from datetime import date
from pathlib import Path

from redops.workflows.domain.entities import WorkflowRun
from redops.workflows.domain.errors import CrossTenantWorkflowRunError
from redops.workflows.domain.value_objects import (
    WorkflowDefinition,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepKind,
)
from redops.workflows.infrastructure.repositories import (
    InMemoryWorkflowRunStore,
    WorkflowRunConfigurationError,
    workflow_run_store_from_env,
)

DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL workflow store test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)

ON = date(2026, 10, 3)
TENANT = "tenant-3f"
OTHER = "tenant-other"
ACTOR = "red-worker"
CORRELATION = "corr-run-1"


def definition(version: str = "1.0.0") -> WorkflowDefinition:
    return WorkflowDefinition(
        definition_id="authority-amplifier",
        version=version,
        steps=(
            WorkflowStep("extract-claims"),
            WorkflowStep("client-approval", WorkflowStepKind.APPROVAL),
            WorkflowStep("publish-asset"),
        ),
    )


def waiting_run() -> WorkflowRun:
    """A run parked on a human approval step, as a restart would find it."""
    run = WorkflowRun(run_id="run-1", tenant_id=TENANT, definition=definition())
    run.start(actor=ACTOR, reason="workflow started", on=ON, correlation_id=CORRELATION)
    run.begin_step(actor=ACTOR, reason="extract began", on=ON, correlation_id=CORRELATION)
    run.commit_step(actor=ACTOR, reason="extract done", on=ON, correlation_id=CORRELATION)
    run.await_approval(
        actor=ACTOR, reason="awaiting client sign-off", on=ON, correlation_id=CORRELATION
    )
    return run


def interrupted_run() -> WorkflowRun:
    """A run whose step side effect had not committed before a crash."""
    run = WorkflowRun(run_id="run-2", tenant_id=TENANT, definition=definition())
    run.start(actor=ACTOR, reason="workflow started", on=ON, correlation_id=CORRELATION)
    run.begin_step(actor=ACTOR, reason="extract began", on=ON, correlation_id=CORRELATION)
    return run


class InMemoryWorkflowRunStoreTests(unittest.TestCase):
    """The port contract, exercised with the process-local reference adapter."""

    def setUp(self) -> None:
        self.store = InMemoryWorkflowRunStore()

    def test_a_waiting_run_survives_a_reload_with_its_pinned_definition(self) -> None:
        run = waiting_run()
        self.store.save(run)

        reloaded = self.store.get("run-1", tenant_id=TENANT)

        self.assertEqual(WorkflowRunStatus.AWAITING_APPROVAL, reloaded.status)
        self.assertEqual("client-approval", reloaded.pending_approval)
        self.assertEqual(("extract-claims",), reloaded.completed_steps)
        self.assertEqual("authority-amplifier", reloaded.definition.definition_id)
        self.assertEqual("1.0.0", reloaded.definition.version)
        self.assertEqual(run.transitions, reloaded.transitions)

    def test_an_interrupted_step_is_persisted_for_resume(self) -> None:
        self.store.save(interrupted_run())

        reloaded = self.store.get("run-2", tenant_id=TENANT)

        self.assertEqual(WorkflowRunStatus.RUNNING, reloaded.status)
        self.assertEqual("extract-claims", reloaded.in_progress_step)
        self.assertEqual("extract-claims", reloaded.resume_step().name)

    def test_a_committed_resave_advances_the_run_without_losing_history(self) -> None:
        run = waiting_run()
        self.store.save(run)
        run.approve(
            actor="client-approver",
            reason="client approved",
            on=ON,
            correlation_id=CORRELATION,
        )
        self.store.save(run)

        reloaded = self.store.get("run-1", tenant_id=TENANT)

        self.assertEqual(WorkflowRunStatus.RUNNING, reloaded.status)
        self.assertIsNone(reloaded.pending_approval)
        self.assertEqual(("extract-claims", "client-approval"), reloaded.completed_steps)
        self.assertEqual(3, len(reloaded.transitions))

    def test_a_stored_run_is_independent_of_the_caller(self) -> None:
        run = waiting_run()
        self.store.save(run)

        run.fail(actor=ACTOR, reason="mutated after save", on=ON, correlation_id=CORRELATION)

        self.assertEqual(
            WorkflowRunStatus.AWAITING_APPROVAL,
            self.store.get("run-1", tenant_id=TENANT).status,
        )

    def test_a_run_is_not_read_back_for_another_client(self) -> None:
        self.store.save(waiting_run())

        self.assertIsNone(self.store.get("run-1", tenant_id=OTHER))

    def test_save_refuses_an_unscoped_run(self) -> None:
        run = WorkflowRun(run_id="run-1", tenant_id=TENANT, definition=definition())
        run.tenant_id = "   "

        with self.assertRaises(CrossTenantWorkflowRunError):
            self.store.save(run)

    def test_get_requires_a_tenant(self) -> None:
        with self.assertRaises(CrossTenantWorkflowRunError):
            self.store.get("run-1", tenant_id="")

    def test_list_resumable_returns_only_runs_with_a_due_step(self) -> None:
        self.store.save(waiting_run())
        self.store.save(interrupted_run())

        self.assertEqual(("run-2",), self.store.list_resumable(tenant_id=TENANT))

    def test_list_resumable_is_scoped_to_the_requested_client(self) -> None:
        self.store.save(waiting_run())
        self.store.save(interrupted_run())

        self.assertEqual((), self.store.list_resumable(tenant_id=OTHER))

    def test_list_resumable_refuses_an_unscoped_scan(self) -> None:
        with self.assertRaises(CrossTenantWorkflowRunError):
            self.store.list_resumable(tenant_id="")

    def test_the_factory_builds_the_in_memory_store_without_a_database(self) -> None:
        store = workflow_run_store_from_env(None)
        self.assertIsInstance(store, InMemoryWorkflowRunStore)
        self.assertIsInstance(workflow_run_store_from_env(""), InMemoryWorkflowRunStore)

    def test_a_set_url_without_a_driver_raises_a_named_error(self) -> None:
        from redops.workflows.infrastructure import repositories

        previous = repositories.psycopg
        repositories.psycopg = None
        try:
            with self.assertRaises(WorkflowRunConfigurationError):
                workflow_run_store_from_env("postgresql://example/redops")
        finally:
            repositories.psycopg = previous


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresWorkflowRunStoreTests(unittest.TestCase):
    """The port contract, exercised against the real PostgreSQL schema."""

    @classmethod
    def setUpClass(cls) -> None:
        from alembic import command
        from alembic.config import Config

        cls._psycopg = importlib.import_module("psycopg")
        cls._jsonb = importlib.import_module("psycopg.types.json").Jsonb
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
        from redops.workflows.infrastructure.repositories import (
            PostgresWorkflowRunStore,
        )

        self.store = PostgresWorkflowRunStore(self._connection)
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE workflow_runs RESTART IDENTITY")
        self._connection.commit()

    def test_the_factory_builds_the_postgres_store_from_a_database_url(self) -> None:
        from redops.workflows.infrastructure.repositories import (
            PostgresWorkflowRunStore,
        )

        store = workflow_run_store_from_env(DATABASE_URL)
        try:
            self.assertIsInstance(store, PostgresWorkflowRunStore)
            self.assertIsNone(store.get("run-1", tenant_id=TENANT))
        finally:
            store.close()

    def test_a_waiting_run_survives_a_reload_and_resave_upserts(self) -> None:
        run = waiting_run()
        self.store.save(run)

        reloaded = self.store.get("run-1", tenant_id=TENANT)
        self.assertEqual(WorkflowRunStatus.AWAITING_APPROVAL, reloaded.status)
        self.assertEqual("client-approval", reloaded.pending_approval)
        self.assertEqual("1.0.0", reloaded.definition.version)

        run.approve(
            actor="client-approver",
            reason="client approved",
            on=ON,
            correlation_id=CORRELATION,
        )
        self.store.save(run)

        reloaded_again = self.store.get("run-1", tenant_id=TENANT)
        self.assertEqual(WorkflowRunStatus.RUNNING, reloaded_again.status)
        self.assertEqual(3, len(reloaded_again.transitions))

    def test_an_interrupted_step_is_persisted_for_resume(self) -> None:
        self.store.save(interrupted_run())

        reloaded = self.store.get("run-2", tenant_id=TENANT)

        self.assertEqual("extract-claims", reloaded.in_progress_step)
        self.assertEqual("extract-claims", reloaded.resume_step().name)

    def test_a_run_is_not_read_back_for_another_client(self) -> None:
        self.store.save(waiting_run())

        self.assertIsNone(self.store.get("run-1", tenant_id=OTHER))

    def test_list_resumable_returns_only_the_clients_due_runs(self) -> None:
        self.store.save(waiting_run())
        self.store.save(interrupted_run())

        self.assertEqual(("run-2",), self.store.list_resumable(tenant_id=TENANT))
        self.assertEqual((), self.store.list_resumable(tenant_id=OTHER))

    def test_reload_refuses_a_stored_run_the_domain_would_reject(self) -> None:
        from redops.workflows.infrastructure.mappers import workflow_run_to_payload

        payload = workflow_run_to_payload(waiting_run())
        payload["completed_steps"] = ["client-approval"]
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO workflow_runs (
                    tenant_id, run_id, status, definition_id,
                    definition_version, run
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    TENANT,
                    "run-1",
                    WorkflowRunStatus.AWAITING_APPROVAL.value,
                    "authority-amplifier",
                    "1.0.0",
                    self._jsonb(payload),
                ),
            )
        self._connection.commit()

        from redops.workflows.domain.errors import InvalidWorkflowDefinitionError

        with self.assertRaises(InvalidWorkflowDefinitionError):
            self.store.get("run-1", tenant_id=TENANT)


if __name__ == "__main__":
    unittest.main()
