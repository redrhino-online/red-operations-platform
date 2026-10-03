"""Reference adapters for the Operations dismissal port (SPEC.md section 6).

The process-local adapter exercises the port contract and the application seam
without a database, so the append-only rule (a dismissal cannot be re-stated with
different content under its key) is testable and the durable PostgreSQL adapter
follows the same contract. ``PostgresInterventionDismissalRepository`` is the
durable adapter whose table is created by migration
``0016_intervention_dismissals``; it is exercised wherever a psycopg driver and a
``DATABASE_URL`` are available (see
``tests/unit/operations/test_intervention_dismissal_postgres.py``). Row
serialisation lives in ``mappers.py``.
"""

from __future__ import annotations

from typing import Any

from redops.contexts.operations.application.ports import (
    InterventionDismissalRepository,
)
from redops.contexts.operations.domain.errors import (
    InterventionDismissalConflictError,
    InterventionDismissalTenantBoundaryError,
)
from redops.contexts.operations.domain.value_objects import InterventionDismissal
from redops.contexts.operations.infrastructure.mappers import (
    intervention_dismissal_from_payload,
    intervention_dismissal_to_payload,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class InterventionDismissalConfigurationError(RuntimeError):
    """The dismissal store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept
    an operator dismissal that vanishes on restart, so a missing psycopg driver is
    a configuration error rather than a degraded mode (SPEC.md sections 7 and 9).
    """


def _require_dismissal_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a client's dismissal decision.

    SPEC.md sections 3 and 9 make an intervention a client resource that must
    carry its tenant on every command and query; storing or resolving one without
    a client would either leak across clients or create an orphaned decision.
    """

    if not value or not value.strip():
        raise InterventionDismissalTenantBoundaryError(
            f"a tenant-scoped intervention dismissal {operation} requires a "
            "non-blank tenant id; a dismissal is a client resource and cannot be "
            "stored or read unscoped"
        )


class InMemoryInterventionDismissalRepository(
    InterventionDismissalRepository
):
    """Append-only, process-local dismissal store."""

    def __init__(self) -> None:
        self._dismissals: dict[
            tuple[str, str, str, str], InterventionDismissal
        ] = {}

    def list(
        self, tenant_id: str, client: str
    ) -> tuple[InterventionDismissal, ...]:
        _require_dismissal_tenant(tenant_id, "read")
        return tuple(
            dismissal
            for (stored_tenant, stored_client, _reason, _subject), dismissal
            in self._dismissals.items()
            if stored_tenant == tenant_id and stored_client == client
        )

    def save(self, dismissal: InterventionDismissal) -> None:
        _require_dismissal_tenant(dismissal.tenant_id, "write")
        key = (
            dismissal.tenant_id,
            dismissal.client,
            dismissal.reason.value,
            dismissal.subject,
        )
        existing = self._dismissals.get(key)
        if existing is not None and existing != dismissal:
            raise InterventionDismissalConflictError(
                f"intervention dismissal {dismissal.key!r} is already stored for "
                f"tenant {dismissal.tenant_id!r} with different content; a "
                "dismissal is an append-only operator decision"
            )
        self._dismissals[key] = dismissal

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


class PostgresInterventionDismissalRepository(
    InterventionDismissalRepository
):
    """Durable, append-only dismissal store backed by PostgreSQL.

    Rows are created by migration ``0016_intervention_dismissals`` and are scoped
    by a NOT NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``list`` reads
    only the requested tenant's rows for the exact client and rebuilds each
    dismissal through ``intervention_dismissal_from_payload``, so a stored row the
    value object would reject raises on load rather than being read back as a
    decision (SPEC.md section 4). ``save`` inserts a new dismissal and treats an
    exact replay as idempotent while refusing a same-key row with different
    content. Row-level security (ADR 0004) is a follow-up; tenant scoping is
    enforced here by the WHERE clause and the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL intervention dismissal adapter requires psycopg; "
                "install the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def list(
        self, tenant_id: str, client: str
    ) -> tuple[InterventionDismissal, ...]:
        _require_dismissal_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT dismissal
                FROM intervention_dismissals
                WHERE tenant_id = %s
                  AND client = %s
                ORDER BY reason, subject
                """,
                (tenant_id, client),
            )
            rows = cursor.fetchall()
        return tuple(
            intervention_dismissal_from_payload(row[0]) for row in rows
        )

    def save(self, dismissal: InterventionDismissal) -> None:
        _require_dismissal_tenant(dismissal.tenant_id, "write")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT dismissal
                FROM intervention_dismissals
                WHERE tenant_id = %s
                  AND client = %s
                  AND reason = %s
                  AND subject = %s
                """,
                (
                    dismissal.tenant_id,
                    dismissal.client,
                    dismissal.reason.value,
                    dismissal.subject,
                ),
            )
            row = cursor.fetchone()
        if row is not None:
            existing = intervention_dismissal_from_payload(row[0])
            if existing != dismissal:
                raise InterventionDismissalConflictError(
                    f"intervention dismissal {dismissal.key!r} is already stored "
                    f"for tenant {dismissal.tenant_id!r} with different content; a "
                    "dismissal is an append-only operator decision"
                )
            return
        payload = intervention_dismissal_to_payload(dismissal)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO intervention_dismissals (
                    tenant_id,
                    client,
                    reason,
                    subject,
                    dismissal
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    dismissal.tenant_id,
                    dismissal.client,
                    dismissal.reason.value,
                    dismissal.subject,
                    Jsonb(payload),
                ),
            )
        self._connection.commit()

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def intervention_dismissal_repository_from_env(
    database_url: str | None,
) -> InterventionDismissalRepository:
    """Select the dismissal store from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so an operator
    dismissal survives a restart (SPEC.md sections 7 and 9); without one the
    process-local reference adapter keeps local development and the domain-only
    test interpreter working. A set but unusable configuration raises
    ``InterventionDismissalConfigurationError`` so a deployment cannot mistake a
    non-durable store for a durable one. The caller owns the returned adapter's
    lifecycle and calls ``close`` when the request ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryInterventionDismissalRepository()
    if psycopg is None:
        raise InterventionDismissalConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to use "
            "the process-local intervention dismissal store"
        )
    return PostgresInterventionDismissalRepository(psycopg.connect(database_url))
