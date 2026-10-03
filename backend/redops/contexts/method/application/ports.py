"""Application ports for the Method bounded context (SPEC.md section 6).

A port is defined by an application need: the stage 6 to 10 gate use cases must
resolve the exact approved method version a prior gate was pinned to, instead of
trusting a repeated request body that re-states the approval. The adapter is
chosen in the composition layer, so the use case depends on the interface, not a
concrete store.
"""

from __future__ import annotations

import abc

from redops.contexts.method.domain.entities import MethodVersion
from redops.contexts.method.domain.value_objects import SemanticVersion


class MethodVersionRepository(abc.ABC):
    """Seam for approved method versions, keyed by client and exact version.

    SPEC.md section 3: approval pins an exact version and intended use; SPEC.md
    section 4 keeps a previous approved version historically identifiable. The
    store is append-only per ``(tenant_id, method_id, semantic_version)``: an
    approved version is immutable, and a later gate resolves it rather than
    re-declaring it. ``close`` releases any connection the adapter opened.
    """

    @abc.abstractmethod
    def get(
        self,
        tenant_id: str,
        method_id: str,
        version: SemanticVersion,
    ) -> MethodVersion | None:
        """Return the exact approved method version, or ``None`` if unknown."""

    @abc.abstractmethod
    def list(self, tenant_id: str) -> tuple[MethodVersion, ...]:
        """Return the tenant's approved method versions, ordered by identity."""

    @abc.abstractmethod
    def save(self, method: MethodVersion) -> None:
        """Store an approved method version, refusing a different same-key body."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""
