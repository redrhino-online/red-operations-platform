"""Reference adapters for the ``MeasurementRegistry`` port (SPEC.md section 6).

The process-local adapter exercises the port contract and the application seam
without a database, so append-only registration and tenant scoping are testable
and the durable PostgreSQL adapter follows the same contract.
``PostgresMeasurementRegistry`` is the durable adapter whose tables are created by
migration ``0014_measurements``; it is exercised wherever a psycopg driver and a
``DATABASE_URL`` are available (see
``tests/unit/measurement/test_measurement_registry.py``). Row serialisation lives
in ``mappers.py``.
"""

from __future__ import annotations

from typing import Any

from redops.contexts.measurement.application.ports import MeasurementRegistry
from redops.contexts.measurement.domain.errors import (
    MeasurementConflictError,
    UnscopedMeasurementError,
)
from redops.contexts.measurement.domain.value_objects import (
    MeasurementRecord,
    MetricDefinition,
)
from redops.contexts.measurement.infrastructure.mappers import (
    metric_from_payload,
    metric_to_payload,
    record_from_payload,
    record_to_payload,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class MeasurementConfigurationError(RuntimeError):
    """The measurement registry was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept a
    metric observation that vanishes on restart, so a missing psycopg driver is a
    configuration error rather than a degraded mode (SPEC.md sections 3 and 9).
    """


def _require_measurement_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a client's measurement registry.

    SPEC.md sections 3 and 9 make a Measurement a client resource that must carry
    its tenant on every command and query; storing or resolving one without a
    client would either leak across clients or create an orphaned registry row.
    """

    if not value or not value.strip():
        raise UnscopedMeasurementError(
            f"a tenant-scoped measurement registry {operation} requires a "
            "non-blank tenant id; a measurement is a client resource and cannot "
            "be stored or read unscoped"
        )


def _require_metric_append_only(
    existing: MetricDefinition, candidate: MetricDefinition
) -> None:
    """Refuse a same-version metric re-statement with a different body.

    SPEC.md section 3 keys an observation by its exact versioned metric, so a
    registered ``(metric_id, version)`` is append-only: an identical replay is
    idempotent, but a redefinition of the same version is refused and must be a
    new version instead.
    """

    if existing != candidate:
        raise MeasurementConflictError(
            f"metric definition {candidate.metric_id!r} version "
            f"{candidate.version} is already registered for tenant "
            f"{candidate.tenant_id!r} with different contents; a metric "
            "redefinition is a new version, not a rewrite"
        )


def _require_record_append_only(
    existing: MeasurementRecord, candidate: MeasurementRecord
) -> None:
    """Refuse a same-id observation re-statement with a different body.

    SPEC.md section 3 keys an observation by its metric and window and keeps it
    distinct from a causal conclusion, so a recorded ``record_id`` is
    append-only: an identical replay is idempotent, but a changed observation is
    refused rather than silently rewriting a figure historical results cite.
    """

    if existing != candidate:
        raise MeasurementConflictError(
            f"measurement record {candidate.record_id!r} is already stored for "
            f"tenant {candidate.tenant_id!r} with different contents; an "
            "observation is append-only and a corrected figure is a new record"
        )


class InMemoryMeasurementRegistry(MeasurementRegistry):
    """Append-only, process-local metric registry keyed by client."""

    def __init__(self) -> None:
        self._metrics: dict[tuple[str, str, int], MetricDefinition] = {}
        self._records: dict[tuple[str, str], MeasurementRecord] = {}

    def list_metrics(self, tenant_id: str) -> tuple[MetricDefinition, ...]:
        _require_measurement_tenant(tenant_id, "read")
        return tuple(
            self._metrics[key]
            for key in sorted(
                (key for key in self._metrics if key[0] == tenant_id),
                key=lambda key: (key[1], key[2]),
            )
        )

    def get_metric(
        self, tenant_id: str, metric_id: str, version: int
    ) -> MetricDefinition | None:
        _require_measurement_tenant(tenant_id, "read")
        return self._metrics.get((tenant_id, metric_id, version))

    def list_records(self, tenant_id: str) -> tuple[MeasurementRecord, ...]:
        _require_measurement_tenant(tenant_id, "read")
        return tuple(
            self._records[key]
            for key in sorted(
                (key for key in self._records if key[0] == tenant_id),
                key=lambda key: (
                    self._records[key].recorded_on,
                    key[1],
                ),
            )
        )

    def get_record(
        self, tenant_id: str, record_id: str
    ) -> MeasurementRecord | None:
        _require_measurement_tenant(tenant_id, "read")
        return self._records.get((tenant_id, record_id))

    def save_metric(self, metric: MetricDefinition) -> None:
        _require_measurement_tenant(metric.tenant_id, "write")
        key = (metric.tenant_id, metric.metric_id, metric.version)
        existing = self._metrics.get(key)
        if existing is not None:
            _require_metric_append_only(existing, metric)
            return
        self._metrics[key] = metric

    def save_record(self, record: MeasurementRecord) -> None:
        _require_measurement_tenant(record.tenant_id, "write")
        key = (record.tenant_id, record.record_id)
        existing = self._records.get(key)
        if existing is not None:
            _require_record_append_only(existing, record)
            return
        self._records[key] = record

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


class PostgresMeasurementRegistry(MeasurementRegistry):
    """Durable, append-only metric registry backed by PostgreSQL.

    Rows are created by migration ``0014_measurements`` and are scoped by a NOT
    NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``list`` and ``get``
    read only the requested tenant's rows and rebuild the values through the
    mappers, so a stored row the domain would reject raises on load (SPEC.md
    section 3). A ``save`` is idempotent for an identical replay and refuses a
    different same-key body, because a metric version and an observation are
    append-only. Row-level security (ADR 0004) is a follow-up; tenant scoping is
    enforced here by the WHERE clause and the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL measurement registry requires psycopg; "
                "install the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def list_metrics(self, tenant_id: str) -> tuple[MetricDefinition, ...]:
        _require_measurement_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT definition
                FROM metric_definitions
                WHERE tenant_id = %s
                ORDER BY metric_id, version
                """,
                (tenant_id,),
            )
            rows = cursor.fetchall()
        return tuple(metric_from_payload(row[0]) for row in rows)

    def get_metric(
        self, tenant_id: str, metric_id: str, version: int
    ) -> MetricDefinition | None:
        _require_measurement_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT definition
                FROM metric_definitions
                WHERE tenant_id = %s
                  AND metric_id = %s
                  AND version = %s
                """,
                (tenant_id, metric_id, version),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return metric_from_payload(row[0])

    def list_records(self, tenant_id: str) -> tuple[MeasurementRecord, ...]:
        _require_measurement_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT record
                FROM measurement_records
                WHERE tenant_id = %s
                ORDER BY record->>'recorded_on', record_id
                """,
                (tenant_id,),
            )
            rows = cursor.fetchall()
        return tuple(record_from_payload(row[0]) for row in rows)

    def get_record(
        self, tenant_id: str, record_id: str
    ) -> MeasurementRecord | None:
        _require_measurement_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT record
                FROM measurement_records
                WHERE tenant_id = %s
                  AND record_id = %s
                """,
                (tenant_id, record_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return record_from_payload(row[0])

    def save_metric(self, metric: MetricDefinition) -> None:
        _require_measurement_tenant(metric.tenant_id, "write")
        existing = self.get_metric(
            metric.tenant_id, metric.metric_id, metric.version
        )
        if existing is not None:
            _require_metric_append_only(existing, metric)
            return
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO metric_definitions (
                    tenant_id,
                    metric_id,
                    version,
                    definition
                ) VALUES (%s, %s, %s, %s)
                ON CONFLICT (tenant_id, metric_id, version) DO NOTHING
                """,
                (
                    metric.tenant_id,
                    metric.metric_id,
                    metric.version,
                    Jsonb(metric_to_payload(metric)),
                ),
            )
        self._connection.commit()

    def save_record(self, record: MeasurementRecord) -> None:
        _require_measurement_tenant(record.tenant_id, "write")
        existing = self.get_record(record.tenant_id, record.record_id)
        if existing is not None:
            _require_record_append_only(existing, record)
            return
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO measurement_records (
                    tenant_id,
                    record_id,
                    record
                ) VALUES (%s, %s, %s)
                ON CONFLICT (tenant_id, record_id) DO NOTHING
                """,
                (
                    record.tenant_id,
                    record.record_id,
                    Jsonb(record_to_payload(record)),
                ),
            )
        self._connection.commit()

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def measurement_registry_from_env(
    database_url: str | None,
) -> MeasurementRegistry:
    """Select the measurement registry from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so a metric
    definition and an observation survive a restart and are shared across the API
    and worker processes (SPEC.md sections 3 and 4). Without one the process-local
    reference adapter keeps local development and the domain-only test interpreter
    working. A set but unusable configuration raises
    ``MeasurementConfigurationError`` so a deployment cannot mistake a
    non-durable store for a durable one. The caller owns the returned adapter's
    lifecycle and calls ``close`` when the request ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryMeasurementRegistry()
    if psycopg is None:
        raise MeasurementConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to "
            "use the process-local measurement registry"
        )
    return PostgresMeasurementRegistry(psycopg.connect(database_url))
