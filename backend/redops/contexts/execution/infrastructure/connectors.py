"""Reference adapters for the idempotency-keyed connector seam (SPEC.md section 6).

``IdempotentConnector`` is the replay-safe ``ConnectorPort`` adapter: it composes
an ``ExternalOperationStore`` with a ``ConnectorTransport`` so an effect is sent
at most once (SPEC.md section 11, "duplicate delivery creates one external
operation"). ``InMemoryExternalOperationStore`` and ``RecordingConnectorTransport``
are the process-local reference implementations used by tests; the durable
``PostgresExternalOperationStore`` (migration ``0018_external_operations``)
implements the same port so an already-recorded operation survives a process
restart and cannot be re-sent (SPEC.md sections 9 and 11). A durable adapter
implements the same ports without changing callers.

The store is append-only per ``(tenant_id, idempotency_key)``. A repeat of the
same effect returns the recorded operation; a reused key with different content
raises ``ConnectorIdempotencyConflictError`` rather than overwriting the record
or sending a second effect.
"""

from __future__ import annotations

from typing import Any

from redops.contexts.execution.application.ports import (
    ConnectorPort,
    ConnectorTransport,
    ExternalOperationStore,
)
from redops.contexts.execution.domain.connector import (
    ConnectorEffect,
    ExternalOperation,
)
from redops.contexts.execution.domain.errors import (
    ConnectorIdempotencyConflictError,
    ConnectorTenantBoundaryError,
)
from redops.contexts.execution.infrastructure.mappers import (
    external_operation_from_payload,
    external_operation_to_payload,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class ConnectorConfigurationError(RuntimeError):
    """The external operation store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept
    an external operation that vanishes on restart and could be sent a second
    time (SPEC.md section 11), so a missing psycopg driver is a configuration
    error rather than a degraded mode.
    """


def _require_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a client's external operation."""

    if not value or not value.strip():
        raise ConnectorTenantBoundaryError(
            f"a tenant-scoped external operation {operation} requires a "
            "non-blank tenant id; an outbound operation is a client resource "
            "and cannot be stored or read unscoped"
        )


class InMemoryExternalOperationStore(ExternalOperationStore):
    """Append-only, process-local external operation log."""

    def __init__(self) -> None:
        self._operations: dict[tuple[str, str], ExternalOperation] = {}

    def get(
        self, tenant_id: str, idempotency_key: str
    ) -> ExternalOperation | None:
        _require_tenant(tenant_id, "read")
        return self._operations.get((tenant_id, idempotency_key))

    def record(self, operation: ExternalOperation) -> None:
        effect = operation.effect
        _require_tenant(effect.tenant_id, "write")
        key = (effect.tenant_id, effect.idempotency_key)
        existing = self._operations.get(key)
        if existing is not None:
            if existing == operation:
                return
            raise ConnectorIdempotencyConflictError(
                f"idempotency key {effect.idempotency_key!r} for tenant "
                f"{effect.tenant_id!r} is already spent on a different "
                "external operation"
            )
        self._operations[key] = operation


class RecordingConnectorTransport(ConnectorTransport):
    """A process-local transport that records each effect it sends.

    It returns a stable, incrementing external reference per send, so a test can
    assert that a duplicate delivery sent exactly once.
    """

    def __init__(self, *, prefix: str = "crm-op") -> None:
        self._prefix = prefix
        self._count = 0
        self.sent: list[ConnectorEffect] = []

    def send(self, effect: ConnectorEffect) -> str:
        self._count += 1
        self.sent.append(effect)
        return f"{self._prefix}-{self._count}"


class IdempotentConnector(ConnectorPort):
    """Replay-safe connector that sends each effect at most once."""

    def __init__(
        self, *, store: ExternalOperationStore, transport: ConnectorTransport
    ) -> None:
        self._store = store
        self._transport = transport

    def deliver(self, effect: ConnectorEffect) -> ExternalOperation:
        _require_tenant(effect.tenant_id, "delivery")
        existing = self._store.get(effect.tenant_id, effect.idempotency_key)
        if existing is not None:
            if existing.matches(effect):
                return existing
            raise ConnectorIdempotencyConflictError(
                f"idempotency key {effect.idempotency_key!r} for tenant "
                f"{effect.tenant_id!r} was already delivered with different "
                "content"
            )
        external_ref = self._transport.send(effect)
        operation = ExternalOperation(
            effect=effect,
            external_ref=external_ref,
            delivered_on=effect.requested_on,
        )
        self._store.record(operation)
        return operation


class PostgresExternalOperationStore(ExternalOperationStore):
    """Durable, append-only external operation log backed by PostgreSQL.

    Rows are created by migration ``0018_external_operations`` and are scoped by
    a NOT NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``get`` reads only
    the requested tenant's row for the exact ``idempotency_key`` and rebuilds the
    operation through ``external_operation_from_payload``, so a stored row the
    value objects would reject raises on load rather than being read back as a
    valid operation (SPEC.md section 4). The unique ``(tenant_id,
    idempotency_key)`` key is what makes the guarantee durable: after a restart
    the recorded operation is still found, so a retry resolves to it instead of
    sending a second effect (SPEC.md section 11). ``record`` treats a same-body
    replay as idempotent and refuses a same-key row with different content: a
    spent idempotency key is immutable (SPEC.md section 11). Row-level security
    (ADR 0004) is a follow-up; tenant scoping is enforced here by the WHERE
    clause and the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL external operation adapter requires psycopg; "
                "install the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def get(
        self, tenant_id: str, idempotency_key: str
    ) -> ExternalOperation | None:
        _require_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT operation
                FROM external_operations
                WHERE tenant_id = %s
                  AND idempotency_key = %s
                """,
                (tenant_id, idempotency_key),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return external_operation_from_payload(row[0])

    def record(self, operation: ExternalOperation) -> None:
        effect = operation.effect
        _require_tenant(effect.tenant_id, "write")
        existing = self.get(effect.tenant_id, effect.idempotency_key)
        if existing is not None:
            if existing == operation:
                return
            raise ConnectorIdempotencyConflictError(
                f"idempotency key {effect.idempotency_key!r} for tenant "
                f"{effect.tenant_id!r} is already spent on a different "
                "external operation"
            )
        payload = external_operation_to_payload(operation)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO external_operations (
                    tenant_id,
                    idempotency_key,
                    connector,
                    target,
                    payload_digest,
                    operation
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    effect.tenant_id,
                    effect.idempotency_key,
                    effect.connector,
                    effect.target,
                    effect.payload_digest,
                    Jsonb(payload),
                ),
            )
        self._connection.commit()

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def external_operation_store_from_env(
    database_url: str | None,
) -> ExternalOperationStore:
    """Select the external operation store from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so an
    already-recorded operation survives a restart and is shared across the API
    and worker processes (SPEC.md section 11); without one the process-local
    reference adapter keeps local development and the domain-only test
    interpreter working. A set but unusable configuration raises
    ``ConnectorConfigurationError`` so a deployment cannot mistake a non-durable
    store for a durable one. The caller owns the returned adapter's lifecycle and
    calls ``close`` when the request ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryExternalOperationStore()
    if psycopg is None:
        raise ConnectorConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to use "
            "the process-local external operation store"
        )
    return PostgresExternalOperationStore(psycopg.connect(database_url))
