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

from redops.contexts.execution.domain.connector import (
    ConnectorEffect,
    ExternalOperation,
)
from redops.contexts.execution.domain.entities import FunnelIntegration, LaunchQA
from redops.contexts.execution.domain.journey_release import JourneyRelease


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
    def list(self, tenant_id: str) -> tuple[LaunchQA, ...]:
        """Return every stored authorized launch QA for one client tenant."""

    @abc.abstractmethod
    def save(self, qa: LaunchQA) -> None:
        """Store an authorized launch QA, refusing a different same-id body."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""


class JourneyReleaseRepository(abc.ABC):
    """Seam for authorized journey releases, keyed by client and release id.

    SPEC.md section 3 names ``JourneyRelease`` (assets, routing, configuration
    digest, rollback ref) as a core aggregate whose invariant is "launch needs
    signed readiness and authorized release", and SPEC.md section 4 keeps a
    previous deployed release historically identifiable. The store is append-only
    per ``(tenant_id, release_id)``: an authorized release is immutable and a
    later launch is a new identity. ``list`` returns a client's releases for the
    ``/journeys`` read and ``close`` releases any connection the adapter opened.
    """

    @abc.abstractmethod
    def get(self, tenant_id: str, release_id: str) -> JourneyRelease | None:
        """Return the exact authorized release, or ``None`` if unknown."""

    @abc.abstractmethod
    def list(self, tenant_id: str) -> tuple[JourneyRelease, ...]:
        """Return every stored release for one client tenant."""

    @abc.abstractmethod
    def save(self, release: JourneyRelease) -> None:
        """Store an authorized release, refusing a different same-id body."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""


class ConnectorTransport(abc.ABC):
    """Sends one outbound effect to its external connector (SPEC.md section 6).

    This is the raw vendor seam: it performs the effect once and returns the
    connector's own reference for the operation. It makes no idempotency
    guarantee on its own; the replay-safe wrapper composes it with an
    ``ExternalOperationStore`` so a retried effect is sent at most once.
    """

    @abc.abstractmethod
    def send(self, effect: ConnectorEffect) -> str:
        """Perform the effect and return the external reference for the operation."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""


class ExternalOperationStore(abc.ABC):
    """Append-only log of the external operations an effect produced.

    SPEC.md section 11: "duplicate delivery creates one external operation". The
    log is keyed by ``(tenant_id, idempotency_key)`` and immutable: a record is
    returned for a retry, and a reused key with different content is refused
    rather than overwritten. SPEC.md section 9 scopes every read and write to one
    client.
    """

    @abc.abstractmethod
    def get(
        self, tenant_id: str, idempotency_key: str
    ) -> ExternalOperation | None:
        """Return the client's recorded operation, or ``None`` if absent."""

    @abc.abstractmethod
    def record(self, operation: ExternalOperation) -> None:
        """Append the operation, refusing a different body under a spent key."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""


class ConnectorPort(abc.ABC):
    """The replay-safe outbound seam a use case depends on (SPEC.md section 6).

    ``deliver`` returns the one recorded external operation for an effect. A
    repeat of the same effect resolves to the recorded operation without sending
    again; a reused key with different content is refused (SPEC.md section 11).
    """

    @abc.abstractmethod
    def deliver(self, effect: ConnectorEffect) -> ExternalOperation:
        """Deliver an effect at most once and return its recorded operation."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""
