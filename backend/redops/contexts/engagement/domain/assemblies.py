"""Stage 0 gate assembly for the Engagement bounded context (pure domain).

SPEC.md section 4 makes the stage 0 "Intake" gate the first checkpoint of the
stage 0-10 pipeline: the stage is complete only when its required assets exist,
pass the "Production Ready" checkpoint, and receive approval for downstream use,
and a passing gate pins the exact asset versions and intended use. The
``IntakePackage`` (Engagement value object) holds the twelve real stage 0 assets,
the governance ``StageGate.from_assets`` pins them as exact ``AssetVersionRef``
evidence, ``ProductionReadyPolicy`` evaluates the checkpoint, and
``GateApproverAuthorityPolicy`` binds the gate's designated approver to the
workspace authority registry.

This assembler composes those pieces so a caller cannot hand an under-declared
or unvalidated stage 0 gate to ``GateDecision.from_gate``. It is a pure domain
service: it returns a gate and mutates nothing, invokes no persistence, and never
invents a concrete approver identity or authority role, which remain open
decisions supplied by the client workspace (SPEC.md section 11).
"""

from __future__ import annotations

from datetime import date
from typing import Iterable

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    GateApproverNotAuthorizedError,
    GateAuthorRequiredError,
    NotStageZeroGateError,
)
from redops.contexts.engagement.domain.policies import (
    GateApproverAuthorityPolicy,
    ProductionReadyPolicy,
)
from redops.contexts.engagement.domain.value_objects import IntakePackage
from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
    StageGate,
)
from redops.contexts.governance.domain.value_objects import (
    GateDisposition,
    GateState,
    StageTemplate,
)
from redops.contexts.knowledge.domain.entities import Claim

STAGE_ZERO = 0


class StageZeroGateAssembler:
    """Builds and validates the canonical stage 0 gate for one client workspace.

    The package must be production ready (every canonical asset kind present,
    each owned by a named workspace authority, each evidenced by a same-tenant,
    known, directly sourced claim), the assembled gate must pin the template's
    exact stage 0 asset package, and the designated approver must be a named
    authority on the same workspace. A caller-supplied gate that skips any of
    these steps is exactly what this assembler replaces (SPEC.md sections 3, 4
    and 5).
    """

    def assemble(
        self,
        *,
        template: StageTemplate,
        workspace: ClientWorkspace,
        package: IntakePackage,
        approver: str,
        claims: Iterable[Claim],
        proposed_by: str | None = None,
    ) -> StageGate:
        ProductionReadyPolicy().require(package, workspace, claims)
        gate = StageGate.from_assets(
            template,
            STAGE_ZERO,
            tenant_id=workspace.tenant_id,
            assets=package.stage_asset_versions(),
        )
        gate.approver = approver
        gate.proposed_by = proposed_by
        GateApproverAuthorityPolicy().require(gate, workspace)
        return gate


class StageZeroGateRecorder:
    """Records the passing stage 0 "Production Ready" gate decision.

    SPEC.md section 4: a stage is complete only when its required assets exist,
    pass the checkpoint, and receive approval for downstream use, and a passing
    gate pins "the exact evidence and intended downstream use". Given the gate
    ``StageZeroGateAssembler`` already validated, this pure-domain path issues one
    version-specific ``ApprovalRequest`` per required asset on behalf of the gate's
    author, has the workspace's designated approver approve each one, records them
    on the gate, and stores the immutable ``GateDecision`` in the durable
    ``GateLedger``. It refuses a gate for another stage, an absent author or
    approver, and an approver who holds no authority on the workspace, so the
    stage 0 rubric can never approve an unrelated asset package or a self-issued
    approval (SPEC.md sections 3, 4, 5 and 11). It mutates only the gate it is
    given and the ledger; it never invents a concrete human identity.
    """

    def record(
        self,
        *,
        gate: StageGate,
        workspace: ClientWorkspace,
        ledger: GateLedger,
        scope: str,
        checkpoint_evidence: str,
        rationale: str,
        assigned_owner: str,
        due_on: date,
        on: date,
        next_action: str = "",
    ) -> GateDecision:
        if gate.stage_number != STAGE_ZERO:
            raise NotStageZeroGateError(
                f"stage 0 recording path cannot record a decision for stage "
                f"{gate.stage_number}"
            )
        author = gate.proposed_by
        if not author or not author.strip():
            raise GateAuthorRequiredError(
                "stage 0 recording requires the gate's author so an approval "
                "request has a requester distinct from the designated approver"
            )
        GateApproverAuthorityPolicy().require(gate, workspace)
        approver = gate.approver
        if not approver or not approver.strip():
            raise GateApproverNotAuthorizedError(
                "stage 0 recording requires the gate's designated approver"
            )
        for asset in sorted(gate.required_assets, key=str):
            request = ApprovalRequest(
                asset=asset,
                scope=scope,
                requested_by=author,
                approver=approver,
            )
            request.approve(
                actor=approver,
                on=on,
                rationale=f"stage 0 asset {asset} approved for {scope}",
            )
            gate.record_asset_approval(request)
        gate.state = GateState.APPROVED
        decision = GateDecision.from_gate(
            gate,
            ledger=ledger,
            reviewer=approver,
            scope=scope,
            checkpoint_evidence=checkpoint_evidence,
            disposition=GateDisposition.APPROVED,
            rationale=rationale,
            on=on,
            assigned_owner=assigned_owner,
            due_on=due_on,
            next_action=next_action,
        )
        ledger.record(decision)
        return decision
