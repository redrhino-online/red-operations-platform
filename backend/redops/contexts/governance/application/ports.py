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

from redops.contexts.governance.domain.entities import GateDecision, GateLedger
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
