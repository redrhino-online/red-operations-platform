"""Gate integrity policy for the Governance bounded context (pure domain).

Decides whether a stage gate is eligible for approval given the current evidence
and the states of its prerequisite gates. This encodes SPEC.md section 4:
stage completion requires gate acceptance, not activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from redops.contexts.governance.domain.entities import StageGate
from redops.contexts.governance.domain.value_objects import GateState


@dataclass(frozen=True)
class GateEvaluation:
    approvable: bool
    reasons: tuple[str, ...] = ()

    @property
    def blocked(self) -> bool:
        return not self.approvable


class GateIntegrityPolicy:
    def evaluate(
        self,
        gate: StageGate,
        dependency_states: Mapping[int, GateState],
    ) -> GateEvaluation:
        reasons: list[str] = []

        if gate.state is GateState.SUPERSEDED:
            reasons.append("gate is superseded")

        missing = gate.missing_assets()
        if missing:
            names = ", ".join(sorted(str(asset) for asset in missing))
            reasons.append(f"required asset versions not approved: {names}")

        unapproved = sorted(
            stage
            for stage in gate.dependencies
            if dependency_states.get(stage) is not GateState.APPROVED
        )
        if unapproved:
            names = ", ".join(str(stage) for stage in unapproved)
            reasons.append(f"prerequisite stage gates not approved: {names}")

        if not gate.approver or not gate.approver.strip():
            reasons.append("a designated approver is required")

        if (
            gate.approver
            and gate.proposed_by
            and gate.approver == gate.proposed_by
        ):
            reasons.append("approver cannot approve own proposal")

        return GateEvaluation(approvable=not reasons, reasons=tuple(reasons))
