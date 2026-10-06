"""Application ports for the Portfolio bounded context (SPEC.md section 6).

SPEC.md section 7 lists ``/opportunities`` and SPEC.md section 1 puts portfolio
expansion in the product contract. The canon's Grow motion splits the foundation
offer into smaller offers that are new entry points and raise customer lifetime
value (canon files 11 and 12; SPEC.md section 12.3). This port lets the API store
and read the proposed opportunity register without depending on a concrete store;
the adapter is chosen in the composition layer (SPEC.md section 6).
"""

from __future__ import annotations

import abc

from redops.contexts.portfolio.domain.value_objects import (
    Opportunity,
    UmbrellaPlan,
)


class OpportunityRepository(abc.ABC):
    """Seam for the durable, tenant-scoped portfolio opportunity register.

    The register is append-only keyed by ``(tenant_id, opportunity_id)`` (SPEC.md
    section 3, Decision invariant: decision history is append only). ``list``
    returns one tenant's opportunities, ``get`` resolves one exact id, and
    ``close`` releases any connection the adapter opened.
    """

    @abc.abstractmethod
    def get(self, tenant_id: str, opportunity_id: str) -> Opportunity | None:
        """Return one opportunity under its tenant, or ``None`` if absent."""

    @abc.abstractmethod
    def list(self, tenant_id: str) -> tuple[Opportunity, ...]:
        """Return every opportunity stored for one tenant."""

    @abc.abstractmethod
    def save(self, opportunity: Opportunity) -> None:
        """Store an opportunity, refusing a different same-id re-statement."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""


class UmbrellaPlanRepository(abc.ABC):
    """Seam for the durable, tenant-scoped canon umbrella plan register.

    SPEC.md section 12.5 records the canon umbrella plan (the Online Business
    Launch Map and the one-page Bulletproof Business Plan, canon files 00 and 01)
    as a planning decision over the whole stage 0-10 pipeline, revisited every 90
    days. The production view carries it as a tenant-scoped read-model projection
    (SPEC.md section 4), so the API needs a port to load the stored plan without
    depending on a concrete store; the adapter is chosen in the composition layer
    (SPEC.md section 6). The register is append-only keyed by
    ``(tenant_id, plan_id)`` (SPEC.md section 3, Decision invariant: decision
    history is append only). ``list`` returns one tenant's plans, ``get`` resolves
    one exact id, and ``close`` releases any connection the adapter opened.
    """

    @abc.abstractmethod
    def get(self, tenant_id: str, plan_id: str) -> UmbrellaPlan | None:
        """Return one umbrella plan under its tenant, or ``None`` if absent."""

    @abc.abstractmethod
    def list(self, tenant_id: str) -> tuple[UmbrellaPlan, ...]:
        """Return every umbrella plan stored for one tenant."""

    @abc.abstractmethod
    def save(self, plan: UmbrellaPlan) -> None:
        """Store a plan, refusing a different same-id re-statement."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""
