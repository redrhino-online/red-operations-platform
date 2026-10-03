"""Reference adapter for the ``MethodVersionRepository`` port (SPEC.md section 6).

The process-local adapter exercises the port contract and the application seam
without a database, so the immutability rule (an approved method version cannot
be re-stated with different content) is testable and the durable PostgreSQL
adapter follows the same contract. ``PostgresMethodVersionRepository`` is the
durable adapter whose table is created by migration ``0003_method_versions``; it
is exercised wherever a psycopg driver and a ``DATABASE_URL`` are available (see
``tests/unit/method/test_method_version_postgres.py``). Row serialisation lives
in ``mappers.py``.
"""

from __future__ import annotations

from typing import Any

from redops.contexts.method.application.ports import MethodVersionRepository
from redops.contexts.method.domain.entities import MethodVersion
from redops.contexts.method.domain.errors import (
    MethodApprovalError,
    MethodVersionConflictError,
    MethodVersionTenantBoundaryError,
)
from redops.contexts.method.domain.value_objects import SemanticVersion
from redops.contexts.method.infrastructure.mappers import (
    method_from_payload,
    method_to_payload,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class MethodVersionConfigurationError(RuntimeError):
    """The approved method store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept
    an approved method version that vanishes on restart, so a missing psycopg
    driver is a configuration error rather than a degraded mode (SPEC.md
    sections 3, 4 and 9).
    """



def _require_method_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a client's approved method.

    SPEC.md sections 3 and 9 make a method version a client resource that must
    carry its tenant on every command and query; storing or resolving one
    without a client would either leak across clients or create an orphaned
    record.
    """

    if not value or not value.strip():
        raise MethodVersionTenantBoundaryError(
            f"a tenant-scoped method version {operation} requires a non-blank "
            "tenant id; an approved method is a client resource and cannot be "
            "stored or read unscoped"
        )


class InMemoryMethodVersionRepository(MethodVersionRepository):
    """Append-only, process-local approved method store keyed by client and version."""

    def __init__(self) -> None:
        self._methods: dict[tuple[str, str, SemanticVersion], MethodVersion] = {}

    def get(
        self,
        tenant_id: str,
        method_id: str,
        version: SemanticVersion,
    ) -> MethodVersion | None:
        _require_method_tenant(tenant_id, "read")
        return self._methods.get((tenant_id, method_id, version))

    def save(self, method: MethodVersion) -> None:
        _require_method_tenant(method.tenant_id, "write")
        if method.approval is None:
            raise MethodApprovalError(
                "an approved method version store only holds approved methods; "
                "an unapproved draft cannot be stored"
            )
        key = (method.tenant_id, method.method_id, method.semantic_version)
        existing = self._methods.get(key)
        if existing is not None and existing != method:
            raise MethodVersionConflictError(
                f"approved method {method.method_id!r} at version "
                f"{method.semantic_version} is already stored for tenant "
                f"{method.tenant_id!r} with different content; an approved "
                "version is immutable and a change must advance the version"
            )
        self._methods[key] = method

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


class PostgresMethodVersionRepository(MethodVersionRepository):
    """Durable, append-only approved method store backed by PostgreSQL.

    Rows are created by migration ``0003_method_versions`` and are scoped by a
    NOT NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``get`` reads only
    the requested tenant's row for the exact ``(method_id, semantic_version)``
    and rebuilds the aggregate through ``method_from_payload``, so a stored row
    the aggregate would reject raises on load rather than being read back as an
    approved method (SPEC.md section 4). ``save`` refuses an unapproved draft,
    inserts a new approved version, and treats a same-key replay as idempotent
    while refusing a same-key row with different content: an approved version is
    immutable and a change must advance the version (SPEC.md sections 3 and 4).
    Row-level security (ADR 0004) is a follow-up; tenant scoping is enforced here
    by the WHERE clause and the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL method version adapter requires psycopg; "
                "install the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def get(
        self,
        tenant_id: str,
        method_id: str,
        version: SemanticVersion,
    ) -> MethodVersion | None:
        _require_method_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT method
                FROM method_versions
                WHERE tenant_id = %s
                  AND method_id = %s
                  AND semantic_version = %s
                """,
                (tenant_id, method_id, str(version)),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return method_from_payload(row[0])

    def save(self, method: MethodVersion) -> None:
        _require_method_tenant(method.tenant_id, "write")
        if method.approval is None:
            raise MethodApprovalError(
                "an approved method version store only holds approved methods; "
                "an unapproved draft cannot be stored"
            )
        existing = self.get(
            method.tenant_id, method.method_id, method.semantic_version
        )
        if existing is not None:
            if existing != method:
                raise MethodVersionConflictError(
                    f"approved method {method.method_id!r} at version "
                    f"{method.semantic_version} is already stored for tenant "
                    f"{method.tenant_id!r} with different content; an approved "
                    "version is immutable and a change must advance the version"
                )
            return
        payload = method_to_payload(method)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO method_versions (
                    tenant_id,
                    method_id,
                    semantic_version,
                    method
                ) VALUES (%s, %s, %s, %s)
                """,
                (
                    method.tenant_id,
                    method.method_id,
                    str(method.semantic_version),
                    Jsonb(payload),
                ),
            )
        self._connection.commit()

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def method_version_repository_from_env(
    database_url: str | None,
) -> MethodVersionRepository:
    """Select the approved method store from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so an
    approved method version survives a restart and is shared across the API and
    worker processes (SPEC.md sections 3 and 4); without one the process-local
    reference adapter keeps local development and the domain-only test
    interpreter working. A set but unusable configuration raises
    ``MethodVersionConfigurationError`` so a deployment cannot mistake a
    non-durable store for a durable one. The caller owns the returned adapter's
    lifecycle and calls ``close`` when the request ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryMethodVersionRepository()
    if psycopg is None:
        raise MethodVersionConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to "
            "use the process-local approved method store"
        )
    return PostgresMethodVersionRepository(psycopg.connect(database_url))
