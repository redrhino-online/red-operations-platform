"""In-memory gate ledger repository: the reference adapter for the port.

Implements ``GateLedgerRepository`` (SPEC.md section 6: infrastructure adapters
implement ports) with a process-local, append-only store. It is the reference
adapter that satisfies the port contract and the double used by application and
API tests before a PostgreSQL-backed store exists.

ADR 0003 requires a PostgreSQL adapter. That adapter is a follow-up: neither the
domain-only interpreter (Python 3.10, no third-party packages) nor the vendored
OpenExecutive environment (Python 3.12, FastAPI) ships a PostgreSQL driver, so a
SQL adapter could not be behaviorally verified this cycle. This adapter is not a
substitute for it; it is the seam the PostgreSQL adapter will implement, so the
application no longer depends on how the ledger is stored.
"""

from __future__ import annotations

from redops.contexts.governance.application.ports import GateLedgerRepository
from redops.contexts.governance.domain.entities import GateDecision, GateLedger
from redops.contexts.governance.domain.value_objects import StageTemplate


class InMemoryGateLedgerRepository(GateLedgerRepository):
    """Append-only, process-local gate decision store keyed by template version."""

    def __init__(self) -> None:
        self._decisions: list[GateDecision] = []

    def load(self, template: StageTemplate) -> GateLedger:
        ledger = GateLedger(template)
        for decision in self._decisions:
            if decision.template_version != template.version:
                continue
            ledger.record(decision)
        return ledger

    def append(self, decision: GateDecision) -> None:
        self._decisions.append(decision)
