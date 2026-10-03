"""Application use cases for the Engagement bounded context.

SPEC.md section 6 places use cases between the entry points and the domain: an
API or worker calls a use case, the use case composes domain services, and it
depends on domain types and ports rather than on web, ORM, queue or vendor code.
"""

from __future__ import annotations

from redops.contexts.engagement.application.commands import (
    RecordStageEightGateCommand,
    RecordStageFiveGateCommand,
    RecordStageFourGateCommand,
    RecordStageOneGateCommand,
    RecordStageSevenGateCommand,
    RecordStageSixGateCommand,
    RecordStageThreeGateCommand,
    RecordStageTwoGateCommand,
    RecordStageZeroGateCommand,
)
from redops.contexts.engagement.domain.assemblies import (
    StageEightGateAssembler,
    StageEightGateRecorder,
    StageFiveGateAssembler,
    StageFiveGateRecorder,
    StageFourGateAssembler,
    StageFourGateRecorder,
    StageOneGateAssembler,
    StageOneGateRecorder,
    StageSevenGateAssembler,
    StageSevenGateRecorder,
    StageSixGateAssembler,
    StageSixGateRecorder,
    StageThreeGateAssembler,
    StageThreeGateRecorder,
    StageTwoGateAssembler,
    StageTwoGateRecorder,
    StageZeroGateAssembler,
    StageZeroGateRecorder,
)
from redops.contexts.engagement.domain.errors import (
    StageRunNotCompletableError,
    StageRunNotStageEightError,
    StageRunNotStageFiveError,
    StageRunNotStageFourError,
    StageRunNotStageOneError,
    StageRunNotStageSevenError,
    StageRunNotStageSixError,
    StageRunNotStageThreeError,
    StageRunNotStageTwoError,
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
STAGE_TWO = 2
STAGE_THREE = 3
STAGE_FOUR = 4
STAGE_FIVE = 5
STAGE_SIX = 6
STAGE_SEVEN = 7
STAGE_EIGHT = 8


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


class RecordStageTwoGateHandler:
    """Assemble, record and close the stage 2 "Currency Locked" gate.

    SPEC.md section 4: a stage is complete only when its required assets exist,
    pass a defined checkpoint, and receive approval for downstream use, and a
    failed or expired prerequisite blocks dependent authorization until resolved.
    The Engagement domain already owns both halves -- ``StageTwoGateAssembler``
    validates the real ``CurrencyPackage`` against the workspace tenant and binds
    the approver, and ``StageTwoGateRecorder`` issues the exact-version approvals
    and writes the durable ``GateDecision`` -- but they are separate services a
    caller must remember to chain. This use case chains them so the canonical
    assembly cannot be bypassed by handing a hand-built gate to the recorder, and
    it closes the stage 2 ``StageRun`` from the durable decision in the same
    operation (SPEC.md sections 4 and 6).

    The stage run is validated before the decision is written, because completing
    a run whose state forbids COMPLETE would otherwise leave the ledger with a
    passing decision for a stage that never closed. Stage 2 depends on stage 1, so
    the handler is given a ``GateLedger`` that must already hold a passing stage 1
    decision; governance refuses the stage 2 decision otherwise. The use case
    mutates only the gate, the stage run and the ledger; it never invents a
    concrete human identity.
    """

    def __init__(
        self,
        *,
        assembler: StageTwoGateAssembler | None = None,
        recorder: StageTwoGateRecorder | None = None,
    ) -> None:
        self._assembler = assembler or StageTwoGateAssembler()
        self._recorder = recorder or StageTwoGateRecorder()

    def handle(
        self,
        command: RecordStageTwoGateCommand,
        *,
        ledger: GateLedger,
    ) -> GateDecision:
        self._require_stage_two_run(command.stage_run, command.template)
        gate = self._assembler.assemble(
            template=command.template,
            workspace=command.workspace,
            package=command.package,
            approver=command.approver,
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
            reason=f"stage 2 {decision.checkpoint} accepted",
            on=command.on,
            correlation_id=command.correlation_id,
        )
        return decision

    @staticmethod
    def _require_stage_two_run(
        stage_run: StageRun, template: StageTemplate
    ) -> None:
        if stage_run.stage_number != STAGE_TWO:
            raise StageRunNotStageTwoError(
                f"the stage 2 closure cannot close a run for stage "
                f"{stage_run.stage_number}"
            )
        if stage_run.template_version != template.version:
            raise StageRunNotStageTwoError(
                f"the stage 2 run is pinned to template version "
                f"{stage_run.template_version!r}, not {template.version!r}"
            )
        if not StageTransitionPolicy().can_transition(
            stage_run.status, StageStatus.COMPLETE
        ):
            raise StageRunNotCompletableError(
                f"the stage 2 run is {stage_run.status.value!r} and cannot "
                "complete; only an active Working or In Review run may close"
            )


class RecordStageThreeGateHandler:
    """Assemble, record and close the stage 3 "Diagnostic Model Approved" gate.

    SPEC.md section 4: a stage is complete only when its required assets exist,
    pass a defined checkpoint, and receive approval for downstream use, and a
    failed or expired prerequisite blocks dependent authorization until resolved.
    The Engagement domain already owns both halves -- ``StageThreeGateAssembler``
    validates the real ``DiagnosticPackage`` against the workspace tenant and
    binds the approver, and ``StageThreeGateRecorder`` issues the exact-version
    approvals and writes the durable ``GateDecision`` -- but they are separate
    services a caller must remember to chain. This use case chains them so the
    canonical assembly cannot be bypassed by handing a hand-built gate to the
    recorder, and it closes the stage 3 ``StageRun`` from the durable decision in
    the same operation (SPEC.md sections 4 and 6).

    The stage run is validated before the decision is written, because completing
    a run whose state forbids COMPLETE would otherwise leave the ledger with a
    passing decision for a stage that never closed. Stage 3 depends on stage 2, so
    the handler is given a ``GateLedger`` that must already hold a passing stage 2
    decision; governance refuses the stage 3 decision otherwise. The use case
    mutates only the gate, the stage run and the ledger; it never invents a
    concrete human identity.
    """

    def __init__(
        self,
        *,
        assembler: StageThreeGateAssembler | None = None,
        recorder: StageThreeGateRecorder | None = None,
    ) -> None:
        self._assembler = assembler or StageThreeGateAssembler()
        self._recorder = recorder or StageThreeGateRecorder()

    def handle(
        self,
        command: RecordStageThreeGateCommand,
        *,
        ledger: GateLedger,
    ) -> GateDecision:
        self._require_stage_three_run(command.stage_run, command.template)
        gate = self._assembler.assemble(
            template=command.template,
            workspace=command.workspace,
            package=command.package,
            approver=command.approver,
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
            reason=f"stage 3 {decision.checkpoint} accepted",
            on=command.on,
            correlation_id=command.correlation_id,
        )
        return decision

    @staticmethod
    def _require_stage_three_run(
        stage_run: StageRun, template: StageTemplate
    ) -> None:
        if stage_run.stage_number != STAGE_THREE:
            raise StageRunNotStageThreeError(
                f"the stage 3 closure cannot close a run for stage "
                f"{stage_run.stage_number}"
            )
        if stage_run.template_version != template.version:
            raise StageRunNotStageThreeError(
                f"the stage 3 run is pinned to template version "
                f"{stage_run.template_version!r}, not {template.version!r}"
            )
        if not StageTransitionPolicy().can_transition(
            stage_run.status, StageStatus.COMPLETE
        ):
            raise StageRunNotCompletableError(
                f"the stage 3 run is {stage_run.status.value!r} and cannot "
                "complete; only an active Working or In Review run may close"
            )


class RecordStageFourGateHandler:
    """Assemble, record and close the stage 4 "IP Architecture Locked" gate.

    SPEC.md section 4: a stage is complete only when its required assets exist,
    pass a defined checkpoint, and receive approval for downstream use, and a
    failed or expired prerequisite blocks dependent authorization until resolved.
    The Engagement domain already owns both halves -- ``StageFourGateAssembler``
    validates the real ``SignaturePackage`` against the workspace tenant and binds
    the approver, and ``StageFourGateRecorder`` issues the exact-version approvals
    and writes the durable ``GateDecision`` -- but they are separate services a
    caller must remember to chain. This use case chains them so the canonical
    assembly cannot be bypassed by handing a hand-built gate to the recorder, and
    it closes the stage 4 ``StageRun`` from the durable decision in the same
    operation (SPEC.md sections 4 and 6).

    The stage run is validated before the decision is written, because completing
    a run whose state forbids COMPLETE would otherwise leave the ledger with a
    passing decision for a stage that never closed. Stage 4 depends on stage 3, so
    the handler is given a ``GateLedger`` that must already hold a passing stage 3
    decision; governance refuses the stage 4 decision otherwise. The use case
    mutates only the gate, the stage run and the ledger; it never invents a
    concrete human identity.
    """

    def __init__(
        self,
        *,
        assembler: StageFourGateAssembler | None = None,
        recorder: StageFourGateRecorder | None = None,
    ) -> None:
        self._assembler = assembler or StageFourGateAssembler()
        self._recorder = recorder or StageFourGateRecorder()

    def handle(
        self,
        command: RecordStageFourGateCommand,
        *,
        ledger: GateLedger,
    ) -> GateDecision:
        self._require_stage_four_run(command.stage_run, command.template)
        gate = self._assembler.assemble(
            template=command.template,
            workspace=command.workspace,
            package=command.package,
            approver=command.approver,
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
            reason=f"stage 4 {decision.checkpoint} accepted",
            on=command.on,
            correlation_id=command.correlation_id,
        )
        return decision

    @staticmethod
    def _require_stage_four_run(
        stage_run: StageRun, template: StageTemplate
    ) -> None:
        if stage_run.stage_number != STAGE_FOUR:
            raise StageRunNotStageFourError(
                f"the stage 4 closure cannot close a run for stage "
                f"{stage_run.stage_number}"
            )
        if stage_run.template_version != template.version:
            raise StageRunNotStageFourError(
                f"the stage 4 run is pinned to template version "
                f"{stage_run.template_version!r}, not {template.version!r}"
            )
        if not StageTransitionPolicy().can_transition(
            stage_run.status, StageStatus.COMPLETE
        ):
            raise StageRunNotCompletableError(
                f"the stage 4 run is {stage_run.status.value!r} and cannot "
                "complete; only an active Working or In Review run may close"
            )


class RecordStageFiveGateHandler:
    """Assemble, record and close the stage 5 "Offer Locked" gate.

    SPEC.md section 4: a stage is complete only when its required assets exist,
    pass a defined checkpoint, and receive approval for downstream use, and a
    failed or expired prerequisite blocks dependent authorization until resolved.
    The Engagement domain already owns both halves -- ``StageFiveGateAssembler``
    validates the real ``OfferPackage`` against the workspace tenant and binds the
    approver, and ``StageFiveGateRecorder`` issues the exact-version approvals and
    writes the durable ``GateDecision`` -- but they are separate services a caller
    must remember to chain. This use case chains them so the canonical assembly
    cannot be bypassed by handing a hand-built gate to the recorder, and it closes
    the stage 5 ``StageRun`` from the durable decision in the same operation
    (SPEC.md sections 4 and 6).

    The stage run is validated before the decision is written, because completing
    a run whose state forbids COMPLETE would otherwise leave the ledger with a
    passing decision for a stage that never closed. Stage 5 depends on stage 4, so
    the handler is given a ``GateLedger`` that must already hold a passing stage 4
    decision; governance refuses the stage 5 decision otherwise. The use case
    mutates only the gate, the stage run and the ledger; it never invents a
    concrete human identity.
    """

    def __init__(
        self,
        *,
        assembler: StageFiveGateAssembler | None = None,
        recorder: StageFiveGateRecorder | None = None,
    ) -> None:
        self._assembler = assembler or StageFiveGateAssembler()
        self._recorder = recorder or StageFiveGateRecorder()

    def handle(
        self,
        command: RecordStageFiveGateCommand,
        *,
        ledger: GateLedger,
    ) -> GateDecision:
        self._require_stage_five_run(command.stage_run, command.template)
        gate = self._assembler.assemble(
            template=command.template,
            workspace=command.workspace,
            package=command.package,
            approver=command.approver,
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
            reason=f"stage 5 {decision.checkpoint} accepted",
            on=command.on,
            correlation_id=command.correlation_id,
        )
        return decision

    @staticmethod
    def _require_stage_five_run(
        stage_run: StageRun, template: StageTemplate
    ) -> None:
        if stage_run.stage_number != STAGE_FIVE:
            raise StageRunNotStageFiveError(
                f"the stage 5 closure cannot close a run for stage "
                f"{stage_run.stage_number}"
            )
        if stage_run.template_version != template.version:
            raise StageRunNotStageFiveError(
                f"the stage 5 run is pinned to template version "
                f"{stage_run.template_version!r}, not {template.version!r}"
            )
        if not StageTransitionPolicy().can_transition(
            stage_run.status, StageStatus.COMPLETE
        ):
            raise StageRunNotCompletableError(
                f"the stage 5 run is {stage_run.status.value!r} and cannot "
                "complete; only an active Working or In Review run may close"
            )


class RecordStageSixGateHandler:
    """Assemble, record and close the stage 6 "Campaign Message Approved" gate.

    SPEC.md section 4: a stage is complete only when its required assets exist,
    pass a defined checkpoint, and receive approval for downstream use, and a
    failed or expired prerequisite blocks dependent authorization until resolved.
    The Engagement domain already owns both halves -- ``StageSixGateAssembler``
    validates the reviewed ``CampaignMessagePackage`` against the workspace tenant
    and the message's own approval, and binds the approver, and
    ``StageSixGateRecorder`` issues the exact-version approvals and writes the
    durable ``GateDecision`` -- but they are separate services a caller must
    remember to chain. This use case chains them so the canonical assembly cannot
    be bypassed by handing a hand-built gate to the recorder, and it closes the
    stage 6 ``StageRun`` from the durable decision in the same operation (SPEC.md
    sections 4 and 6).

    The stage run is validated before the decision is written, because completing
    a run whose state forbids COMPLETE would otherwise leave the ledger with a
    passing decision for a stage that never closed. Stage 6 depends on stage 5, so
    the handler is given a ``GateLedger`` that must already hold a passing stage 5
    decision; governance refuses the stage 6 decision otherwise. The use case
    mutates only the gate, the stage run and the ledger; it never invents a
    concrete human identity.
    """

    def __init__(
        self,
        *,
        assembler: StageSixGateAssembler | None = None,
        recorder: StageSixGateRecorder | None = None,
    ) -> None:
        self._assembler = assembler or StageSixGateAssembler()
        self._recorder = recorder or StageSixGateRecorder()

    def handle(
        self,
        command: RecordStageSixGateCommand,
        *,
        ledger: GateLedger,
    ) -> GateDecision:
        self._require_stage_six_run(command.stage_run, command.template)
        gate = self._assembler.assemble(
            template=command.template,
            workspace=command.workspace,
            package=command.package,
            approver=command.approver,
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
            reason=f"stage 6 {decision.checkpoint} accepted",
            on=command.on,
            correlation_id=command.correlation_id,
        )
        return decision

    @staticmethod
    def _require_stage_six_run(
        stage_run: StageRun, template: StageTemplate
    ) -> None:
        if stage_run.stage_number != STAGE_SIX:
            raise StageRunNotStageSixError(
                f"the stage 6 closure cannot close a run for stage "
                f"{stage_run.stage_number}"
            )
        if stage_run.template_version != template.version:
            raise StageRunNotStageSixError(
                f"the stage 6 run is pinned to template version "
                f"{stage_run.template_version!r}, not {template.version!r}"
            )
        if not StageTransitionPolicy().can_transition(
            stage_run.status, StageStatus.COMPLETE
        ):
            raise StageRunNotCompletableError(
                f"the stage 6 run is {stage_run.status.value!r} and cannot "
                "complete; only an active Working or In Review run may close"
            )


class RecordStageSevenGateHandler:
    """Assemble, record and close the stage 7 "Authority Amplifier Approved" gate.

    SPEC.md section 4: a stage is complete only when its required assets exist,
    pass a defined checkpoint, and receive approval for downstream use, and a
    failed or expired prerequisite blocks dependent authorization until resolved.
    The Engagement domain already owns both halves -- ``StageSevenGateAssembler``
    validates the reviewed ``AuthorityAmplifierPackage`` against the workspace
    tenant and the amplifier's final creative acceptance, and binds the approver,
    and ``StageSevenGateRecorder`` issues the exact-version approvals and writes
    the durable ``GateDecision`` -- but they are separate services a caller must
    remember to chain. This use case chains them so the canonical assembly cannot
    be bypassed by handing a hand-built gate to the recorder, and it closes the
    stage 7 ``StageRun`` from the durable decision in the same operation (SPEC.md
    sections 4 and 6).

    The stage run is validated before the decision is written, because completing
    a run whose state forbids COMPLETE would otherwise leave the ledger with a
    passing decision for a stage that never closed. Stage 7 depends on stage 6, so
    the handler is given a ``GateLedger`` that must already hold a passing stage 6
    decision; governance refuses the stage 7 decision otherwise. The use case
    mutates only the gate, the stage run and the ledger; it never invents a
    concrete human identity.
    """

    def __init__(
        self,
        *,
        assembler: StageSevenGateAssembler | None = None,
        recorder: StageSevenGateRecorder | None = None,
    ) -> None:
        self._assembler = assembler or StageSevenGateAssembler()
        self._recorder = recorder or StageSevenGateRecorder()

    def handle(
        self,
        command: RecordStageSevenGateCommand,
        *,
        ledger: GateLedger,
    ) -> GateDecision:
        self._require_stage_seven_run(command.stage_run, command.template)
        gate = self._assembler.assemble(
            template=command.template,
            workspace=command.workspace,
            package=command.package,
            approver=command.approver,
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
            reason=f"stage 7 {decision.checkpoint} accepted",
            on=command.on,
            correlation_id=command.correlation_id,
        )
        return decision

    @staticmethod
    def _require_stage_seven_run(
        stage_run: StageRun, template: StageTemplate
    ) -> None:
        if stage_run.stage_number != STAGE_SEVEN:
            raise StageRunNotStageSevenError(
                f"the stage 7 closure cannot close a run for stage "
                f"{stage_run.stage_number}"
            )
        if stage_run.template_version != template.version:
            raise StageRunNotStageSevenError(
                f"the stage 7 run is pinned to template version "
                f"{stage_run.template_version!r}, not {template.version!r}"
            )
        if not StageTransitionPolicy().can_transition(
            stage_run.status, StageStatus.COMPLETE
        ):
            raise StageRunNotCompletableError(
                f"the stage 7 run is {stage_run.status.value!r} and cannot "
                "complete; only an active Working or In Review run may close"
            )


class RecordStageEightGateHandler:
    """Assemble, record and close the stage 8 "Funnel Complete" gate.

    SPEC.md section 4: a stage is complete only when its required assets exist,
    pass a defined checkpoint, and receive approval for downstream use, and a
    failed or expired prerequisite blocks dependent authorization until resolved.
    The Engagement domain already owns both halves -- ``StageEightGateAssembler``
    validates the reviewed ``FunnelIntegrationPackage`` against the workspace
    tenant and the funnel's completed prospect path, and binds the approver, and
    ``StageEightGateRecorder`` issues the exact-version approvals and writes the
    durable ``GateDecision`` -- but they are separate services a caller must
    remember to chain. This use case chains them so the canonical assembly cannot
    be bypassed by handing a hand-built gate to the recorder, and it closes the
    stage 8 ``StageRun`` from the durable decision in the same operation (SPEC.md
    sections 4 and 6).

    The stage run is validated before the decision is written, because completing
    a run whose state forbids COMPLETE would otherwise leave the ledger with a
    passing decision for a stage that never closed. Stage 8 depends on stage 7, so
    the handler is given a ``GateLedger`` that must already hold a passing stage 7
    decision; governance refuses the stage 8 decision otherwise. The use case
    mutates only the gate, the stage run and the ledger; it never invents a
    concrete human identity.
    """

    def __init__(
        self,
        *,
        assembler: StageEightGateAssembler | None = None,
        recorder: StageEightGateRecorder | None = None,
    ) -> None:
        self._assembler = assembler or StageEightGateAssembler()
        self._recorder = recorder or StageEightGateRecorder()

    def handle(
        self,
        command: RecordStageEightGateCommand,
        *,
        ledger: GateLedger,
    ) -> GateDecision:
        self._require_stage_eight_run(command.stage_run, command.template)
        gate = self._assembler.assemble(
            template=command.template,
            workspace=command.workspace,
            package=command.package,
            approver=command.approver,
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
            reason=f"stage 8 {decision.checkpoint} accepted",
            on=command.on,
            correlation_id=command.correlation_id,
        )
        return decision

    @staticmethod
    def _require_stage_eight_run(
        stage_run: StageRun, template: StageTemplate
    ) -> None:
        if stage_run.stage_number != STAGE_EIGHT:
            raise StageRunNotStageEightError(
                f"the stage 8 closure cannot close a run for stage "
                f"{stage_run.stage_number}"
            )
        if stage_run.template_version != template.version:
            raise StageRunNotStageEightError(
                f"the stage 8 run is pinned to template version "
                f"{stage_run.template_version!r}, not {template.version!r}"
            )
        if not StageTransitionPolicy().can_transition(
            stage_run.status, StageStatus.COMPLETE
        ):
            raise StageRunNotCompletableError(
                f"the stage 8 run is {stage_run.status.value!r} and cannot "
                "complete; only an active Working or In Review run may close"
            )
