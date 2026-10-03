"""Application ports for the Execution bounded context (SPEC.md section 6).

A port is defined by an application need: the stage 9 and 10 gate use cases must
resolve the exact stage 8 ``FunnelIntegration`` a prior gate approved at "Funnel
Complete", instead of trusting a repeated request body that re-states the funnel
assets and its prospect path dry run (SPEC.md sections 3 and 4). The adapter is
chosen in the composition layer, so the use case depends on the interface, not a
concrete store.
"""

from __future__ import annotations

import abc

from redops.contexts.execution.domain.entities import FunnelIntegration, LaunchQA


class FunnelIntegrationRepository(abc.ABC):
    """Seam for approved stage 8 funnels, keyed by client and integration id.

    SPEC.md section 3: a passing gate pins the exact approved asset versions and
    intended use; SPEC.md section 4 keeps a previous approved version
    historically identifiable. The store is append-only per
    ``(tenant_id, integration_id)``: an approved funnel is immutable, and a later
    gate resolves it rather than re-declaring it. ``close`` releases any
    connection the adapter opened.
    """

    @abc.abstractmethod
    def get(
        self, tenant_id: str, integration_id: str
    ) -> FunnelIntegration | None:
        """Return the exact completed funnel, or ``None`` if unknown."""

    @abc.abstractmethod
    def save(self, funnel: FunnelIntegration) -> None:
        """Store a completed funnel, refusing a different same-id body."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""


class LaunchQARepository(abc.ABC):
    """Seam for approved stage 9 launch QAs, keyed by client and QA id.

    SPEC.md section 3: a passing gate pins the exact approved asset versions and
    intended use; SPEC.md section 4 keeps a previous approved version
    historically identifiable. The store is append-only per ``(tenant_id,
    qa_id)``: an authorized launch QA is immutable, and the stage 10 gate
    resolves it rather than re-declaring it. ``close`` releases any connection
    the adapter opened.
    """

    @abc.abstractmethod
    def get(self, tenant_id: str, qa_id: str) -> LaunchQA | None:
        """Return the exact authorized launch QA, or ``None`` if unknown."""

    @abc.abstractmethod
    def save(self, qa: LaunchQA) -> None:
        """Store an authorized launch QA, refusing a different same-id body."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""
