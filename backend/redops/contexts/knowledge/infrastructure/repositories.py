"""Reference adapter for the ``SourceRecordStore`` port (SPEC.md section 6).

The process-local adapter exercises the port contract and the application seam
without a database, so immutability and tenant scoping are testable and the
durable PostgreSQL adapter follows the same contract.
``PostgresSourceRecordStore`` is the durable adapter whose table is created by
migration ``0011_source_records``; it is exercised wherever a psycopg driver and
a ``DATABASE_URL`` are available (see
``tests/unit/knowledge/test_source_record_store.py``). Row serialisation lives in
``mappers.py``.
"""

from __future__ import annotations

from typing import Any

from redops.contexts.knowledge.application.ports import SourceRecordStore
from redops.contexts.knowledge.domain.entities import SourceRecord
from redops.contexts.knowledge.domain.errors import (
    SourceRecordImmutableError,
    UnscopedSourceRecordError,
)
from redops.contexts.knowledge.infrastructure.mappers import (
    source_from_payload,
    source_to_payload,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class SourceRecordConfigurationError(RuntimeError):
    """The source record store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept
    an immutable source that vanishes on restart, so a missing psycopg driver is
    a configuration error rather than a degraded mode (SPEC.md sections 3 and 9).
    """


def _require_source_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a client's source record.

    SPEC.md sections 3 and 9 make a SourceRecord a client resource that must
    carry its tenant on every command and query; storing or resolving one without
    a client would either leak across clients or create an orphaned record.
    """

    if not value or not value.strip():
        raise UnscopedSourceRecordError(
            f"a tenant-scoped source record {operation} requires a non-blank "
            "tenant id; a source is a client resource and cannot be stored or "
            "read unscoped"
        )


class InMemorySourceRecordStore(SourceRecordStore):
    """Immutable, process-local source record store keyed by client and id."""

    def __init__(self) -> None:
        self._sources: dict[tuple[str, str], SourceRecord] = {}

    def list(self, tenant_id: str) -> tuple[SourceRecord, ...]:
        _require_source_tenant(tenant_id, "read")
        return tuple(
            self._sources[key]
            for key in sorted(
                (key for key in self._sources if key[0] == tenant_id),
                key=lambda key: (self._sources[key].captured_on, key[1]),
            )
        )

    def get(self, tenant_id: str, source_id: str) -> SourceRecord | None:
        _require_source_tenant(tenant_id, "read")
        return self._sources.get((tenant_id, source_id))

    def save(self, source: SourceRecord) -> None:
        _require_source_tenant(source.tenant_id, "write")
        key = (source.tenant_id, source.source_id)
        existing = self._sources.get(key)
        if existing is not None:
            if existing != source:
                raise SourceRecordImmutableError(
                    f"source record {source.source_id!r} is already stored for "
                    f"tenant {source.tenant_id!r} with different contents; an "
                    "original is immutable, so a corrected capture is a new "
                    "record, not a rewrite"
                )
            return
        self._sources[key] = source

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


class PostgresSourceRecordStore(SourceRecordStore):
    """Durable, immutable source record store backed by PostgreSQL.

    Rows are created by migration ``0011_source_records`` and are scoped by a
    NOT NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``list`` and ``get``
    read only the requested tenant's rows and rebuild the value object through
    ``source_from_payload``, so a stored row the value object would reject raises
    on load (SPEC.md section 3). ``save`` is idempotent for an identical replay
    and refuses a different same-key body, because the original is immutable.
    Row-level security (ADR 0004) is a follow-up; tenant scoping is enforced here
    by the WHERE clause and the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL source record adapter requires psycopg; "
                "install the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def list(self, tenant_id: str) -> tuple[SourceRecord, ...]:
        _require_source_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT source
                FROM source_records
                WHERE tenant_id = %s
                ORDER BY source->>'captured_on', source_id
                """,
                (tenant_id,),
            )
            rows = cursor.fetchall()
        return tuple(source_from_payload(row[0]) for row in rows)

    def get(self, tenant_id: str, source_id: str) -> SourceRecord | None:
        _require_source_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT source
                FROM source_records
                WHERE tenant_id = %s
                  AND source_id = %s
                """,
                (tenant_id, source_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return source_from_payload(row[0])

    def save(self, source: SourceRecord) -> None:
        _require_source_tenant(source.tenant_id, "write")
        existing = self.get(source.tenant_id, source.source_id)
        if existing is not None:
            if existing != source:
                raise SourceRecordImmutableError(
                    f"source record {source.source_id!r} is already stored for "
                    f"tenant {source.tenant_id!r} with different contents; an "
                    "original is immutable, so a corrected capture is a new "
                    "record, not a rewrite"
                )
            return
        payload = source_to_payload(source)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO source_records (
                    tenant_id,
                    source_id,
                    source
                ) VALUES (%s, %s, %s)
                """,
                (
                    source.tenant_id,
                    source.source_id,
                    Jsonb(payload),
                ),
            )
        self._connection.commit()

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def source_record_store_from_env(
    database_url: str | None,
) -> SourceRecordStore:
    """Select the source record store from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so an
    immutable source survives a restart and is shared across the API and worker
    processes (SPEC.md sections 3 and 4); without one the process-local reference
    adapter keeps local development and the domain-only test interpreter working.
    A set but unusable configuration raises ``SourceRecordConfigurationError`` so
    a deployment cannot mistake a non-durable store for a durable one. The caller
    owns the returned adapter's lifecycle and calls ``close`` when the request
    ends.
    """

    if database_url is None or not database_url.strip():
        return InMemorySourceRecordStore()
    if psycopg is None:
        raise SourceRecordConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to "
            "use the process-local source record store"
        )
    return PostgresSourceRecordStore(psycopg.connect(database_url))
