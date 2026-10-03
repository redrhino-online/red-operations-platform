"""Application ports for the Operations bounded context (SPEC.md section 6).

SPEC.md section 7 exposes the command center's intervention cards at
``/interventions`` and allows a card to be dismissed with rationale. The cards
themselves are derived on every read from the Governance production view, so the
only durable Operations record is the human decision to suppress one; this port
lets the API store and resolve that decision without depending on a concrete
store. The adapter is chosen in the composition layer (SPEC.md section 6).
"""

from __future__ import annotations

import abc

from redops.contexts.operations.domain.value_objects import InterventionDismissal


class InterventionDismissalRepository(abc.ABC):
    """Seam for durable operator dismissals of intervention cards.

    A dismissal is an append-only operator decision (SPEC.md sections 7 and 9),
    keyed by ``(tenant_id, client, reason, subject)``. ``list`` returns one
    client's dismissals so the read surface can mark the matching derived cards
    dismissed, and ``close`` releases any connection the adapter opened.
    """

    @abc.abstractmethod
    def list(
        self, tenant_id: str, client: str
    ) -> tuple[InterventionDismissal, ...]:
        """Return every dismissal stored for one client under its tenant."""

    @abc.abstractmethod
    def save(self, dismissal: InterventionDismissal) -> None:
        """Store a dismissal, refusing a different same-key re-statement."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""
