"""In-memory gate ledger repository: the reference adapter for the port.

Implements ``GateLedgerRepository`` (SPEC.md section 6: infrastructure adapters
implement ports) with a process-local, append-only store. It is the reference
adapter that satisfies the port contract and the double used by application and
API tests before a PostgreSQL-backed store exists.

ADR 0003 makes RED's gate and decision records durable in PostgreSQL. Two
adapters implement the same port: ``InMemoryGateLedgerRepository`` is the
process-local reference adapter used by application and API tests, and
``PostgresGateLedgerRepository`` is the durable adapter whose table is created
by migration ``0001_gate_decisions``. The PostgreSQL adapter is exercised
wherever a psycopg driver and a ``DATABASE_URL`` are available (see
``tests/unit/governance/test_gate_ledger_postgres.py``); the domain-only test
interpreter ships no driver, so the in-memory adapter keeps the port contract
covered there. Row serialisation lives in ``mappers.py``.
"""

from __future__ import annotations

from typing import Any

from redops.contexts.governance.application.ports import GateLedgerRepository
from redops.contexts.governance.domain.entities import GateDecision, GateLedger
from redops.contexts.governance.domain.errors import CrossTenantGateError
from redops.contexts.governance.domain.value_objects import StageTemplate
from redops.contexts.governance.infrastructure.mappers import (
    decision_from_payload,
    decision_to_payload,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class GateLedgerConfigurationError(RuntimeError):
    """The gate ledger store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept
    and report gate decisions that vanish on restart, so a missing psycopg
    driver is a configuration error rather than a degraded mode (SPEC.md
    sections 3, 4 and 9).
    """


class InMemoryGateLedgerRepository(GateLedgerRepository):
    """Append-only, process-local gate decision store keyed by client and template."""

    def __init__(self) -> None:
        self._decisions: list[GateDecision] = []

    def load(self, template: StageTemplate, tenant_id: str) -> GateLedger:
        if not tenant_id or not tenant_id.strip():
            raise CrossTenantGateError(
                "a tenant-scoped gate ledger load requires a non-blank tenant id"
            )
        ledger = GateLedger(template, tenant_id=tenant_id)
        for decision in self._decisions:
            if decision.template_version != template.version:
                continue
            if decision.tenant_id != tenant_id:
                continue
            ledger.record(decision)
        return ledger

    def append(self, decision: GateDecision) -> None:
        if not decision.tenant_id or not decision.tenant_id.strip():
            raise CrossTenantGateError(
                "a stored gate decision requires a non-blank tenant id; a gate "
                "decision is a client resource and cannot be stored unscoped"
            )
        self._decisions.append(decision)

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


def _require_tenant_id(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a client gate decision.

    SPEC.md sections 3 and 9 make a gate decision a client resource that must
    carry its tenant on every command and query; storing or loading one without
    a client would either leak across clients or create an orphaned record.
    """
    if not value or not value.strip():
        raise CrossTenantGateError(
            f"a tenant-scoped gate ledger {operation} requires a non-blank "
            "tenant id; a gate decision is a client resource and cannot be "
            "stored or read unscoped"
        )


class PostgresGateLedgerRepository(GateLedgerRepository):
    """Durable, append-only gate decision store backed by PostgreSQL.

    Rows are created by migration ``0001_gate_decisions`` and are scoped by a
    NOT NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``load`` reads only
    the requested tenant's rows for the requested template version, in append
    order, and replays each one through ``GateLedger.record`` so the domain
    re-applies the canonical template, exact-package, checkpoint, prerequisite,
    dependency and tenant rules. A stored row the domain rejects raises on load
    rather than being read back as an approved gate (SPEC.md section 4).

    The adapter owns the transaction for a single append: a decision is written
    and committed as one row, and a superseding decision is inserted alongside
    it, never updating an earlier row (SPEC.md section 3: history is append
    only). Row-level security (ADR 0004) is a follow-up; tenant scoping is
    enforced here by the WHERE clause and the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL gate ledger adapter requires psycopg; install "
                "the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def load(self, template: StageTemplate, tenant_id: str) -> GateLedger:
        _require_tenant_id(tenant_id, "load")
        ledger = GateLedger(template, tenant_id=tenant_id)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT decision
                FROM gate_decisions
                WHERE tenant_id = %s AND template_version = %s
                ORDER BY id
                """,
                (tenant_id, template.version),
            )
            rows = cursor.fetchall()
        for (payload,) in rows:
            ledger.record(decision_from_payload(payload))
        return ledger

    def append(self, decision: GateDecision) -> None:
        _require_tenant_id(decision.tenant_id, "append")
        payload = decision_to_payload(decision)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO gate_decisions (
                    tenant_id,
                    template_version,
                    stage_number,
                    disposition,
                    decided_on,
                    due_on,
                    decision
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    decision.tenant_id,
                    decision.template_version,
                    decision.stage_number,
                    decision.disposition.value,
                    decision.decided_on,
                    decision.due_on,
                    Jsonb(payload),
                ),
            )
        self._connection.commit()

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def gate_ledger_repository_from_env(
    database_url: str | None,
) -> GateLedgerRepository:
    """Select the gate ledger adapter from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so approved
    gate progress survives a restart and is shared across the API and worker
    processes (SPEC.md sections 3 and 4); without one the process-local
    reference adapter keeps local development and the domain-only test
    interpreter working. A set but unusable configuration raises
    ``GateLedgerConfigurationError`` so a deployment cannot mistake a
    non-durable ledger for a durable one. The caller owns the returned adapter's
    lifecycle and calls ``close`` when the request ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryGateLedgerRepository()
    if psycopg is None:
        raise GateLedgerConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to "
            "use the process-local gate ledger"
        )
    return PostgresGateLedgerRepository(psycopg.connect(database_url))
