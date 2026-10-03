"""Reference adapters for the Production repository port (SPEC.md section 6).

The process-local adapter exercises the port contract and the application seam
without a database, so the immutability rule (an approved asset cannot be
re-stated with different content under the same id) is testable and the durable
PostgreSQL adapter follows the same contract. ``PostgresAuthorityAmplifierRepository``
is the durable stage 7 amplifier adapter whose table is created by migration
``0006_authority_amplifiers``. It is exercised wherever a psycopg driver and a
``DATABASE_URL`` are available (see
``tests/unit/production/test_authority_amplifier_postgres.py``). Row
serialisation lives in ``mappers.py``.
"""

from __future__ import annotations

from typing import Any

from redops.contexts.production.application.ports import (
    AuthorityAmplifierRepository,
)
from redops.contexts.production.domain.entities import AuthorityAmplifier
from redops.contexts.production.domain.errors import (
    AuthorityAmplifierReadinessError,
    AuthorityAmplifierVersionConflictError,
    AuthorityAmplifierVersionTenantBoundaryError,
)
from redops.contexts.production.infrastructure.mappers import (
    authority_amplifier_from_payload,
    authority_amplifier_to_payload,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class AuthorityAmplifierConfigurationError(RuntimeError):
    """The approved amplifier store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept an
    approved stage 7 amplifier that vanishes on restart, so a missing psycopg
    driver is a configuration error rather than a degraded mode (SPEC.md sections
    3, 4 and 9).
    """


def _require_amplifier_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a client's approved amplifier.

    SPEC.md sections 3 and 9 make an amplifier a client resource that must carry
    its tenant on every command and query; storing or resolving one without a
    client would either leak across clients or create an orphaned record.
    """

    if not value or not value.strip():
        raise AuthorityAmplifierVersionTenantBoundaryError(
            f"a tenant-scoped authority amplifier {operation} requires a "
            "non-blank tenant id; an approved amplifier is a client resource and "
            "cannot be stored or read unscoped"
        )


class InMemoryAuthorityAmplifierRepository(AuthorityAmplifierRepository):
    """Append-only, process-local approved amplifier store keyed by client and id."""

    def __init__(self) -> None:
        self._amplifiers: dict[tuple[str, str], AuthorityAmplifier] = {}

    def get(
        self, tenant_id: str, amplifier_id: str
    ) -> AuthorityAmplifier | None:
        _require_amplifier_tenant(tenant_id, "read")
        return self._amplifiers.get((tenant_id, amplifier_id))

    def save(self, amplifier: AuthorityAmplifier) -> None:
        _require_amplifier_tenant(amplifier.tenant_id, "write")
        if not amplifier.is_approved:
            raise AuthorityAmplifierReadinessError(
                "an approved amplifier store only holds amplifiers that received "
                "creative acceptance; a stage 7 amplifier that has not passed the "
                "Authority Amplifier Approved checkpoint cannot be stored"
            )
        key = (amplifier.tenant_id, amplifier.amplifier_id)
        existing = self._amplifiers.get(key)
        if existing is not None and existing != amplifier:
            raise AuthorityAmplifierVersionConflictError(
                f"authority amplifier {amplifier.amplifier_id!r} is already "
                f"stored for tenant {amplifier.tenant_id!r} with different "
                "content; an approved amplifier is immutable and a change must "
                "be a new revision"
            )
        self._amplifiers[key] = amplifier

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


class PostgresAuthorityAmplifierRepository(AuthorityAmplifierRepository):
    """Durable, append-only approved amplifier store backed by PostgreSQL.

    Rows are created by migration ``0006_authority_amplifiers`` and are scoped by
    a NOT NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``get`` reads only
    the requested tenant's row for the exact ``amplifier_id`` and rebuilds the
    aggregate through ``authority_amplifier_from_payload``, so a stored row the
    aggregate would reject raises on load rather than being read back as an
    approved amplifier (SPEC.md section 4). ``save`` refuses an unapproved
    amplifier, inserts a new approved amplifier, and treats a same-id replay as
    idempotent while refusing a same-id row with different content: an approved
    amplifier is immutable and a change must be a new revision (SPEC.md sections
    3 and 4). Row-level security (ADR 0004) is a follow-up; tenant scoping is
    enforced here by the WHERE clause and the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL authority amplifier adapter requires psycopg; "
                "install the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def get(
        self, tenant_id: str, amplifier_id: str
    ) -> AuthorityAmplifier | None:
        _require_amplifier_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT amplifier
                FROM authority_amplifiers
                WHERE tenant_id = %s
                  AND amplifier_id = %s
                """,
                (tenant_id, amplifier_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return authority_amplifier_from_payload(row[0])

    def save(self, amplifier: AuthorityAmplifier) -> None:
        _require_amplifier_tenant(amplifier.tenant_id, "write")
        if not amplifier.is_approved:
            raise AuthorityAmplifierReadinessError(
                "an approved amplifier store only holds amplifiers that received "
                "creative acceptance; a stage 7 amplifier that has not passed the "
                "Authority Amplifier Approved checkpoint cannot be stored"
            )
        existing = self.get(amplifier.tenant_id, amplifier.amplifier_id)
        if existing is not None:
            if existing != amplifier:
                raise AuthorityAmplifierVersionConflictError(
                    f"authority amplifier {amplifier.amplifier_id!r} is already "
                    f"stored for tenant {amplifier.tenant_id!r} with different "
                    "content; an approved amplifier is immutable and a change "
                    "must be a new revision"
                )
            return
        payload = authority_amplifier_to_payload(amplifier)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO authority_amplifiers (
                    tenant_id,
                    amplifier_id,
                    amplifier
                ) VALUES (%s, %s, %s)
                """,
                (
                    amplifier.tenant_id,
                    amplifier.amplifier_id,
                    Jsonb(payload),
                ),
            )
        self._connection.commit()

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def authority_amplifier_repository_from_env(
    database_url: str | None,
) -> AuthorityAmplifierRepository:
    """Select the approved amplifier store from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so the stage 7
    amplifier a gate approved survives a restart and is shared across the API and
    worker processes (SPEC.md sections 3 and 4); without one the process-local
    reference adapter keeps local development and the domain-only test interpreter
    working. A set but unusable configuration raises
    ``AuthorityAmplifierConfigurationError`` so a deployment cannot mistake a
    non-durable store for a durable one. The caller owns the returned adapter's
    lifecycle and calls ``close`` when the request ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryAuthorityAmplifierRepository()
    if psycopg is None:
        raise AuthorityAmplifierConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to use "
            "the process-local approved amplifier store"
        )
    return PostgresAuthorityAmplifierRepository(psycopg.connect(database_url))
