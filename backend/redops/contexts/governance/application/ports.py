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
    """Durable, append-only store of stage gate decisions per template version.

    The port is keyed by template version because a passing gate pins the exact
    template it was decided against (SPEC.md sections 3 and 4): a decision
    recorded for one template version must never be replayed into another.
    """

    @abc.abstractmethod
    def load(self, template: StageTemplate) -> GateLedger:
        """Reconstruct the ledger for ``template`` from its stored decisions.

        Stored decisions are replayed through ``GateLedger.record``, which
        re-applies the canonical template, exact-package, checkpoint,
        prerequisite and dependency rules. A decision that storage cannot
        legally hold therefore cannot be read back as approved (SPEC.md section
        4); a corrupt or out-of-order history fails loudly rather than
        laundering an unapproved dependency into an approved gate.
        """

    @abc.abstractmethod
    def append(self, decision: GateDecision) -> None:
        """Persist one immutable decision to its stage's history.

        History is append-only: a superseding decision is stored alongside the
        earlier one, never edits it (SPEC.md section 3). The store does not
        itself decide whether a decision is valid; ``load`` replays through the
        domain ledger so integrity is enforced on the canonical aggregate.
        """
