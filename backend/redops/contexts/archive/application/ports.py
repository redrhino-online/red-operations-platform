"""Application ports for the Stage Artifact archive bounded context.

A port is defined by an application need: the ``/clients/{id}/artifacts`` API
surface must drop and list the archived markdown artifacts of every stage
(docs/specs/stage-artifact-archive.md section 1.3) without the entry point
reaching into a concrete store. A StageArtifact is a client resource (SPEC.md
section 3), so the port is always scoped by tenant and a blank tenant is
refused rather than read or written unscoped. The adapter is chosen in the
composition layer, so the use case depends on the interface, not a concrete
store.
"""

from __future__ import annotations

import abc

from redops.contexts.archive.domain.entities import StageArtifact


class StageArtifactStore(abc.ABC):
    """Seam for archived stage artifacts, keyed by the archive's append-only key.

    The key is ``(tenant_id, workspace_id, asset_id, version)``
    (docs/specs/stage-artifact-archive.md section 1.1). ``save`` is append-only:
    an identical replay of the key with identical content is an idempotent
    success and the same key with different content is refused with a named
    conflict, so archived content is never rewritten. ``list`` returns only the
    requested tenant's artifacts, filtered and ordered by stage, kind, asset and
    version descending; ``next_version`` allocates the next free version for one
    asset so an omitted version drops at the next free slot. ``close`` releases
    any connection the adapter opened.
    """

    @abc.abstractmethod
    def save(self, artifact: StageArtifact) -> None:
        """Append one artifact, idempotent for an identical same-key replay."""

    @abc.abstractmethod
    def list(
        self,
        tenant_id: str,
        workspace_id: str | None = None,
        stage_number: int | None = None,
        kind: str | None = None,
        asset_id: str | None = None,
    ) -> tuple[StageArtifact, ...]:
        """Return the tenant's artifacts, newest version first per asset."""

    @abc.abstractmethod
    def next_version(self, tenant_id: str, workspace_id: str, asset_id: str) -> int:
        """Return the next free version for one asset's archive key."""

    def close(self) -> None:
        """A default no-op so a process-local adapter need not implement it."""
