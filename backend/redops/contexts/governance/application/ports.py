"""Application ports for the Governance bounded context.

SPEC.md section 6 (onion dependency rule): application use cases depend on
domain types and ports, and infrastructure adapters implement the ports. ADR
0003 makes RED's persistence PostgreSQL behind repository ports, so the gate
ledger is reached through a port rather than constructed inline by a route or
worker.

SPEC.md section 4 requires the gate record to be durable and time-aware: "a
passing gate pins the exact evidence and intended downstream use", history is
append-only (section 3), and "a failed or expired prerequisite blocks dependent
authorization until resolved". The ``GateLedgerRepository`` port is the seam that
lets the application record a ``GateDecision`` through the domain's append-only
``GateLedger`` and later reconstruct the same ledger from storage, so
approved-gate progress and dependency state survive a process restart and are
shared across the API and worker processes. It is deliberately narrow: load a
ledger for one template version, append one immutable decision.
"""

from __future__ import annotations

import abc

from redops.contexts.governance.domain.entities import (
    GateDecision,
    GateLedger,
    StageRun,
)
from redops.contexts.governance.domain.value_objects import StageTemplate


class GateLedgerRepository(abc.ABC):
    """Durable, append-only store of stage gate decisions per client and template.

    The port is keyed by tenant and template version because a passing gate pins
    the exact template it was decided against (SPEC.md sections 3 and 4) and
    every client resource belongs to exactly one client (SPEC.md section 3): a
    decision recorded for one template version or one client must never be
    replayed into another client's ledger.
    """

    @abc.abstractmethod
    def load(self, template: StageTemplate, tenant_id: str) -> GateLedger:
        """Reconstruct the ledger for ``tenant_id`` and ``template``.

        The returned ledger is tenant scoped: it carries ``tenant_id`` and
        replays only that client's stored decisions. Stored decisions are
        replayed through ``GateLedger.record``, which re-applies the canonical
        template, exact-package, checkpoint, prerequisite, dependency and
        tenant rules. A decision that storage cannot legally hold therefore
        cannot be read back as approved (SPEC.md section 4); a corrupt or
        out-of-order history fails loudly rather than laundering an unapproved
        dependency, or another client's decision, into an approved gate.
        """

    @abc.abstractmethod
    def append(self, decision: GateDecision) -> None:
        """Persist one immutable, tenant-carrying decision to its history.

        History is append-only: a superseding decision is stored alongside the
        earlier one, never edits it (SPEC.md section 3). A decision that carries
        no tenant cannot be persisted, because it would be a client resource
        with no client to scope it to (SPEC.md sections 3 and 9). The store does
        not itself decide whether a decision is valid; ``load`` replays through
        the domain ledger so integrity is enforced on the canonical aggregate.
        """

    def close(self) -> None:
        """Release any resource the adapter owns for the caller's request.

        A durable adapter holds a connection; a process-local adapter holds
        nothing. The default is a no-op, so the lifecycle concern stays with the
        adapter that needs it rather than leaking into the port's data contract
        (SPEC.md section 6).
        """

        return None


class StageRunRepository(abc.ABC):
    """Durable store of production ``StageRun`` progress per client and stage.

    SPEC.md section 3 makes ``StageRun`` a core aggregate whose fields are the
    engagement, stage number, template version, assigned owner, status and the
    entered and exited timestamps, and section 4 requires a stage to complete
    only through an accepted gate rather than activity, recording every
    transition actor, reason, timestamp, old and new status, and correlation ID.
    That progress cannot be reconstructed from the append-only ``GateDecision``
    ledger alone -- a Working stage with no decision, its assigned owner and the
    instant it was entered are not gate decisions -- so the stage run is stored
    behind its own tenant-scoped port and survives a process restart, shared
    across the API and worker processes (SPEC.md section 6).

    The port is deliberately narrow: load the run for one client's engagement
    and stage, or save one. It is keyed by tenant because every client resource
    belongs to exactly one client and a run from one client's workspace must
    never be read back into another's (SPEC.md sections 3 and 9).
    """

    @abc.abstractmethod
    def load(
        self,
        template_version: str,
        engagement: str,
        stage_number: int,
        tenant_id: str,
    ) -> StageRun | None:
        """Return the client's run for one engagement stage, or ``None``.

        A missing run is a stage that has not been started, not an error. The
        returned run carries the assigned owner, status, entered/exited
        timestamps and restored transition log, so the production view reports
        verified progress rather than a synthesised placeholder.
        """

    @abc.abstractmethod
    def save(self, run: StageRun) -> None:
        """Persist one run's current progress for its client.

        A run that carries no tenant cannot be stored, because it would be a
        client resource with no client to scope it to (SPEC.md sections 3 and
        9). Saving upserts the run identified by (tenant, engagement, template
        version, stage number); the status and timestamps are progress, so a
        later save is the stage moving forward, not a new history -- the
        append-only record of each move is the run's own transition log.
        """

    def close(self) -> None:
        """Release any resource the adapter owns for the caller's request."""

        return None
