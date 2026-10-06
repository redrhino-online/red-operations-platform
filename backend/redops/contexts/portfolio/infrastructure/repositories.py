"""Reference adapters for the Portfolio opportunity port (SPEC.md section 6).

The process-local adapter exercises the port contract and the application seam
without a database, so the append-only rule (an opportunity cannot be re-stated
with different content under its id) is testable and the durable PostgreSQL
adapter follows the same contract. ``PostgresOpportunityRepository`` is the
durable adapter whose table is created by migration ``0017_opportunities``; it is
exercised wherever a psycopg driver and a ``DATABASE_URL`` are available (see
``tests/unit/portfolio/test_opportunity_postgres.py``). Row serialisation lives
in ``mappers.py``.
"""

from __future__ import annotations

from typing import Any

from redops.contexts.portfolio.application.ports import (
    OpportunityRepository,
    UmbrellaPlanRepository,
)
from redops.contexts.portfolio.domain.errors import (
    OpportunityConflictError,
    OpportunityTenantBoundaryError,
    UmbrellaPlanConflictError,
    UmbrellaPlanTenantBoundaryError,
)
from redops.contexts.portfolio.domain.value_objects import (
    Opportunity,
    UmbrellaPlan,
)
from redops.contexts.portfolio.infrastructure.mappers import (
    opportunity_from_payload,
    opportunity_to_payload,
    umbrella_plan_from_payload,
    umbrella_plan_to_payload,
)

try:  # psycopg is an app dependency; the domain-only test env lacks it.
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - taken on the domain-only interpreter
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class OpportunityConfigurationError(RuntimeError):
    """The opportunity store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept a
    portfolio opportunity that vanishes on restart, so a missing psycopg driver
    is a configuration error rather than a degraded mode (SPEC.md sections 7
    and 9).
    """


def _require_opportunity_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a tenant's opportunity register.

    SPEC.md sections 3 and 9 make an opportunity a client resource that must
    carry its tenant on every command and query; reading or storing one without a
    client would either leak across clients or create an orphaned proposal.
    """

    if not value or not value.strip():
        raise OpportunityTenantBoundaryError(
            f"a tenant-scoped opportunity {operation} requires a non-blank "
            "tenant id; an opportunity is a client resource and cannot be "
            "stored or read unscoped"
        )


class InMemoryOpportunityRepository(OpportunityRepository):
    """Append-only, process-local opportunity store."""

    def __init__(self) -> None:
        self._opportunities: dict[tuple[str, str], Opportunity] = {}

    def get(self, tenant_id: str, opportunity_id: str) -> Opportunity | None:
        _require_opportunity_tenant(tenant_id, "read")
        return self._opportunities.get((tenant_id, opportunity_id))

    def list(self, tenant_id: str) -> tuple[Opportunity, ...]:
        _require_opportunity_tenant(tenant_id, "read")
        return tuple(
            opportunity
            for (stored_tenant, _opportunity_id), opportunity
            in self._opportunities.items()
            if stored_tenant == tenant_id
        )

    def save(self, opportunity: Opportunity) -> None:
        _require_opportunity_tenant(opportunity.tenant_id, "write")
        key = (opportunity.tenant_id, opportunity.opportunity_id)
        existing = self._opportunities.get(key)
        if existing is not None and existing != opportunity:
            raise OpportunityConflictError(
                f"opportunity {opportunity.opportunity_id!r} is already stored "
                f"for tenant {opportunity.tenant_id!r} with different content; "
                "the opportunity register is append-only"
            )
        self._opportunities[key] = opportunity

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


class PostgresOpportunityRepository(OpportunityRepository):
    """Durable, append-only opportunity store backed by PostgreSQL.

    Rows are created by migration ``0017_opportunities`` and are scoped by a NOT
    NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``list`` and ``get``
    read only the requested tenant's rows and rebuild each opportunity through
    ``opportunity_from_payload``, so a stored row the value object would reject
    raises on load rather than being read back as a client fact (SPEC.md
    sections 1 and 5). ``save`` inserts a new opportunity and treats an exact
    replay as idempotent while refusing a same-id row with different content.
    Row-level security (ADR 0004) is a follow-up; tenant scoping is enforced here
    by the WHERE clause and the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL opportunity adapter requires psycopg; install "
                "the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def get(self, tenant_id: str, opportunity_id: str) -> Opportunity | None:
        _require_opportunity_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT opportunity
                FROM opportunities
                WHERE tenant_id = %s
                  AND opportunity_id = %s
                """,
                (tenant_id, opportunity_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return opportunity_from_payload(row[0])

    def list(self, tenant_id: str) -> tuple[Opportunity, ...]:
        _require_opportunity_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT opportunity
                FROM opportunities
                WHERE tenant_id = %s
                ORDER BY opportunity_id
                """,
                (tenant_id,),
            )
            rows = cursor.fetchall()
        return tuple(opportunity_from_payload(row[0]) for row in rows)

    def save(self, opportunity: Opportunity) -> None:
        _require_opportunity_tenant(opportunity.tenant_id, "write")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT opportunity
                FROM opportunities
                WHERE tenant_id = %s
                  AND opportunity_id = %s
                """,
                (opportunity.tenant_id, opportunity.opportunity_id),
            )
            row = cursor.fetchone()
        if row is not None:
            existing = opportunity_from_payload(row[0])
            if existing != opportunity:
                raise OpportunityConflictError(
                    f"opportunity {opportunity.opportunity_id!r} is already "
                    f"stored for tenant {opportunity.tenant_id!r} with different "
                    "content; the opportunity register is append-only"
                )
            return
        payload = opportunity_to_payload(opportunity)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO opportunities (
                    tenant_id,
                    opportunity_id,
                    opportunity
                ) VALUES (%s, %s, %s)
                """,
                (
                    opportunity.tenant_id,
                    opportunity.opportunity_id,
                    Jsonb(payload),
                ),
            )
        self._connection.commit()

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def opportunity_repository_from_env(
    database_url: str | None,
) -> OpportunityRepository:
    """Select the opportunity store from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so the
    portfolio opportunity register survives a restart (SPEC.md sections 7 and 9);
    without one the process-local reference adapter keeps local development and
    the domain-only test interpreter working. A set but unusable configuration
    raises ``OpportunityConfigurationError`` so a deployment cannot mistake a
    non-durable store for a durable one. The caller owns the returned adapter's
    lifecycle and calls ``close`` when the request ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryOpportunityRepository()
    if psycopg is None:
        raise OpportunityConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to use "
            "the process-local opportunity store"
        )
    return PostgresOpportunityRepository(psycopg.connect(database_url))


class UmbrellaPlanConfigurationError(RuntimeError):
    """The umbrella plan store was configured without a usable driver.

    A set ``DATABASE_URL`` is an explicit instruction to use the durable store
    (ADR 0003). Silently falling back to the process-local adapter would accept a
    canon umbrella plan that vanishes on restart, so a missing psycopg driver is a
    configuration error rather than a degraded mode (SPEC.md sections 7 and 9).
    """


def _require_umbrella_plan_tenant(value: str, operation: str) -> None:
    """Refuse an unscoped read or write of a tenant's umbrella plan register.

    SPEC.md sections 3 and 9 make an umbrella plan a client resource that must
    carry its tenant on every command and query; reading or storing one without a
    client would either leak across clients or create an orphaned plan.
    """

    if not value or not value.strip():
        raise UmbrellaPlanTenantBoundaryError(
            f"a tenant-scoped umbrella plan {operation} requires a non-blank "
            "tenant id; an umbrella plan is a client resource and cannot be "
            "stored or read unscoped"
        )


class InMemoryUmbrellaPlanRepository(UmbrellaPlanRepository):
    """Append-only, process-local umbrella plan store."""

    def __init__(self) -> None:
        self._plans: dict[tuple[str, str], UmbrellaPlan] = {}

    def get(self, tenant_id: str, plan_id: str) -> UmbrellaPlan | None:
        _require_umbrella_plan_tenant(tenant_id, "read")
        return self._plans.get((tenant_id, plan_id))

    def list(self, tenant_id: str) -> tuple[UmbrellaPlan, ...]:
        _require_umbrella_plan_tenant(tenant_id, "read")
        return tuple(
            plan
            for (stored_tenant, _plan_id), plan in self._plans.items()
            if stored_tenant == tenant_id
        )

    def save(self, plan: UmbrellaPlan) -> None:
        _require_umbrella_plan_tenant(plan.tenant_id, "write")
        key = (plan.tenant_id, plan.plan_id)
        existing = self._plans.get(key)
        if existing is not None and existing != plan:
            raise UmbrellaPlanConflictError(
                f"umbrella plan {plan.plan_id!r} is already stored for tenant "
                f"{plan.tenant_id!r} with different content; the umbrella plan "
                "register is append-only"
            )
        self._plans[key] = plan

    def close(self) -> None:
        """A process-local store owns no external resource to release."""

        return None


class PostgresUmbrellaPlanRepository(UmbrellaPlanRepository):
    """Durable, append-only umbrella plan store backed by PostgreSQL.

    Rows are created by migration ``0019_umbrella_plans`` and are scoped by a NOT
    NULL ``tenant_id`` column (SPEC.md sections 3 and 9). ``list`` and ``get``
    read only the requested tenant's rows and rebuild each plan through
    ``umbrella_plan_from_payload``, so a stored row the aggregate would reject
    raises on load rather than being read back as a client plan (SPEC.md sections
    1 and 5). ``save`` inserts a new plan and treats an exact replay as idempotent
    while refusing a same-id row with different content. Row-level security (ADR
    0004) is a follow-up; tenant scoping is enforced here by the WHERE clause and
    the NOT NULL column.
    """

    def __init__(self, connection: "psycopg.Connection[Any]") -> None:
        if psycopg is None:
            raise RuntimeError(
                "the PostgreSQL umbrella plan adapter requires psycopg; install "
                "the app dependencies (psycopg[binary]) to use it"
            )
        self._connection = connection

    def get(self, tenant_id: str, plan_id: str) -> UmbrellaPlan | None:
        _require_umbrella_plan_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT plan
                FROM umbrella_plans
                WHERE tenant_id = %s
                  AND plan_id = %s
                """,
                (tenant_id, plan_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return umbrella_plan_from_payload(row[0])

    def list(self, tenant_id: str) -> tuple[UmbrellaPlan, ...]:
        _require_umbrella_plan_tenant(tenant_id, "read")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT plan
                FROM umbrella_plans
                WHERE tenant_id = %s
                ORDER BY plan_id
                """,
                (tenant_id,),
            )
            rows = cursor.fetchall()
        return tuple(umbrella_plan_from_payload(row[0]) for row in rows)

    def save(self, plan: UmbrellaPlan) -> None:
        _require_umbrella_plan_tenant(plan.tenant_id, "write")
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT plan
                FROM umbrella_plans
                WHERE tenant_id = %s
                  AND plan_id = %s
                """,
                (plan.tenant_id, plan.plan_id),
            )
            row = cursor.fetchone()
        if row is not None:
            existing = umbrella_plan_from_payload(row[0])
            if existing != plan:
                raise UmbrellaPlanConflictError(
                    f"umbrella plan {plan.plan_id!r} is already stored for tenant "
                    f"{plan.tenant_id!r} with different content; the umbrella "
                    "plan register is append-only"
                )
            return
        payload = umbrella_plan_to_payload(plan)
        with self._connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO umbrella_plans (
                    tenant_id,
                    plan_id,
                    plan
                ) VALUES (%s, %s, %s)
                """,
                (
                    plan.tenant_id,
                    plan.plan_id,
                    Jsonb(payload),
                ),
            )
        self._connection.commit()

    def close(self) -> None:
        """Release the connection the adapter holds for the request."""

        self._connection.close()


def umbrella_plan_repository_from_env(
    database_url: str | None,
) -> UmbrellaPlanRepository:
    """Select the umbrella plan store from configuration (ADR 0003).

    With a ``DATABASE_URL`` the durable PostgreSQL adapter is used so the canon
    umbrella plan survives a restart (SPEC.md sections 7 and 9); without one the
    process-local reference adapter keeps local development and the domain-only
    test interpreter working. A set but unusable configuration raises
    ``UmbrellaPlanConfigurationError`` so a deployment cannot mistake a
    non-durable store for a durable one. The caller owns the returned adapter's
    lifecycle and calls ``close`` when the request ends.
    """

    if database_url is None or not database_url.strip():
        return InMemoryUmbrellaPlanRepository()
    if psycopg is None:
        raise UmbrellaPlanConfigurationError(
            "DATABASE_URL is set but no PostgreSQL driver is installed; install "
            "the app dependencies (psycopg[binary]) or unset DATABASE_URL to use "
            "the process-local umbrella plan store"
        )
    return PostgresUmbrellaPlanRepository(psycopg.connect(database_url))
