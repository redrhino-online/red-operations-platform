"""Reference adapter for the ``ClientWorkspaceStore`` port (SPEC.md section 6).

The process-local adapter exercises the port contract and the application seam
without a database, so tenant scoping and the workspace round-trip are testable
and the durable PostgreSQL adapter follows the same contract.
``PostgresClientWorkspaceStore`` is the durable adapter whose table is created by
migration ``0010_client_workspaces``; it is exercised wherever a psycopg driver
and a ``DATABASE_URL`` are available (see
``tests/unit/engagement/test_client_workspace_store.py``). Row serialisation
lives in ``mappers.py``.
"""

from __future__ import annotations

from typing import Any

from redops.contexts.engagement.application.ports import ClientWorkspaceStore
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import UnscopedClientWorkspaceError
from redops.contexts.engagement.infrastructure.mappers import (
    workspace_from_payload,
    workspace_to_payload,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class ClientWorkspaceConfigurationError(RuntimeError):
    """The client workspace store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept a
    client workspace that vanishes on restart, so a missing psycopg driver is a
    configuration error rather than a degraded mode (SPEC.md sections 3, 4 and
    9).
    """


def _require_workspace_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a client workspace.

    SPEC.md sections 3 and 9 make a client workspace a tenant resource that must
    carry its tenant on every command and query; listing or resolving one without
    a client would either leak across clients or create an orphaned record.
    """

    if not value or not value.strip():
        raise UnscopedClientWorkspaceError(
            f"a tenant-scoped client workspace {operation} requires a non-blank "
            "tenant id; a workspace is a client resource and cannot be stored or "
            "read unscoped"
        )


class InMemoryClientWorkspaceStore(ClientWorkspaceStore):
    """Process-local client workspace store keyed by ``(tenant, workspace)``."""

    def __init__(self) -> None:
        self._workspaces: dict[tuple[str, str], ClientWorkspace] = {}

    def list(self, tenant_id: str) -> tuple[ClientWorkspace, ...]:
        _require_workspace_tenant(tenant_id, "read")
        return tuple(
            self._workspaces[key]
            for key in sorted(self._workspaces)
            if key[0] == tenant_id
        )

    def get(self, tenant_id: str, workspace_id: str) -> ClientWorkspace | None:
        _require_workspace_tenant(tenant_id, "read")
        return self._workspaces.get((tenant_id, workspace_id))

    def save(self, workspace: ClientWorkspace) -> None:
        _require_workspace_tenant(workspace.tenant_id, "write")
        self._workspaces[(workspace.tenant_id, workspace.workspace_id)] = (
            workspace_from_payload(workspace_to_payload(workspace))
        )

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


class PostgresClientWorkspaceStore(ClientWorkspaceStore):
    """Durable client workspace store backed by PostgreSQL.

    Rows are created by migration ``0010_client_workspaces`` and are scoped by a
    NOT NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``list`` and ``get``
    read only the requested tenant's rows and rebuild the aggregate through
    ``workspace_from_payload``, so a stored workspace the aggregate would reject
    raises on load rather than being read back as a real client. ``save`` upserts
    a workspace under its own tenant, so a lifecycle advance or a new authority
    is persisted (SPEC.md section 4). Row-level security (ADR 0004) is a
    follow-up; tenant scoping is enforced here by the WHERE clause and the NOT
    NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL client workspace adapter requires psycopg; "
                "install the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def list(self, tenant_id: str) -> tuple[ClientWorkspace, ...]:
        _require_workspace_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT workspace
                FROM client_workspaces
                WHERE tenant_id = %s
                ORDER BY workspace_id
                """,
                (tenant_id,),
            )
            rows = cursor.fetchall()
        return tuple(workspace_from_payload(row[0]) for row in rows)

    def get(self, tenant_id: str, workspace_id: str) -> ClientWorkspace | None:
        _require_workspace_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT workspace
                FROM client_workspaces
                WHERE tenant_id = %s
                  AND workspace_id = %s
                """,
                (tenant_id, workspace_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return workspace_from_payload(row[0])

    def save(self, workspace: ClientWorkspace) -> None:
        _require_workspace_tenant(workspace.tenant_id, "write")
        payload = workspace_to_payload(workspace)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO client_workspaces (
                    tenant_id,
                    workspace_id,
                    workspace
                ) VALUES (%s, %s, %s)
                ON CONFLICT (tenant_id, workspace_id)
                DO UPDATE SET workspace = EXCLUDED.workspace,
                              recorded_at = now()
                """,
                (
                    workspace.tenant_id,
                    workspace.workspace_id,
                    Jsonb(payload),
                ),
            )
        self._connection.commit()

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def client_workspace_store_from_env(
    database_url: str | None,
) -> ClientWorkspaceStore:
    """Select the client workspace store from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so a client
    workspace survives a restart and is shared across the API and worker
    processes (SPEC.md sections 3 and 4); without one the process-local reference
    adapter keeps local development and the domain-only test interpreter working.
    A set but unusable configuration raises ``ClientWorkspaceConfigurationError``
    so a deployment cannot mistake a non-durable store for a durable one. The
    caller owns the returned adapter's lifecycle and calls ``close`` when the
    request ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryClientWorkspaceStore()
    if psycopg is None:
        raise ClientWorkspaceConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to "
            "use the process-local client workspace store"
        )
    return PostgresClientWorkspaceStore(psycopg.connect(database_url))
