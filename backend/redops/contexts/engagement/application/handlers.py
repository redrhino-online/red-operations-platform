"""Application use cases for the Engagement bounded context.

SPEC.md section 6 places use cases between the entry points and the domain: an
API or worker calls a use case, the use case composes domain services, and it
depends on domain types and ports rather than on web, ORM, queue or vendor code.
"""

from __future__ import annotations

from redops.contexts.engagement.application.commands import (
    RecordStageOneGateCommand,
    RecordStageZeroGateCommand,
)
from redops.contexts.engagement.domain.assemblies import (
    StageOneGateAssembler,
    StageOneGateRecorder,
    StageZeroGateAssembler,
    StageZeroGateRecorder,
)
from redops.contexts.engagement.domain.errors import (
    StageRunNotCompletableError,
    StageRunNotStageOneError,
    StageRunNotStageZeroError,
)
from redops.contexts.governance.domain.entities import (
    GateDecision,
    GateLedger,
    StageRun,
)
from redops.contexts.governance.domain.policies import StageTransitionPolicy
from redops.contexts.governance.domain.value_objects import (
    StageStatus,
    StageTemplate,
)

STAGE_ZERO = 0
STAGE_ONE = 1


class RecordStageZeroGateHandler:
    """Assemble, record and close the stage 0 "Production Ready" gate.

    SPEC.md section 4: a stage is complete only when its required assets exist,
    pass a defined checkpoint, and receive approval for downstream use. The
    Engagement domain already owns both halves -- ``StageZeroGateAssembler``
    validates the real ``IntakePackage`` against ``ProductionReadyPolicy`` and
    ``GateApproverAuthorityPolicy``, and ``StageZeroGateRecorder`` issues the
    exact-version approvals and writes the durable ``GateDecision``. This use
    case chains them so the canonical assembly cannot be bypassed by handing a
    hand-built gate to the recorder, and it closes the stage 0 ``StageRun`` from
    the durable decision in the same operation (SPEC.md sections 4 and 6). That
    keeps approved-gate progress and stage status from drifting: a passing gate
    cannot be recorded while the stage stays incomplete.

    The stage run is validated before the decision is written, because completing
    a run whose state forbids COMPLETE would otherwise leave the ledger with a
    passing decision for a stage that never closed. The use case mutates only the
    gate, the stage run and the ledger; it never invents a concrete human
    identity.
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
        self._require_stage_zero_run(command.stage_run, command.template)
        gate = self._assembler.assemble(
            template=command.template,
            workspace=command.workspace,
            package=command.package,
            approver=command.approver,
            claims=command.claims,
            proposed_by=command.proposed_by,
        )
        decision = self._recorder.record(
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
        command.stage_run.complete(
            decision=decision,
            ledger=ledger,
            actor=command.approver,
            reason=f"stage 0 {decision.checkpoint} accepted",
            on=command.on,
            correlation_id=command.correlation_id,
        )
        return decision

    @staticmethod
    def _require_stage_zero_run(
        stage_run: StageRun, template: StageTemplate
    ) -> None:
        if stage_run.stage_number != STAGE_ZERO:
            raise StageRunNotStageZeroError(
                f"the stage 0 closure cannot close a run for stage "
                f"{stage_run.stage_number}"
            )
        if stage_run.template_version != template.version:
            raise StageRunNotStageZeroError(
                f"the stage 0 run is pinned to template version "
                f"{stage_run.template_version!r}, not {template.version!r}"
            )
        if not StageTransitionPolicy().can_transition(
            stage_run.status, StageStatus.COMPLETE
        ):
            raise StageRunNotCompletableError(
                f"the stage 0 run is {stage_run.status.value!r} and cannot "
                "complete; only an active Working or In Review run may close"
            )


class RecordStageOneGateHandler:
    """Assemble, record and close the stage 1 "Avatar Locked" gate.

    SPEC.md section 4: a stage is complete only when its required assets exist,
    pass a defined checkpoint, and receive approval for downstream use, and a
    failed or expired prerequisite blocks dependent authorization until resolved.
    The Engagement domain already owns both halves -- ``StageOneGateAssembler``
    validates the real ``DiagnosisPackage`` against ``AvatarLockedPolicy`` and
    ``DiagnosisEvidencePolicy`` and binds the approver, and ``StageOneGateRecorder``
    issues the exact-version approvals and writes the durable ``GateDecision`` --
    but they are separate services a caller must remember to chain. This use case
    chains them so the canonical assembly cannot be bypassed by handing a
    hand-built gate to the recorder, and it closes the stage 1 ``StageRun`` from
    the durable decision in the same operation (SPEC.md sections 4 and 6).

    The stage run is validated before the decision is written, because completing
    a run whose state forbids COMPLETE would otherwise leave the ledger with a
    passing decision for a stage that never closed. Stage 1 depends on stage 0, so
    the handler is given a ``GateLedger`` that must already hold a passing stage 0
    decision; governance refuses the stage 1 decision otherwise. The use case
    mutates only the gate, the stage run and the ledger; it never invents a
    concrete human identity.
    """

    def __init__(
        self,
        *,
        assembler: StageOneGateAssembler | None = None,
        recorder: StageOneGateRecorder | None = None,
    ) -> None:
        self._assembler = assembler or StageOneGateAssembler()
        self._recorder = recorder or StageOneGateRecorder()

    def handle(
        self,
        command: RecordStageOneGateCommand,
        *,
        ledger: GateLedger,
    ) -> GateDecision:
        self._require_stage_one_run(command.stage_run, command.template)
        gate = self._assembler.assemble(
            template=command.template,
            workspace=command.workspace,
            package=command.package,
            approver=command.approver,
            claims=command.claims,
            proposed_by=command.proposed_by,
        )
        decision = self._recorder.record(
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
        command.stage_run.complete(
            decision=decision,
            ledger=ledger,
            actor=command.approver,
            reason=f"stage 1 {decision.checkpoint} accepted",
            on=command.on,
            correlation_id=command.correlation_id,
        )
        return decision

    @staticmethod
    def _require_stage_one_run(
        stage_run: StageRun, template: StageTemplate
    ) -> None:
        if stage_run.stage_number != STAGE_ONE:
            raise StageRunNotStageOneError(
                f"the stage 1 closure cannot close a run for stage "
                f"{stage_run.stage_number}"
            )
        if stage_run.template_version != template.version:
            raise StageRunNotStageOneError(
                f"the stage 1 run is pinned to template version "
                f"{stage_run.template_version!r}, not {template.version!r}"
            )
        if not StageTransitionPolicy().can_transition(
            stage_run.status, StageStatus.COMPLETE
        ):
            raise StageRunNotCompletableError(
                f"the stage 1 run is {stage_run.status.value!r} and cannot "
                "complete; only an active Working or In Review run may close"
            )
