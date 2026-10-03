"""Application ports for the Engagement bounded context (SPEC.md section 6).

A port is defined by an application need: the ``/clients`` API surface must list
and create the stage 0 client workspace the rest of the pipeline anchors to,
without the entry point reaching into a concrete store. The ClientWorkspace is
the tenant root in SPEC.md section 3, so the port is always scoped by tenant and
a blank tenant is refused rather than read or written unscoped. The adapter is
chosen in the composition layer, so the use case depends on the interface, not a
concrete store.
"""

from __future__ import annotations

import abc

from redops.contexts.engagement.domain.entities import ClientWorkspace


class ClientWorkspaceStore(abc.ABC):
    """Seam for client workspaces, keyed by ``(tenant_id, workspace_id)``.

    SPEC.md section 3: every child resource belongs to exactly one client, and
    every tenant resource and query carries ``tenant_id``. ``list`` returns only
    the requested tenant's workspaces so a portfolio-wide read is impossible
    through this seam; ``close`` releases any connection the adapter opened.
    """

    @abc.abstractmethod
    def list(self, tenant_id: str) -> tuple[ClientWorkspace, ...]:
        """Return the tenant's workspaces, ordered by workspace id."""

    @abc.abstractmethod
    def get(self, tenant_id: str, workspace_id: str) -> ClientWorkspace | None:
        """Return one tenant-scoped workspace, or ``None`` if unknown."""

    @abc.abstractmethod
    def save(self, workspace: ClientWorkspace) -> None:
        """Create or update a workspace under its own tenant."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""
