"""Reference adapters for the ``OfferVersionRepository`` port (SPEC.md section 6).

The process-local adapter exercises the port contract and the application seam
without a database, so the immutability rule (a production ready offer cannot be
re-stated with different content under the same id) is testable and the durable
PostgreSQL adapter follows the same contract. ``PostgresOfferVersionRepository``
is the durable adapter whose table is created by migration
``0004_offer_versions``; it is exercised wherever a psycopg driver and a
``DATABASE_URL`` are available (see
``tests/unit/commercial/test_offer_version_postgres.py``). Row serialisation
lives in ``mappers.py``.
"""

from __future__ import annotations

from typing import Any

from redops.contexts.commercial.application.ports import OfferVersionRepository
from redops.contexts.commercial.domain.entities import OfferVersion
from redops.contexts.commercial.domain.errors import (
    OfferReadinessError,
    OfferVersionConflictError,
    OfferVersionTenantBoundaryError,
)
from redops.contexts.commercial.infrastructure.mappers import (
    offer_from_payload,
    offer_to_payload,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class OfferVersionConfigurationError(RuntimeError):
    """The production ready offer store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept a
    production ready offer that vanishes on restart, so a missing psycopg driver
    is a configuration error rather than a degraded mode (SPEC.md sections 3, 4
    and 9).
    """


def _require_offer_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a client's production ready offer.

    SPEC.md sections 3 and 9 make an offer a client resource that must carry its
    tenant on every command and query; storing or resolving one without a client
    would either leak across clients or create an orphaned record.
    """

    if not value or not value.strip():
        raise OfferVersionTenantBoundaryError(
            f"a tenant-scoped offer version {operation} requires a non-blank "
            "tenant id; a production ready offer is a client resource and cannot "
            "be stored or read unscoped"
        )


class InMemoryOfferVersionRepository(OfferVersionRepository):
    """Append-only, process-local production ready offer store keyed by client and id."""

    def __init__(self) -> None:
        self._offers: dict[tuple[str, str], OfferVersion] = {}

    def get(self, tenant_id: str, offer_id: str) -> OfferVersion | None:
        _require_offer_tenant(tenant_id, "read")
        return self._offers.get((tenant_id, offer_id))

    def save(self, offer: OfferVersion) -> None:
        _require_offer_tenant(offer.tenant_id, "write")
        if not offer.is_production_ready:
            raise OfferReadinessError(
                "a production ready offer store only holds approved offers; an "
                "offer that has not passed the stage 5 Offer Locked gate cannot "
                "be stored"
            )
        key = (offer.tenant_id, offer.offer_id)
        existing = self._offers.get(key)
        if existing is not None and existing != offer:
            raise OfferVersionConflictError(
                f"offer {offer.offer_id!r} is already stored for tenant "
                f"{offer.tenant_id!r} with different content; a production ready "
                "offer is immutable and a change must be a new revision"
            )
        self._offers[key] = offer

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


class PostgresOfferVersionRepository(OfferVersionRepository):
    """Durable, append-only production ready offer store backed by PostgreSQL.

    Rows are created by migration ``0004_offer_versions`` and are scoped by a
    NOT NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``get`` reads only
    the requested tenant's row for the exact ``offer_id`` and rebuilds the
    aggregate through ``offer_from_payload``, so a stored row the aggregate would
    reject raises on load rather than being read back as a production ready offer
    (SPEC.md section 4). ``save`` refuses an unready offer, inserts a new
    production ready offer, and treats a same-id replay as idempotent while
    refusing a same-id row with different content: an approved offer is
    immutable and a change must be a new revision (SPEC.md sections 3 and 4).
    Row-level security (ADR 0004) is a follow-up; tenant scoping is enforced here
    by the WHERE clause and the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL offer version adapter requires psycopg; install "
                "the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def get(self, tenant_id: str, offer_id: str) -> OfferVersion | None:
        _require_offer_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT offer
                FROM offer_versions
                WHERE tenant_id = %s
                  AND offer_id = %s
                """,
                (tenant_id, offer_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return offer_from_payload(row[0])

    def save(self, offer: OfferVersion) -> None:
        _require_offer_tenant(offer.tenant_id, "write")
        if not offer.is_production_ready:
            raise OfferReadinessError(
                "a production ready offer store only holds approved offers; an "
                "offer that has not passed the stage 5 Offer Locked gate cannot "
                "be stored"
            )
        existing = self.get(offer.tenant_id, offer.offer_id)
        if existing is not None:
            if existing != offer:
                raise OfferVersionConflictError(
                    f"offer {offer.offer_id!r} is already stored for tenant "
                    f"{offer.tenant_id!r} with different content; a production "
                    "ready offer is immutable and a change must be a new revision"
                )
            return
        payload = offer_to_payload(offer)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO offer_versions (
                    tenant_id,
                    offer_id,
                    offer
                ) VALUES (%s, %s, %s)
                """,
                (offer.tenant_id, offer.offer_id, Jsonb(payload)),
            )
        self._connection.commit()

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def offer_version_repository_from_env(
    database_url: str | None,
) -> OfferVersionRepository:
    """Select the production ready offer store from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so the stage 5
    offer a gate pinned survives a restart and is shared across the API and worker
    processes (SPEC.md sections 3 and 4); without one the process-local reference
    adapter keeps local development and the domain-only test interpreter working.
    A set but unusable configuration raises ``OfferVersionConfigurationError`` so
    a deployment cannot mistake a non-durable store for a durable one. The caller
    owns the returned adapter's lifecycle and calls ``close`` when the request
    ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryOfferVersionRepository()
    if psycopg is None:
        raise OfferVersionConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to use "
            "the process-local production ready offer store"
        )
    return PostgresOfferVersionRepository(psycopg.connect(database_url))
