"""Reference adapters for the Execution repository port (SPEC.md section 6).

The process-local adapter exercises the port contract and the application seam
without a database, so the immutability rule (an approved asset cannot be
re-stated with different content under the same id) is testable and the durable
PostgreSQL adapter follows the same contract. ``PostgresFunnelIntegrationRepository``
is the durable stage 8 funnel adapter whose table is created by migration
``0007_funnel_integrations``. It is exercised wherever a psycopg driver and a
``DATABASE_URL`` are available (see
``tests/unit/execution/test_funnel_integration_postgres.py``). Row serialisation
lives in ``mappers.py``.
"""

from __future__ import annotations

from typing import Any

from redops.contexts.execution.application.ports import (
    FunnelIntegrationRepository,
)
from redops.contexts.execution.domain.entities import FunnelIntegration
from redops.contexts.execution.domain.errors import (
    FunnelReadinessError,
    FunnelVersionConflictError,
    FunnelVersionTenantBoundaryError,
)
from redops.contexts.execution.infrastructure.mappers import (
    funnel_integration_from_payload,
    funnel_integration_to_payload,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class FunnelIntegrationConfigurationError(RuntimeError):
    """The completed funnel store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept a
    completed stage 8 funnel that vanishes on restart, so a missing psycopg
    driver is a configuration error rather than a degraded mode (SPEC.md sections
    3, 4 and 9).
    """


def _require_funnel_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a client's completed funnel.

    SPEC.md sections 3 and 9 make a funnel a client resource that must carry its
    tenant on every command and query; storing or resolving one without a client
    would either leak across clients or create an orphaned record.
    """

    if not value or not value.strip():
        raise FunnelVersionTenantBoundaryError(
            f"a tenant-scoped funnel integration {operation} requires a "
            "non-blank tenant id; a completed funnel is a client resource and "
            "cannot be stored or read unscoped"
        )


class InMemoryFunnelIntegrationRepository(FunnelIntegrationRepository):
    """Append-only, process-local completed funnel store keyed by client and id."""

    def __init__(self) -> None:
        self._funnels: dict[tuple[str, str], FunnelIntegration] = {}

    def get(
        self, tenant_id: str, integration_id: str
    ) -> FunnelIntegration | None:
        _require_funnel_tenant(tenant_id, "read")
        return self._funnels.get((tenant_id, integration_id))

    def save(self, funnel: FunnelIntegration) -> None:
        _require_funnel_tenant(funnel.tenant_id, "write")
        if not funnel.is_complete:
            raise FunnelReadinessError(
                "a completed funnel store only holds funnels that passed the "
                "Funnel Complete checkpoint; a stage 8 funnel whose prospect "
                "path dry run has not routed every handoff cannot be stored"
            )
        key = (funnel.tenant_id, funnel.integration_id)
        existing = self._funnels.get(key)
        if existing is not None and existing != funnel:
            raise FunnelVersionConflictError(
                f"funnel integration {funnel.integration_id!r} is already "
                f"stored for tenant {funnel.tenant_id!r} with different "
                "content; a completed funnel is immutable and a change must "
                "be a new revision"
            )
        self._funnels[key] = funnel

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


class PostgresFunnelIntegrationRepository(FunnelIntegrationRepository):
    """Durable, append-only completed funnel store backed by PostgreSQL.

    Rows are created by migration ``0007_funnel_integrations`` and are scoped by
    a NOT NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``get`` reads only
    the requested tenant's row for the exact ``integration_id`` and rebuilds the
    aggregate through ``funnel_integration_from_payload``, so a stored row the
    aggregate would reject raises on load rather than being read back as a
    completed funnel (SPEC.md section 4). ``save`` refuses an incomplete funnel,
    inserts a new completed funnel, and treats a same-id replay as idempotent
    while refusing a same-id row with different content: a completed funnel is
    immutable and a change must be a new revision (SPEC.md sections 3 and 4).
    Row-level security (ADR 0004) is a follow-up; tenant scoping is enforced here
    by the WHERE clause and the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL funnel integration adapter requires psycopg; "
                "install the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def get(
        self, tenant_id: str, integration_id: str
    ) -> FunnelIntegration | None:
        _require_funnel_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT funnel
                FROM funnel_integrations
                WHERE tenant_id = %s
                  AND integration_id = %s
                """,
                (tenant_id, integration_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return funnel_integration_from_payload(row[0])

    def save(self, funnel: FunnelIntegration) -> None:
        _require_funnel_tenant(funnel.tenant_id, "write")
        if not funnel.is_complete:
            raise FunnelReadinessError(
                "a completed funnel store only holds funnels that passed the "
                "Funnel Complete checkpoint; a stage 8 funnel whose prospect "
                "path dry run has not routed every handoff cannot be stored"
            )
        existing = self.get(funnel.tenant_id, funnel.integration_id)
        if existing is not None:
            if existing != funnel:
                raise FunnelVersionConflictError(
                    f"funnel integration {funnel.integration_id!r} is already "
                    f"stored for tenant {funnel.tenant_id!r} with different "
                    "content; a completed funnel is immutable and a change "
                    "must be a new revision"
                )
            return
        payload = funnel_integration_to_payload(funnel)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO funnel_integrations (
                    tenant_id,
                    integration_id,
                    funnel
                ) VALUES (%s, %s, %s)
                """,
                (
                    funnel.tenant_id,
                    funnel.integration_id,
                    Jsonb(payload),
                ),
            )
        self._connection.commit()

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def funnel_integration_repository_from_env(
    database_url: str | None,
) -> FunnelIntegrationRepository:
    """Select the completed funnel store from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so the stage 8
    funnel a gate approved survives a restart and is shared across the API and
    worker processes (SPEC.md sections 3 and 4); without one the process-local
    reference adapter keeps local development and the domain-only test interpreter
    working. A set but unusable configuration raises
    ``FunnelIntegrationConfigurationError`` so a deployment cannot mistake a
    non-durable store for a durable one. The caller owns the returned adapter's
    lifecycle and calls ``close`` when the request ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryFunnelIntegrationRepository()
    if psycopg is None:
        raise FunnelIntegrationConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to use "
            "the process-local completed funnel store"
        )
    return PostgresFunnelIntegrationRepository(psycopg.connect(database_url))
