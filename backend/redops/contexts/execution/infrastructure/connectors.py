"""Reference adapters for the idempotency-keyed connector seam (SPEC.md section 6).

``IdempotentConnector`` is the replay-safe ``ConnectorPort`` adapter: it composes
an ``ExternalOperationStore`` with a ``ConnectorTransport`` so an effect is sent
at most once (SPEC.md section 11, "duplicate delivery creates one external
operation"). ``InMemoryExternalOperationStore`` and ``RecordingConnectorTransport``
are the process-local reference implementations used by tests and by composition
until a durable PostgreSQL adapter lands; a durable adapter implements the same
ports without changing callers.

The store is append-only per ``(tenant_id, idempotency_key)``. A repeat of the
same effect returns the recorded operation; a reused key with different content
raises ``ConnectorIdempotencyConflictError`` rather than overwriting the record
or sending a second effect.
"""

from __future__ import annotations

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
