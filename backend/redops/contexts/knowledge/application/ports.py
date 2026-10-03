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

from redops.contexts.knowledge.domain.entities import SourceRecord


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
