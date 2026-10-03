"""PostgreSQL and in-memory adapters for the ``WorkflowRunStore`` port.

ADR 0003 makes RED's durable records live in PostgreSQL; SPEC.md section 7 and
ADR 0005 require workflow run state to survive a worker restart so a waiting
approval is preserved and resumption is idempotent. Two adapters implement the
same port: ``InMemoryWorkflowRunStore`` is the process-local reference adapter
used by application and API tests, and ``PostgresWorkflowRunStore`` is the
durable adapter whose table is created by migration ``0009_workflow_runs``.
Row serialisation lives in ``mappers.py``.
"""

from __future__ import annotations

from typing import Any

from redops.workflows.application.ports import WorkflowRunStore
from redops.workflows.domain.entities import WorkflowRun
from redops.workflows.domain.errors import CrossTenantWorkflowRunError
from redops.workflows.infrastructure.mappers import (
    workflow_run_from_payload,
    workflow_run_to_payload,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class WorkflowRunConfigurationError(RuntimeError):
    """The workflow run store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept
    run state that vanishes on restart and could not resume a waiting workflow
    (SPEC.md section 11), so a missing psycopg driver is a configuration error
    rather than a degraded mode.
    """


def _require_run_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a workflow run (SPEC.md section 9)."""
    if not value or not value.strip():
        raise CrossTenantWorkflowRunError(
            f"a tenant-scoped workflow run {operation} requires a non-blank "
            "tenant id; a workflow run is a client resource and cannot be "
            "stored or read unscoped"
        )


class InMemoryWorkflowRunStore(WorkflowRunStore):
    """Process-local reference adapter for the ``WorkflowRunStore`` port.

    Keeps one run per (tenant, run id) and copies on the boundary like a real
    adapter, so the port contract and the application seam are exercised
    without a database.
    """

    def __init__(self) -> None:
        self._runs: dict[tuple[str, str], WorkflowRun] = {}

    def save(self, run: WorkflowRun) -> None:
        _require_run_tenant(run.tenant_id, "save")
        self._runs[(run.tenant_id, run.run_id)] = workflow_run_from_payload(
            workflow_run_to_payload(run)
        )

    def get(self, run_id: str, *, tenant_id: str) -> WorkflowRun | None:
        _require_run_tenant(tenant_id, "load")
        return self._runs.get((tenant_id, run_id))

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


class PostgresWorkflowRunStore(WorkflowRunStore):
    """Durable workflow run store backed by PostgreSQL.

    Rows are created by migration ``0009_workflow_runs`` and are scoped by a NOT
    NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``get`` reads only the
    requested tenant's row and rebuilds the run through
    ``workflow_run_from_payload``, so a stored row the aggregate would reject
    raises on load rather than being read back as a valid run (SPEC.md section
    4). A foreign run is indistinguishable from a missing one, so a lookup never
    leaks another client's run (SPEC.md section 9). ``save`` upserts by (tenant,
    run id): status and the current step are progress, so a run moving forward
    updates the row while the append-only transition log carried in the payload
    preserves each move. Row-level security (ADR 0004) is a follow-up; tenant
    scoping is enforced here by the WHERE clause and the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL workflow run adapter requires psycopg; install "
                "the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def save(self, run: WorkflowRun) -> None:
        _require_run_tenant(run.tenant_id, "save")
        payload = workflow_run_to_payload(run)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO workflow_runs (
                    tenant_id,
                    run_id,
                    status,
                    definition_id,
                    definition_version,
                    run
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    definition_id = EXCLUDED.definition_id,
                    definition_version = EXCLUDED.definition_version,
                    run = EXCLUDED.run,
                    recorded_at = now()
                """,
                (
                    run.tenant_id,
                    run.run_id,
                    run.status.value,
                    run.definition.definition_id,
                    run.definition.version,
                    Jsonb(payload),
                ),
            )
        self._connection.commit()

    def get(self, run_id: str, *, tenant_id: str) -> WorkflowRun | None:
        _require_run_tenant(tenant_id, "load")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT run
                FROM workflow_runs
                WHERE tenant_id = %s AND run_id = %s
                """,
                (tenant_id, run_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return workflow_run_from_payload(row[0])

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def workflow_run_store_from_env(database_url: str | None) -> WorkflowRunStore:
    """Select the workflow run adapter from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so run state
    survives a restart and is shared across the API and worker processes (SPEC.md
    sections 7 and 11); without one the process-local reference adapter keeps
    local development and the domain-only test interpreter working. A set but
    unusable configuration raises ``WorkflowRunConfigurationError`` so a
    deployment cannot mistake a non-durable store for a durable one. The caller
    owns the returned adapter's lifecycle and calls ``close`` when the request
    ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryWorkflowRunStore()
    if psycopg is None:
        raise WorkflowRunConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to "
            "use the process-local workflow run store"
        )
    return PostgresWorkflowRunStore(psycopg.connect(database_url))
