"""Application commands for the Engagement bounded context.

SPEC.md section 6: application use cases depend on domain types and ports; entry
points call use cases rather than reaching into persistence. A command is the
typed, immutable request that carries every input a use case needs, so an entry
point cannot smuggle a hand-built governance gate past the stage 0 checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.value_objects import IntakePackage
from redops.contexts.governance.domain.entities import StageRun
from redops.contexts.governance.domain.value_objects import StageTemplate
from redops.contexts.knowledge.domain.entities import Claim


@dataclass(frozen=True)
class RecordStageZeroGateCommand:
    """Request to assemble and record the stage 0 "Production Ready" gate.

    The command carries the real ``IntakePackage``, the workspace authority
    registry, the supporting ``Claim`` set and the exact decision metadata; it
    deliberately carries no ``StageGate``. The use case builds the canonical gate
    itself from the package, so a caller cannot substitute a hand-built gate and
    skip the owner-authority and sourced-evidence checks (SPEC.md sections 3, 4
    and 6).

    It also carries the stage 0 ``StageRun`` to close. Recording a passing gate
    and completing the stage are one application operation, so the durable
    ``GateDecision`` and the stage status cannot drift apart, and SPEC.md section
    4's "stage completion requires gate acceptance, not merely activity" holds at
    the application boundary.
    """

    template: StageTemplate
    workspace: ClientWorkspace
    package: IntakePackage
    claims: tuple[Claim, ...]
    stage_run: StageRun
    approver: str
    scope: str
    checkpoint_evidence: str
    rationale: str
    assigned_owner: str
    due_on: date
    on: date
    correlation_id: str
    proposed_by: str | None = None
    next_action: str = ""
