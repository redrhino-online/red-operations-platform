"""Application use cases for the Engagement bounded context.

SPEC.md section 6 places use cases between the entry points and the domain: an
API or worker calls a use case, the use case composes domain services, and it
depends on domain types and ports rather than on web, ORM, queue or vendor code.
"""

from __future__ import annotations

from redops.contexts.engagement.application.commands import (
    RecordStageZeroGateCommand,
)
from redops.contexts.engagement.domain.assemblies import (
    StageZeroGateAssembler,
    StageZeroGateRecorder,
)
from redops.contexts.governance.domain.entities import GateDecision, GateLedger


class RecordStageZeroGateHandler:
    """Assemble and record the stage 0 "Production Ready" gate in one operation.

    SPEC.md section 4: a stage is complete only when its required assets exist,
    pass a defined checkpoint, and receive approval for downstream use. The
    Engagement domain already owns both halves -- ``StageZeroGateAssembler``
    validates the real ``IntakePackage`` against ``ProductionReadyPolicy`` and
    ``GateApproverAuthorityPolicy``, and ``StageZeroGateRecorder`` issues the
    exact-version approvals and writes the durable ``GateDecision``. This use
    case chains them so the canonical assembly cannot be bypassed by handing a
    hand-built gate to the recorder: the application boundary always builds the
    gate from the package (SPEC.md sections 4 and 6). It mutates only the ledger
    it records into, and never invents a concrete human identity.
    """

    def __init__(
        self,
        *,
        assembler: StageZeroGateAssembler | None = None,
        recorder: StageZeroGateRecorder | None = None,
    ) -> None:
        self._assembler = assembler or StageZeroGateAssembler()
        self._recorder = recorder or StageZeroGateRecorder()

    def handle(
        self,
        command: RecordStageZeroGateCommand,
        *,
        ledger: GateLedger,
    ) -> GateDecision:
        gate = self._assembler.assemble(
            template=command.template,
            workspace=command.workspace,
            package=command.package,
            approver=command.approver,
            claims=command.claims,
            proposed_by=command.proposed_by,
        )
        return self._recorder.record(
            gate=gate,
            workspace=command.workspace,
            ledger=ledger,
            scope=command.scope,
            checkpoint_evidence=command.checkpoint_evidence,
            rationale=command.rationale,
            assigned_owner=command.assigned_owner,
            due_on=command.due_on,
            on=command.on,
            next_action=command.next_action,
        )
