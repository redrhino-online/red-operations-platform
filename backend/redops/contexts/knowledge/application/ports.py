"""Application ports for the Knowledge bounded context (SPEC.md section 6).

A port is defined by an application need: the ``/clients/{id}/sources`` API
surface must ingest and list the immutable source records claims cite, without
the entry point reaching into a concrete store. A SourceRecord is a client
resource (SPEC.md section 3), so the port is always scoped by tenant and a blank
tenant is refused rather than read or written unscoped. The adapter is chosen in
the composition layer, so the use case depends on the interface, not a concrete
store.
"""

from __future__ import annotations

import abc

from redops.contexts.knowledge.domain.entities import Claim, SourceRecord


class SourceRecordStore(abc.ABC):
    """Seam for immutable source records, keyed by ``(tenant_id, source_id)``.

    SPEC.md section 3: the original is immutable and retrievable to authorized
    users, and every tenant resource and query carries ``tenant_id``. ``list``
    returns only the requested tenant's records; ``save`` refuses a different
    body under the same key so the stored original is never rewritten; ``close``
    releases any connection the adapter opened.
    """

    @abc.abstractmethod
    def list(self, tenant_id: str) -> tuple[SourceRecord, ...]:
        """Return the tenant's source records, ordered by capture then id."""

    @abc.abstractmethod
    def get(self, tenant_id: str, source_id: str) -> SourceRecord | None:
        """Return one tenant-scoped source record, or ``None`` if unknown."""

    @abc.abstractmethod
    def save(self, source: SourceRecord) -> None:
        """Store an immutable source record, refusing a different same-key body."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""


class ClaimStore(abc.ABC):
    """Seam for claims, keyed by ``(tenant_id, claim_id)`` (SPEC.md section 7).

    SPEC.md section 7 lists ``/claims`` and section 9 requires every tenant
    resource query to carry ``tenant_id``, so ``list`` and ``get`` return only the
    requested tenant's claims. A claim's provenance may change only through an
    append-only ``Claim.reclassify``, so ``save`` grows a stored claim's revision
    history but refuses a same-id re-statement that rewrites it; ``close``
    releases any connection the adapter opened.
    """

    @abc.abstractmethod
    def list(self, tenant_id: str) -> tuple[Claim, ...]:
        """Return the tenant's claims, ordered by id."""

    @abc.abstractmethod
    def get(self, tenant_id: str, claim_id: str) -> Claim | None:
        """Return one tenant-scoped claim, or ``None`` if unknown."""

    @abc.abstractmethod
    def save(self, claim: Claim) -> None:
        """Store a claim, refusing a same-id non-append-only re-statement."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""


class KnowledgeRetriever(abc.ABC):
    """Seam for tenant-scoped retrieval of one client's knowledge.

    SPEC.md section 5 gives the Knowledge Management agent a client's source
    index, and SPEC.md section 3 starts with full text and vector retrieval over
    that client's own records. Retrieval therefore always runs against exactly
    one client: a query that would match another client's material returns
    nothing (SPEC.md sections 3 and 9). SPEC.md section 13 condition 3 names the
    retrieval layer explicitly, so the seam exists instead of an implicit store
    read. ``retrieve`` returns claims, which carry their own source citations, so
    a caller can attribute every result.
    """

    @abc.abstractmethod
    def retrieve(self, tenant_id: str, query: str) -> tuple[Claim, ...]:
        """Return the tenant's claims matching the query, with their citations."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""
