"""Gate integrity policy for the Governance bounded context (pure domain).

Decides whether a stage gate is eligible for approval given the current evidence
and the states of its prerequisite gates. This encodes SPEC.md section 4:
stage completion requires gate acceptance, not activity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from redops.contexts.governance.domain.entities import StageGate
from redops.contexts.governance.domain.errors import IllegalStageTransitionError
from redops.contexts.governance.domain.value_objects import (
    GateState,
    StageStatus,
    StageTemplate,
)


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
        template: StageTemplate | None = None,
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

        if template is not None:
            reasons.extend(self._template_reasons(gate, template))

        return GateEvaluation(approvable=not reasons, reasons=tuple(reasons))

    def _template_reasons(
        self, gate: StageGate, template: StageTemplate
    ) -> list[str]:
        """Reject a gate that diverges from the canonical pipeline template.

        A self-declared gate must not omit a canonical prerequisite or
        under-declare the required asset package, and it must pin the same
        template version it is evaluated against (SPEC.md section 4).
        """
        reasons: list[str] = []
        if gate.template_version != template.version:
            reasons.append(
                f"gate template version {gate.template_version!r} does not match "
                f"template version {template.version!r}"
            )

        definition = template.definition_for(gate.stage_number)
        if definition is None:
            reasons.append(
                f"stage {gate.stage_number} is not defined in template "
                f"{template.version!r}"
            )
            return reasons

        omitted = sorted(definition.dependencies - gate.dependencies)
        if omitted:
            names = ", ".join(str(stage) for stage in omitted)
            reasons.append(f"gate omits prerequisite stages: {names}")

        declared_kinds = {asset.asset_id for asset in gate.required_assets}
        unstated = sorted(definition.required_asset_kinds - declared_kinds)
        if unstated:
            names = ", ".join(unstated)
            reasons.append(f"gate omits required asset kinds: {names}")

        return reasons


class StageTransitionPolicy:
    """Legal StageRun status transitions (SPEC.md sections 3 and 4).

    Rejects illegal transitions instead of silently coercing state. Completion
    is reachable from an active stage only; a superseded or not-started stage
    cannot jump to complete.
    """

    ALLOWED: Mapping[StageStatus, frozenset[StageStatus]] = {
        StageStatus.NOT_STARTED: frozenset({StageStatus.WORKING, StageStatus.BLOCKED}),
        StageStatus.WORKING: frozenset(
            {
                StageStatus.IN_REVIEW,
                StageStatus.CHANGES_REQUIRED,
                StageStatus.COMPLETE,
                StageStatus.BLOCKED,
                StageStatus.WAIVED,
            }
        ),
        StageStatus.IN_REVIEW: frozenset(
            {
                StageStatus.WORKING,
                StageStatus.CHANGES_REQUIRED,
                StageStatus.COMPLETE,
                StageStatus.BLOCKED,
            }
        ),
        StageStatus.CHANGES_REQUIRED: frozenset({StageStatus.WORKING, StageStatus.BLOCKED}),
        StageStatus.BLOCKED: frozenset({StageStatus.WORKING}),
        StageStatus.COMPLETE: frozenset({StageStatus.SUPERSEDED}),
        StageStatus.WAIVED: frozenset({StageStatus.SUPERSEDED}),
        StageStatus.SUPERSEDED: frozenset(),
    }

    def can_transition(self, current: StageStatus, target: StageStatus) -> bool:
        return target in self.ALLOWED.get(current, frozenset())

    def require(self, current: StageStatus, target: StageStatus) -> None:
        if not self.can_transition(current, target):
            raise IllegalStageTransitionError(
                f"cannot transition stage from {current.value!r} to {target.value!r}"
            )
