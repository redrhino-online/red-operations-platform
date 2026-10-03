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

from redops.contexts.commercial.domain.policies import (
    AvatarLockedPolicy,
    DiagnosisEvidencePolicy,
    MarketAwarenessPolicy,
)
from redops.contexts.commercial.domain.value_objects import (
    CampaignMessagePackage,
    CurrencyPackage,
    DiagnosisPackage,
    DiagnosticPackage,
    OfferPackage,
    SignaturePackage,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    AuthorityAmplifierNotApprovedError,
    CampaignMessageNotApprovedError,
    GateApproverNotAuthorizedError,
    GateAuthorRequiredError,
    NotStageEightGateError,
    NotStageFiveGateError,
    NotStageFourGateError,
    NotStageNineGateError,
    NotStageOneGateError,
    NotStageSevenGateError,
    NotStageSixGateError,
    NotStageTenGateError,
    NotStageThreeGateError,
    NotStageTwoGateError,
    NotStageZeroGateError,
    TenantBoundaryError,
)
from redops.contexts.engagement.domain.policies import (
    GateApproverAuthorityPolicy,
    GateOwnerAuthorityPolicy,
    ProductionReadyPolicy,
)
from redops.contexts.engagement.domain.value_objects import IntakePackage
from redops.contexts.execution.domain.value_objects import (
    FunnelIntegrationPackage,
    LaunchQAPackage,
    PerformanceBaselinePackage,
)
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
from redops.contexts.production.domain.value_objects import (
    AuthorityAmplifierPackage,
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
STAGE_NINE = 9
STAGE_TEN = 10


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
    approver, an approver who holds no authority on the workspace, and an
    assigned work owner who holds no authority on the workspace, so the
    stage 0 rubric can never approve an unrelated asset package, a self-issued
    approval or an unaccountable owner (SPEC.md sections 3, 4, 5 and 11). It
    mutates only the gate it is given and the ledger; it never invents a concrete
    human identity.
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
        GateOwnerAuthorityPolicy().require(assigned_owner, workspace)
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


class StageOneGateAssembler:
    """Builds and validates the canonical stage 1 "Avatar Locked" gate.

    SPEC.md section 4, stage 1 "Diagnose" and its "Avatar Locked" checkpoint: a
    stranger can recognize who the customer is, what matters, and why now, and the
    stage is complete only when its required assets exist, pass the checkpoint,
    and receive approval for downstream use. The Commercial ``DiagnosisPackage``
    (cycle 69) projects the three reviewed stage 1 values (``AvatarProfile``,
    ``BusinessSnapshot``, ``OfferFunnelAudit``) onto the nine canonical stage 1
    asset kinds as exact ``StageAssetVersion`` evidence, and the canon maps stage
    1 to files 02, 03 and 04 (SPEC.md section 12.3).

    This assembler composes the pieces so a caller cannot hand an unvalidated
    stage 1 gate to ``GateDecision.from_gate``: the reviewed values are checked
    against same-tenant, directly sourced claims (``AvatarLockedPolicy`` and
    ``DiagnosisEvidencePolicy``), the gate is pinned from the template's exact
    stage 1 asset package, and the designated approver is bound to the workspace
    authority registry (``GateApproverAuthorityPolicy``). It is a pure domain
    service: it returns a gate and mutates nothing, invokes no persistence, and
    never invents a concrete approver identity or authority role (SPEC.md section
    11).
    """

    def assemble(
        self,
        *,
        template: StageTemplate,
        workspace: ClientWorkspace,
        package: DiagnosisPackage,
        approver: str,
        claims: Iterable[Claim],
        proposed_by: str | None = None,
    ) -> StageGate:
        if package.tenant_id != workspace.tenant_id:
            raise TenantBoundaryError(
                f"diagnosis package {package.package_id!r} belongs to tenant "
                f"{package.tenant_id!r}, not workspace tenant "
                f"{workspace.tenant_id!r}"
            )
        evidence = tuple(claims)
        AvatarLockedPolicy().require_locked(package.avatar, evidence)
        DiagnosisEvidencePolicy().require_business_snapshot_sourced(
            package.business_snapshot, evidence
        )
        DiagnosisEvidencePolicy().require_offer_funnel_audit_sourced(
            package.offer_funnel_audit, evidence
        )
        MarketAwarenessPolicy().require_targetable(package.awareness_map)
        gate = StageGate.from_assets(
            template,
            STAGE_ONE,
            tenant_id=workspace.tenant_id,
            assets=package.stage_asset_versions(),
        )
        gate.approver = approver
        gate.proposed_by = proposed_by
        GateApproverAuthorityPolicy().require(gate, workspace)
        return gate


class StageOneGateRecorder:
    """Records the passing stage 1 "Avatar Locked" gate decision.

    SPEC.md section 4: a passing gate pins "the exact evidence and intended
    downstream use", approval is version specific, and the author cannot
    impersonate the approver. Given the gate ``StageOneGateAssembler`` already
    validated, this pure-domain path issues one version-specific
    ``ApprovalRequest`` per required asset on behalf of the gate's author, has the
    workspace's designated approver approve each one, records them on the gate,
    and stores the immutable ``GateDecision`` in the durable ``GateLedger``. It
    refuses a gate for another stage, an absent author or approver, an approver
    who holds no authority on the workspace, and an assigned work owner who holds
    no authority on the workspace, so the stage 1 rubric can never approve an
    unrelated asset package, a self-issued approval or an unaccountable owner
    (SPEC.md sections 3, 4, 5 and 11). Because stage 1 depends on stage 0,
    ``GateDecision.from_gate`` and ``GateLedger.record`` refuse a passing decision
    until the ledger holds a passing stage 0 decision, so a failed prerequisite
    blocks dependent authorization (SPEC.md section 4). It mutates only the gate
    it is given and the ledger; it never invents a concrete human identity.
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
        if gate.stage_number != STAGE_ONE:
            raise NotStageOneGateError(
                f"stage 1 recording path cannot record a decision for stage "
                f"{gate.stage_number}"
            )
        author = gate.proposed_by
        if not author or not author.strip():
            raise GateAuthorRequiredError(
                "stage 1 recording requires the gate's author so an approval "
                "request has a requester distinct from the designated approver"
            )
        GateApproverAuthorityPolicy().require(gate, workspace)
        GateOwnerAuthorityPolicy().require(assigned_owner, workspace)
        approver = gate.approver
        if not approver or not approver.strip():
            raise GateApproverNotAuthorizedError(
                "stage 1 recording requires the gate's designated approver"
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
                rationale=f"stage 1 asset {asset} approved for {scope}",
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


class StageTwoGateAssembler:
    """Builds and validates the canonical stage 2 "Currency Locked" gate.

    SPEC.md section 4, stage 2 "Position" and its "Currency Locked" checkpoint:
    "one primary outcome connects a specific person, measurable movement, and
    distinct mechanism", and the stage is complete only when its required assets
    exist, pass the checkpoint, and receive approval for downstream use. The
    Commercial ``CurrencyPackage`` (cycle 71) projects the four reviewed stage 2
    values (``CurrencyInventory``, ``PositioningDecision``, ``PrimaryCurrency``,
    ``MillionDollarMessage``) onto the ten canonical stage 2 asset kinds as exact
    ``StageAssetVersion`` evidence, and the canon maps stage 2 to files 04, 05 and
    06 (SPEC.md section 12.3).

    Unlike stage 1, the "Currency Locked" checkpoint turns on the primary
    currency's internal specificity rather than external customer evidence, and
    the ``PrimaryCurrency`` value object already refuses an unspecified audience
    or an unmeasured outcome at construction, so this assembler adds no separate
    source policy. It composes the pieces so a caller cannot hand an unvalidated
    stage 2 gate to ``GateDecision.from_gate``: the reviewed package is checked
    against the workspace tenant, the gate is pinned from the template's exact
    stage 2 asset package, and the designated approver is bound to the workspace
    authority registry (``GateApproverAuthorityPolicy``). It is a pure domain
    service: it returns a gate and mutates nothing, invokes no persistence, and
    never invents a concrete approver identity or authority role (SPEC.md section
    11).
    """

    def assemble(
        self,
        *,
        template: StageTemplate,
        workspace: ClientWorkspace,
        package: CurrencyPackage,
        approver: str,
        proposed_by: str | None = None,
    ) -> StageGate:
        if package.tenant_id != workspace.tenant_id:
            raise TenantBoundaryError(
                f"currency package {package.package_id!r} belongs to tenant "
                f"{package.tenant_id!r}, not workspace tenant "
                f"{workspace.tenant_id!r}"
            )
        gate = StageGate.from_assets(
            template,
            STAGE_TWO,
            tenant_id=workspace.tenant_id,
            assets=package.stage_asset_versions(),
        )
        gate.approver = approver
        gate.proposed_by = proposed_by
        GateApproverAuthorityPolicy().require(gate, workspace)
        return gate


class StageTwoGateRecorder:
    """Records the passing stage 2 "Currency Locked" gate decision.

    SPEC.md section 4: a passing gate pins "the exact evidence and intended
    downstream use", approval is version specific, and the author cannot
    impersonate the approver. Given the gate ``StageTwoGateAssembler`` already
    validated, this pure-domain path issues one version-specific
    ``ApprovalRequest`` per required asset on behalf of the gate's author, has the
    workspace's designated approver approve each one, records them on the gate,
    and stores the immutable ``GateDecision`` in the durable ``GateLedger``. It
    refuses a gate for another stage, an absent author or approver, an approver
    who holds no authority on the workspace, and an assigned work owner who holds
    no authority on the workspace, so the stage 2 rubric can never approve an
    unrelated asset package, a self-issued approval or an unaccountable owner
    (SPEC.md sections 3, 4, 5 and 11). Because stage 2 depends on stage 1,
    ``GateDecision.from_gate`` and ``GateLedger.record`` refuse a passing decision
    until the ledger holds a passing stage 1 decision, so a failed prerequisite
    blocks dependent authorization (SPEC.md section 4). It mutates only the gate
    it is given and the ledger; it never invents a concrete human identity.
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
        if gate.stage_number != STAGE_TWO:
            raise NotStageTwoGateError(
                f"stage 2 recording path cannot record a decision for stage "
                f"{gate.stage_number}"
            )
        author = gate.proposed_by
        if not author or not author.strip():
            raise GateAuthorRequiredError(
                "stage 2 recording requires the gate's author so an approval "
                "request has a requester distinct from the designated approver"
            )
        GateApproverAuthorityPolicy().require(gate, workspace)
        GateOwnerAuthorityPolicy().require(assigned_owner, workspace)
        approver = gate.approver
        if not approver or not approver.strip():
            raise GateApproverNotAuthorizedError(
                "stage 2 recording requires the gate's designated approver"
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
                rationale=f"stage 2 asset {asset} approved for {scope}",
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


class StageThreeGateAssembler:
    """Builds and validates the canonical stage 3 "Diagnostic Model Approved" gate.

    SPEC.md section 4, stage 3 "Model" and its "Diagnostic Model Approved"
    checkpoint: "a prospect can recognize their current level and desired next
    level using observable differences", and the stage is complete only when its
    required assets exist, pass the checkpoint, and receive approval for
    downstream use. The Commercial ``DiagnosticPackage`` (cycle 73) projects the
    single reviewed ``DiagnosticModel`` -- the Profit Pyramid levels, their
    observable measures, symptoms, behaviors and problems, progression,
    qualification logic, name, visual and explanatory copy -- onto the ten
    canonical stage 3 asset kinds as exact ``StageAssetVersion`` evidence, and the
    canon maps stage 3 to files 07 and 08 (SPEC.md section 12.3).

    Unlike stage 1, the "Diagnostic Model Approved" checkpoint turns on
    adjacent-level observable distinguishability, which ``DiagnosticModel``
    already enforces at construction, so this assembler adds no separate source
    policy. It composes the pieces so a caller cannot hand an unvalidated stage 3
    gate to ``GateDecision.from_gate``: the reviewed package is checked against
    the workspace tenant, the gate is pinned from the template's exact stage 3
    asset package, and the designated approver is bound to the workspace
    authority registry (``GateApproverAuthorityPolicy``). It is a pure domain
    service: it returns a gate and mutates nothing, invokes no persistence, and
    never invents a concrete approver identity or authority role (SPEC.md section
    11).
    """

    def assemble(
        self,
        *,
        template: StageTemplate,
        workspace: ClientWorkspace,
        package: DiagnosticPackage,
        approver: str,
        proposed_by: str | None = None,
    ) -> StageGate:
        if package.tenant_id != workspace.tenant_id:
            raise TenantBoundaryError(
                f"diagnostic package {package.package_id!r} belongs to tenant "
                f"{package.tenant_id!r}, not workspace tenant "
                f"{workspace.tenant_id!r}"
            )
        gate = StageGate.from_assets(
            template,
            STAGE_THREE,
            tenant_id=workspace.tenant_id,
            assets=package.stage_asset_versions(),
        )
        gate.approver = approver
        gate.proposed_by = proposed_by
        GateApproverAuthorityPolicy().require(gate, workspace)
        return gate


class StageThreeGateRecorder:
    """Records the passing stage 3 "Diagnostic Model Approved" gate decision.

    SPEC.md section 4: a passing gate pins "the exact evidence and intended
    downstream use", approval is version specific, and the author cannot
    impersonate the approver. Given the gate ``StageThreeGateAssembler`` already
    validated, this pure-domain path issues one version-specific
    ``ApprovalRequest`` per required asset on behalf of the gate's author, has the
    workspace's designated approver approve each one, records them on the gate,
    and stores the immutable ``GateDecision`` in the durable ``GateLedger``. It
    refuses a gate for another stage, an absent author or approver, an approver
    who holds no authority on the workspace, and an assigned work owner who holds
    no authority on the workspace, so the stage 3 rubric can never approve an
    unrelated asset package, a self-issued approval or an unaccountable owner
    (SPEC.md sections 3, 4, 5 and 11). Because stage 3 depends on stage 2,
    ``GateDecision.from_gate`` and ``GateLedger.record`` refuse a passing decision
    until the ledger holds a passing stage 2 decision, so a failed prerequisite
    blocks dependent authorization (SPEC.md section 4). It mutates only the gate
    it is given and the ledger; it never invents a concrete human identity.
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
        if gate.stage_number != STAGE_THREE:
            raise NotStageThreeGateError(
                f"stage 3 recording path cannot record a decision for stage "
                f"{gate.stage_number}"
            )
        author = gate.proposed_by
        if not author or not author.strip():
            raise GateAuthorRequiredError(
                "stage 3 recording requires the gate's author so an approval "
                "request has a requester distinct from the designated approver"
            )
        GateApproverAuthorityPolicy().require(gate, workspace)
        GateOwnerAuthorityPolicy().require(assigned_owner, workspace)
        approver = gate.approver
        if not approver or not approver.strip():
            raise GateApproverNotAuthorizedError(
                "stage 3 recording requires the gate's designated approver"
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
                rationale=f"stage 3 asset {asset} approved for {scope}",
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


class StageFourGateAssembler:
    """Builds and validates the canonical stage 4 "IP Architecture Locked" gate.

    SPEC.md section 4, stage 4 "Package IP" and its "IP Architecture Locked"
    checkpoint: "the transformation is coherent and explainable without listing
    every tactic", and the stage is complete only when its required assets exist,
    pass the checkpoint, and receive approval for downstream use. The Commercial
    ``SignaturePackage`` (cycle 75) projects the single reviewed
    ``SignatureSolution`` -- the transformation map, process inventory, three
    phases, nine steps, named stages, starting and final states, stage
    inputs/actions/outputs, narrative and visual -- onto the twelve canonical
    stage 4 asset kinds as exact ``StageAssetVersion`` evidence, and the canon maps
    stage 4 to files 09 and 10 (SPEC.md section 12.3).

    Unlike stage 1, the "IP Architecture Locked" checkpoint turns on the coherence
    and continuity of the reviewed transformation, which ``SignatureSolution``
    already enforces at construction, so this assembler adds no separate source
    policy. It composes the pieces so a caller cannot hand an unvalidated stage 4
    gate to ``GateDecision.from_gate``: the reviewed package is checked against
    the workspace tenant, the gate is pinned from the template's exact stage 4
    asset package, and the designated approver is bound to the workspace authority
    registry (``GateApproverAuthorityPolicy``). It is a pure domain service: it
    returns a gate and mutates nothing, invokes no persistence, and never invents
    a concrete approver identity or authority role (SPEC.md section 11).
    """

    def assemble(
        self,
        *,
        template: StageTemplate,
        workspace: ClientWorkspace,
        package: SignaturePackage,
        approver: str,
        proposed_by: str | None = None,
    ) -> StageGate:
        if package.tenant_id != workspace.tenant_id:
            raise TenantBoundaryError(
                f"signature package {package.package_id!r} belongs to tenant "
                f"{package.tenant_id!r}, not workspace tenant "
                f"{workspace.tenant_id!r}"
            )
        gate = StageGate.from_assets(
            template,
            STAGE_FOUR,
            tenant_id=workspace.tenant_id,
            assets=package.stage_asset_versions(),
        )
        gate.approver = approver
        gate.proposed_by = proposed_by
        GateApproverAuthorityPolicy().require(gate, workspace)
        return gate


class StageFourGateRecorder:
    """Records the passing stage 4 "IP Architecture Locked" gate decision.

    SPEC.md section 4: a passing gate pins "the exact evidence and intended
    downstream use", approval is version specific, and the author cannot
    impersonate the approver. Given the gate ``StageFourGateAssembler`` already
    validated, this pure-domain path issues one version-specific
    ``ApprovalRequest`` per required asset on behalf of the gate's author, has the
    workspace's designated approver approve each one, records them on the gate,
    and stores the immutable ``GateDecision`` in the durable ``GateLedger``. It
    refuses a gate for another stage, an absent author or approver, an approver
    who holds no authority on the workspace, and an assigned work owner who holds
    no authority on the workspace, so the stage 4 rubric can never approve an
    unrelated asset package, a self-issued approval or an unaccountable owner
    (SPEC.md sections 3, 4, 5 and 11). Because stage 4 depends on stage 3,
    ``GateDecision.from_gate`` and ``GateLedger.record`` refuse a passing decision
    until the ledger holds a passing stage 3 decision, so a failed prerequisite
    blocks dependent authorization (SPEC.md section 4). It mutates only the gate
    it is given and the ledger; it never invents a concrete human identity.
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
        if gate.stage_number != STAGE_FOUR:
            raise NotStageFourGateError(
                f"stage 4 recording path cannot record a decision for stage "
                f"{gate.stage_number}"
            )
        author = gate.proposed_by
        if not author or not author.strip():
            raise GateAuthorRequiredError(
                "stage 4 recording requires the gate's author so an approval "
                "request has a requester distinct from the designated approver"
            )
        GateApproverAuthorityPolicy().require(gate, workspace)
        GateOwnerAuthorityPolicy().require(assigned_owner, workspace)
        approver = gate.approver
        if not approver or not approver.strip():
            raise GateApproverNotAuthorizedError(
                "stage 4 recording requires the gate's designated approver"
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
                rationale=f"stage 4 asset {asset} approved for {scope}",
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


class StageFiveGateAssembler:
    """Builds and validates the canonical stage 5 "Offer Locked" gate.

    SPEC.md section 4, stage 5 "Productize" and its "Offer Locked" checkpoint:
    "every method step has an action, actor, deliverable, timing and measure", and
    the stage is complete only when its required assets exist, pass the checkpoint,
    and receive approval for downstream use. The Commercial ``OfferPackage`` (cycle
    77) projects the single reviewed ``DeliverySpecification`` -- the delivery
    model, duration, modules, responsibilities, support cadence, stage
    deliverables, outcome measures, pricing and payments, scope, guarantee
    decision, eligibility and offer stack -- onto the twelve canonical stage 5
    asset kinds as exact ``StageAssetVersion`` evidence, and the canon maps stage 5
    to files 11 and 12 (SPEC.md section 12.3).

    Unlike stage 1, the "Offer Locked" checkpoint turns on every delivered method
    step carrying an action, actor, deliverable, timing and measure, which
    ``DeliverySpecification`` already enforces at construction, so this assembler
    adds no separate source policy. It composes the pieces so a caller cannot hand
    an unvalidated stage 5 gate to ``GateDecision.from_gate``: the reviewed package
    is checked against the workspace tenant, the gate is pinned from the template's
    exact stage 5 asset package, and the designated approver is bound to the
    workspace authority registry (``GateApproverAuthorityPolicy``). It is a pure
    domain service: it returns a gate and mutates nothing, invokes no persistence,
    and never invents a concrete approver identity or authority role (SPEC.md
    section 11).
    """

    def assemble(
        self,
        *,
        template: StageTemplate,
        workspace: ClientWorkspace,
        package: OfferPackage,
        approver: str,
        proposed_by: str | None = None,
    ) -> StageGate:
        if package.tenant_id != workspace.tenant_id:
            raise TenantBoundaryError(
                f"offer package {package.package_id!r} belongs to tenant "
                f"{package.tenant_id!r}, not workspace tenant "
                f"{workspace.tenant_id!r}"
            )
        gate = StageGate.from_assets(
            template,
            STAGE_FIVE,
            tenant_id=workspace.tenant_id,
            assets=package.stage_asset_versions(),
        )
        gate.approver = approver
        gate.proposed_by = proposed_by
        GateApproverAuthorityPolicy().require(gate, workspace)
        return gate


class StageFiveGateRecorder:
    """Records the passing stage 5 "Offer Locked" gate decision.

    SPEC.md section 4: a passing gate pins "the exact evidence and intended
    downstream use", approval is version specific, and the author cannot
    impersonate the approver. Given the gate ``StageFiveGateAssembler`` already
    validated, this pure-domain path issues one version-specific
    ``ApprovalRequest`` per required asset on behalf of the gate's author, has the
    workspace's designated approver approve each one, records them on the gate,
    and stores the immutable ``GateDecision`` in the durable ``GateLedger``. It
    refuses a gate for another stage, an absent author or approver, an approver
    who holds no authority on the workspace, and an assigned work owner who holds
    no authority on the workspace, so the stage 5 rubric can never approve an
    unrelated asset package, a self-issued approval or an unaccountable owner
    (SPEC.md sections 3, 4, 5 and 11). Because stage 5 depends on stage 4,
    ``GateDecision.from_gate`` and ``GateLedger.record`` refuse a passing decision
    until the ledger holds a passing stage 4 decision, so a failed prerequisite
    blocks dependent authorization (SPEC.md section 4). It mutates only the gate
    it is given and the ledger; it never invents a concrete human identity.
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
        if gate.stage_number != STAGE_FIVE:
            raise NotStageFiveGateError(
                f"stage 5 recording path cannot record a decision for stage "
                f"{gate.stage_number}"
            )
        author = gate.proposed_by
        if not author or not author.strip():
            raise GateAuthorRequiredError(
                "stage 5 recording requires the gate's author so an approval "
                "request has a requester distinct from the designated approver"
            )
        GateApproverAuthorityPolicy().require(gate, workspace)
        GateOwnerAuthorityPolicy().require(assigned_owner, workspace)
        approver = gate.approver
        if not approver or not approver.strip():
            raise GateApproverNotAuthorizedError(
                "stage 5 recording requires the gate's designated approver"
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
                rationale=f"stage 5 asset {asset} approved for {scope}",
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


class StageSixGateAssembler:
    """Builds and validates the canonical stage 6 "Campaign Message Approved" gate.

    SPEC.md section 4, stage 6 "Message" and its "Campaign Message Approved"
    checkpoint: "avatar, currency, problem, promise, method, product and CTA
    agree", and the stage is complete only when its required assets exist, pass the
    checkpoint, and receive approval for downstream use. The Commercial
    ``CampaignMessagePackage`` (cycle 79) projects the single reviewed
    ``CampaignMessage`` -- the promise, problem hierarchy, desired outcome, proof
    and objections, story, method explanation, CTA, lead magnet, hook, angles,
    landing message and Authority Amplifier outline, grounded on the approved
    stage 5 offer -- onto the twelve canonical stage 6 asset kinds as exact
    ``StageAssetVersion`` evidence, and the canon maps stage 6 to files 06, 15, 24
    and 25-28 (SPEC.md section 12.3).

    Unlike stages 2 through 5, the reviewed message is not constructively complete
    at construction: ``CampaignMessage`` only proves the "Campaign Message
    Approved" congruence when it has passed ``approve``, which checks the message
    against the approved stage 5 offer and the approved method's locked stage 2
    currency and stage 3 diagnostic model. This assembler therefore refuses a
    package whose message is not approved, so a draft or review-required message
    can never be pinned as passing stage 6 evidence. It also checks the reviewed
    package against the workspace tenant, pins the gate from the template's exact
    stage 6 asset package, and binds the designated approver to the workspace
    authority registry (``GateApproverAuthorityPolicy``). It is a pure domain
    service: it returns a gate and mutates nothing, invokes no persistence, and
    never invents a concrete approver identity or authority role (SPEC.md section
    11).
    """

    def assemble(
        self,
        *,
        template: StageTemplate,
        workspace: ClientWorkspace,
        package: CampaignMessagePackage,
        approver: str,
        proposed_by: str | None = None,
    ) -> StageGate:
        if package.tenant_id != workspace.tenant_id:
            raise TenantBoundaryError(
                f"campaign message package {package.package_id!r} belongs to "
                f"tenant {package.tenant_id!r}, not workspace tenant "
                f"{workspace.tenant_id!r}"
            )
        if not package.message.is_approved:
            raise CampaignMessageNotApprovedError(
                f"campaign message {package.message.message_id!r} cannot pass "
                "stage 6: it has not been approved against the stage 5 offer and "
                "the approved method"
            )
        gate = StageGate.from_assets(
            template,
            STAGE_SIX,
            tenant_id=workspace.tenant_id,
            assets=package.stage_asset_versions(),
        )
        gate.approver = approver
        gate.proposed_by = proposed_by
        GateApproverAuthorityPolicy().require(gate, workspace)
        return gate


class StageSixGateRecorder:
    """Records the passing stage 6 "Campaign Message Approved" gate decision.

    SPEC.md section 4: a passing gate pins "the exact evidence and intended
    downstream use", approval is version specific, and the author cannot
    impersonate the approver. Given the gate ``StageSixGateAssembler`` already
    validated, this pure-domain path issues one version-specific
    ``ApprovalRequest`` per required asset on behalf of the gate's author, has the
    workspace's designated approver approve each one, records them on the gate,
    and stores the immutable ``GateDecision`` in the durable ``GateLedger``. It
    refuses a gate for another stage, an absent author or approver, an approver
    who holds no authority on the workspace, and an assigned work owner who holds
    no authority on the workspace, so the stage 6 rubric can never approve an
    unrelated asset package, a self-issued approval or an unaccountable owner
    (SPEC.md sections 3, 4, 5 and 11). Because stage 6 depends on stage 5,
    ``GateDecision.from_gate`` and ``GateLedger.record`` refuse a passing decision
    until the ledger holds a passing stage 5 decision, so a failed prerequisite
    blocks dependent authorization (SPEC.md section 4). It mutates only the gate
    it is given and the ledger; it never invents a concrete human identity.
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
        if gate.stage_number != STAGE_SIX:
            raise NotStageSixGateError(
                f"stage 6 recording path cannot record a decision for stage "
                f"{gate.stage_number}"
            )
        author = gate.proposed_by
        if not author or not author.strip():
            raise GateAuthorRequiredError(
                "stage 6 recording requires the gate's author so an approval "
                "request has a requester distinct from the designated approver"
            )
        GateApproverAuthorityPolicy().require(gate, workspace)
        GateOwnerAuthorityPolicy().require(assigned_owner, workspace)
        approver = gate.approver
        if not approver or not approver.strip():
            raise GateApproverNotAuthorizedError(
                "stage 6 recording requires the gate's designated approver"
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
                rationale=f"stage 6 asset {asset} approved for {scope}",
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


class StageSevenGateAssembler:
    """Builds and validates the canonical stage 7 "Authority Amplifier Approved" gate.

    SPEC.md section 4, stage 7 "Produce" and its "Authority Amplifier Approved"
    checkpoint: "message and supported proof pass review before visual or video
    production; final asset gives a credible next action", and the stage is
    complete only when its required assets exist, pass the checkpoint, and receive
    approval for downstream use. The Production ``AuthorityAmplifierPackage``
    (cycle 81) projects the single reviewed ``AuthorityAmplifier`` -- the six
    script sections in Promise, Proof, Problems, Steps, Context, Action order and
    the eight visual assets (storyboard, brand treatment, presentation, speaker
    notes, recording, edited and hosted video, player assets) -- onto the nine
    canonical stage 7 asset kinds as exact ``StageAssetVersion`` evidence, and the
    canon maps stage 7 to files 13-18 and 28 (SPEC.md section 12.3).

    Unlike stages 2 through 5, the reviewed amplifier is not constructively
    complete at construction: stage 7 has two distinct approvals, and
    ``AuthorityAmplifier`` only proves the second one -- final creative
    acceptance -- when it has passed ``approve_creative``, which itself requires
    the earlier script approval and a complete visual package. This assembler
    therefore refuses a package whose amplifier has not reached creative
    acceptance, so a draft, script-approved or review-required amplifier can never
    be pinned as passing stage 7 evidence. It also checks the reviewed package
    against the workspace tenant, pins the gate from the template's exact stage 7
    asset package, and binds the designated approver to the workspace authority
    registry (``GateApproverAuthorityPolicy``). It is a pure domain service: it
    returns a gate and mutates nothing, invokes no persistence, and never invents
    a concrete approver identity or authority role (SPEC.md section 11).
    """

    def assemble(
        self,
        *,
        template: StageTemplate,
        workspace: ClientWorkspace,
        package: AuthorityAmplifierPackage,
        approver: str,
        proposed_by: str | None = None,
    ) -> StageGate:
        if package.tenant_id != workspace.tenant_id:
            raise TenantBoundaryError(
                f"authority amplifier package {package.package_id!r} belongs to "
                f"tenant {package.tenant_id!r}, not workspace tenant "
                f"{workspace.tenant_id!r}"
            )
        if not package.amplifier.is_approved:
            raise AuthorityAmplifierNotApprovedError(
                f"authority amplifier {package.amplifier.amplifier_id!r} cannot "
                "pass stage 7: it has not received final creative acceptance, the "
                "second of the two stage 7 approvals"
            )
        gate = StageGate.from_assets(
            template,
            STAGE_SEVEN,
            tenant_id=workspace.tenant_id,
            assets=package.stage_asset_versions(),
        )
        gate.approver = approver
        gate.proposed_by = proposed_by
        GateApproverAuthorityPolicy().require(gate, workspace)
        return gate


class StageSevenGateRecorder:
    """Records the passing stage 7 "Authority Amplifier Approved" gate decision.

    SPEC.md section 4: a passing gate pins "the exact evidence and intended
    downstream use", approval is version specific, and the author cannot
    impersonate the approver. Given the gate ``StageSevenGateAssembler`` already
    validated, this pure-domain path issues one version-specific
    ``ApprovalRequest`` per required asset on behalf of the gate's author, has the
    workspace's designated approver approve each one, records them on the gate,
    and stores the immutable ``GateDecision`` in the durable ``GateLedger``. It
    refuses a gate for another stage, an absent author or approver, an approver
    who holds no authority on the workspace, and an assigned work owner who holds
    no authority on the workspace, so the stage 7 rubric can never approve an
    unrelated asset package, a self-issued approval or an unaccountable owner
    (SPEC.md sections 3, 4, 5 and 11). Because stage 7 depends on stage 6,
    ``GateDecision.from_gate`` and ``GateLedger.record`` refuse a passing decision
    until the ledger holds a passing stage 6 decision, so a failed prerequisite
    blocks dependent authorization (SPEC.md section 4). It mutates only the gate
    it is given and the ledger; it never invents a concrete human identity.
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
        if gate.stage_number != STAGE_SEVEN:
            raise NotStageSevenGateError(
                f"stage 7 recording path cannot record a decision for stage "
                f"{gate.stage_number}"
            )
        author = gate.proposed_by
        if not author or not author.strip():
            raise GateAuthorRequiredError(
                "stage 7 recording requires the gate's author so an approval "
                "request has a requester distinct from the designated approver"
            )
        GateApproverAuthorityPolicy().require(gate, workspace)
        GateOwnerAuthorityPolicy().require(assigned_owner, workspace)
        approver = gate.approver
        if not approver or not approver.strip():
            raise GateApproverNotAuthorizedError(
                "stage 7 recording requires the gate's designated approver"
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
                rationale=f"stage 7 asset {asset} approved for {scope}",
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


class StageEightGateAssembler:
    """Builds and validates the canonical stage 8 "Funnel Complete" gate.

    SPEC.md section 4, stage 8 "Integrate" and its "Funnel Complete" checkpoint:
    "a test prospect completes capture, engagement and conversion handoffs with
    reliable records and ownership", and the stage is complete only when its
    required assets exist, pass the checkpoint, and receive approval for
    downstream use. The Execution ``FunnelIntegrationPackage`` (cycle 83) projects
    the single reviewed ``FunnelIntegration`` -- the campaign architecture, pages,
    forms, qualification, booking, sequences, CRM, tags, automation, analytics,
    tracking, sales handoff and SOPs -- onto the thirteen canonical stage 8 asset
    kinds as exact ``StageAssetVersion`` evidence, and the canon maps stage 8 to
    files 13, 14, 21 and 22 (SPEC.md section 12.3).

    The reviewed funnel is not constructively complete at construction: it reaches
    ``FunnelState.COMPLETE`` only after ``mark_funnel_complete`` passes the
    checkpoint on a same-tenant ``ProspectPathDryRun``, and the bridge package
    itself refuses a funnel that has not passed "Funnel Complete". This assembler
    therefore never pins a draft or review-required funnel as passing stage 8
    evidence. It checks the reviewed package against the workspace tenant, pins the
    gate from the template's exact stage 8 asset package, and binds the designated
    approver to the workspace authority registry
    (``GateApproverAuthorityPolicy``). It is a pure domain service: it returns a
    gate and mutates nothing, invokes no persistence, and never invents a concrete
    approver identity or authority role (SPEC.md section 11).
    """

    def assemble(
        self,
        *,
        template: StageTemplate,
        workspace: ClientWorkspace,
        package: FunnelIntegrationPackage,
        approver: str,
        proposed_by: str | None = None,
    ) -> StageGate:
        if package.tenant_id != workspace.tenant_id:
            raise TenantBoundaryError(
                f"funnel integration package {package.package_id!r} belongs to "
                f"tenant {package.tenant_id!r}, not workspace tenant "
                f"{workspace.tenant_id!r}"
            )
        gate = StageGate.from_assets(
            template,
            STAGE_EIGHT,
            tenant_id=workspace.tenant_id,
            assets=package.stage_asset_versions(),
        )
        gate.approver = approver
        gate.proposed_by = proposed_by
        GateApproverAuthorityPolicy().require(gate, workspace)
        return gate


class StageEightGateRecorder:
    """Records the passing stage 8 "Funnel Complete" gate decision.

    SPEC.md section 4: a passing gate pins "the exact evidence and intended
    downstream use", approval is version specific, and the author cannot
    impersonate the approver. Given the gate ``StageEightGateAssembler`` already
    validated, this pure-domain path issues one version-specific
    ``ApprovalRequest`` per required asset on behalf of the gate's author, has the
    workspace's designated approver approve each one, records them on the gate,
    and stores the immutable ``GateDecision`` in the durable ``GateLedger``. It
    refuses a gate for another stage, an absent author or approver, an approver
    who holds no authority on the workspace, and an assigned work owner who holds
    no authority on the workspace, so the stage 8 rubric can never approve an
    unrelated asset package, a self-issued approval or an unaccountable owner
    (SPEC.md sections 3, 4, 5 and 11). Because stage 8 depends on stage 7,
    ``GateDecision.from_gate`` and ``GateLedger.record`` refuse a passing decision
    until the ledger holds a passing stage 7 decision, so a failed prerequisite
    blocks dependent authorization (SPEC.md section 4). It mutates only the gate
    it is given and the ledger; it never invents a concrete human identity.
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
        if gate.stage_number != STAGE_EIGHT:
            raise NotStageEightGateError(
                f"stage 8 recording path cannot record a decision for stage "
                f"{gate.stage_number}"
            )
        author = gate.proposed_by
        if not author or not author.strip():
            raise GateAuthorRequiredError(
                "stage 8 recording requires the gate's author so an approval "
                "request has a requester distinct from the designated approver"
            )
        GateApproverAuthorityPolicy().require(gate, workspace)
        GateOwnerAuthorityPolicy().require(assigned_owner, workspace)
        approver = gate.approver
        if not approver or not approver.strip():
            raise GateApproverNotAuthorizedError(
                "stage 8 recording requires the gate's designated approver"
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
                rationale=f"stage 8 asset {asset} approved for {scope}",
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


class StageNineGateAssembler:
    """Builds and validates the canonical stage 9 "Launch Approved" gate.

    SPEC.md section 4, stage 9 "QA" and its "Launch Approved" checkpoint: "all
    critical path checks pass, exceptions have owners, and the designated human
    authorizes traffic", and the stage is complete only when its required assets
    exist, pass the checkpoint, and receive approval for downstream use. The
    Execution ``LaunchQAPackage`` (cycle 85) projects the single reviewed
    ``LaunchQA`` -- the recorded message, technical and commercial tests on
    desktop and mobile, forms, CRM, email, automation, booking, tracking, payment
    when relevant, handoff, client approval, budget, creative, dashboard and the
    launch decision -- onto the sixteen canonical stage 9 asset kinds as exact
    ``StageAssetVersion`` evidence, and the canon maps stage 9 to files 01, 08, 21,
    22 and 24 (SPEC.md section 12.3).

    The reviewed QA is not constructively ready at construction: it reaches
    ``LaunchQAState.READY_FOR_TRAFFIC`` only after ``authorize_traffic`` passes the
    checkpoint on a complete same-tenant funnel and a designated human
    authorization, and the bridge package itself refuses a QA that has not passed
    "Launch Approved". This assembler therefore never pins a draft or
    review-required QA as passing stage 9 evidence. It checks the reviewed package
    against the workspace tenant, pins the gate from the template's exact stage 9
    asset package, and binds the designated approver to the workspace authority
    registry (``GateApproverAuthorityPolicy``). It is a pure domain service: it
    returns a gate and mutates nothing, invokes no persistence, and never invents a
    concrete approver identity or authority role (SPEC.md section 11).
    """

    def assemble(
        self,
        *,
        template: StageTemplate,
        workspace: ClientWorkspace,
        package: LaunchQAPackage,
        approver: str,
        proposed_by: str | None = None,
    ) -> StageGate:
        if package.tenant_id != workspace.tenant_id:
            raise TenantBoundaryError(
                f"launch QA package {package.package_id!r} belongs to tenant "
                f"{package.tenant_id!r}, not workspace tenant "
                f"{workspace.tenant_id!r}"
            )
        gate = StageGate.from_assets(
            template,
            STAGE_NINE,
            tenant_id=workspace.tenant_id,
            assets=package.stage_asset_versions(),
        )
        gate.approver = approver
        gate.proposed_by = proposed_by
        GateApproverAuthorityPolicy().require(gate, workspace)
        return gate


class StageNineGateRecorder:
    """Records the passing stage 9 "Launch Approved" gate decision.

    SPEC.md section 4: a passing gate pins "the exact evidence and intended
    downstream use", approval is version specific, and the author cannot
    impersonate the approver. Given the gate ``StageNineGateAssembler`` already
    validated, this pure-domain path issues one version-specific
    ``ApprovalRequest`` per required asset on behalf of the gate's author, has the
    workspace's designated approver approve each one, records them on the gate,
    and stores the immutable ``GateDecision`` in the durable ``GateLedger``. It
    refuses a gate for another stage, an absent author or approver, an approver
    who holds no authority on the workspace, and an assigned work owner who holds
    no authority on the workspace, so the stage 9 rubric can never approve an
    unrelated asset package, a self-issued approval or an unaccountable owner
    (SPEC.md sections 3, 4, 5 and 11). Because stage 9 depends on stage 8,
    ``GateDecision.from_gate`` and ``GateLedger.record`` refuse a passing decision
    until the ledger holds a passing stage 8 decision, so a failed prerequisite
    blocks dependent authorization (SPEC.md section 4). It mutates only the gate
    it is given and the ledger; it never invents a concrete human identity.
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
        if gate.stage_number != STAGE_NINE:
            raise NotStageNineGateError(
                f"stage 9 recording path cannot record a decision for stage "
                f"{gate.stage_number}"
            )
        author = gate.proposed_by
        if not author or not author.strip():
            raise GateAuthorRequiredError(
                "stage 9 recording requires the gate's author so an approval "
                "request has a requester distinct from the designated approver"
            )
        GateApproverAuthorityPolicy().require(gate, workspace)
        GateOwnerAuthorityPolicy().require(assigned_owner, workspace)
        approver = gate.approver
        if not approver or not approver.strip():
            raise GateApproverNotAuthorizedError(
                "stage 9 recording requires the gate's designated approver"
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
                rationale=f"stage 9 asset {asset} approved for {scope}",
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


class StageTenGateAssembler:
    """Builds and validates the canonical stage 10 "Performance Baseline" gate.

    SPEC.md section 4, stage 10 "Launch" and its "Performance Baseline
    Established" checkpoint: "the first qualified traffic and subsequent lead,
    appointment and sale are distinct observed milestones, with missing
    observations shown as pending", and the stage is complete only when its
    required assets exist, pass the checkpoint, and receive approval for
    downstream use. The Execution ``PerformanceBaselinePackage`` (cycle 87)
    projects the single reviewed ``PerformanceBaseline`` -- the live campaign,
    spend and lead records, conversion and engagement measures, applications,
    bookings, shows, closes, acquisition cost, attribution and issue log -- onto
    the twelve canonical stage 10 asset kinds as exact ``StageAssetVersion``
    evidence, and the canon maps stage 10 to files 22, 23, 29-31, 33 and 34
    (SPEC.md section 12.3).

    The reviewed baseline is not constructively established at construction: it
    reaches ``PerformanceBaselineState.ESTABLISHED`` only after ``establish``
    passes the checkpoint on the ready-for-traffic stage 9 launch QA and an
    observed first qualified traffic milestone, and the bridge package itself
    refuses a baseline that has not passed "Performance Baseline Established".
    This assembler therefore never pins a draft or review-required baseline as
    passing stage 10 evidence. It checks the reviewed package against the
    workspace tenant, pins the gate from the template's exact stage 10 asset
    package, and binds the designated approver to the workspace authority registry
    (``GateApproverAuthorityPolicy``). It is a pure domain service: it returns a
    gate and mutates nothing, invokes no persistence, and never invents a concrete
    approver identity or authority role (SPEC.md section 11).
    """

    def assemble(
        self,
        *,
        template: StageTemplate,
        workspace: ClientWorkspace,
        package: PerformanceBaselinePackage,
        approver: str,
        proposed_by: str | None = None,
    ) -> StageGate:
        if package.tenant_id != workspace.tenant_id:
            raise TenantBoundaryError(
                f"performance baseline package {package.package_id!r} belongs to "
                f"tenant {package.tenant_id!r}, not workspace tenant "
                f"{workspace.tenant_id!r}"
            )
        gate = StageGate.from_assets(
            template,
            STAGE_TEN,
            tenant_id=workspace.tenant_id,
            assets=package.stage_asset_versions(),
        )
        gate.approver = approver
        gate.proposed_by = proposed_by
        GateApproverAuthorityPolicy().require(gate, workspace)
        return gate


class StageTenGateRecorder:
    """Records the passing stage 10 "Performance Baseline Established" decision.

    SPEC.md section 4: a passing gate pins "the exact evidence and intended
    downstream use", approval is version specific, and the author cannot
    impersonate the approver. Given the gate ``StageTenGateAssembler`` already
    validated, this pure-domain path issues one version-specific
    ``ApprovalRequest`` per required asset on behalf of the gate's author, has the
    workspace's designated approver approve each one, records them on the gate,
    and stores the immutable ``GateDecision`` in the durable ``GateLedger``. It
    refuses a gate for another stage, an absent author or approver, an approver who
    holds no authority on the workspace, and an assigned work owner who holds no
    authority on the workspace, so the stage 10 rubric can never approve an
    unrelated asset package, a self-issued approval or an unaccountable owner
    (SPEC.md sections 3, 4, 5 and 11). Because stage 10 depends on stage 9,
    ``GateDecision.from_gate`` and ``GateLedger.record`` refuse a passing decision
    until the ledger holds a passing stage 9 decision, so a failed prerequisite
    blocks dependent authorization (SPEC.md section 4). It mutates only the gate it
    is given and the ledger; it never invents a concrete human identity.
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
        if gate.stage_number != STAGE_TEN:
            raise NotStageTenGateError(
                f"stage 10 recording path cannot record a decision for stage "
                f"{gate.stage_number}"
            )
        author = gate.proposed_by
        if not author or not author.strip():
            raise GateAuthorRequiredError(
                "stage 10 recording requires the gate's author so an approval "
                "request has a requester distinct from the designated approver"
            )
        GateApproverAuthorityPolicy().require(gate, workspace)
        GateOwnerAuthorityPolicy().require(assigned_owner, workspace)
        approver = gate.approver
        if not approver or not approver.strip():
            raise GateApproverNotAuthorizedError(
                "stage 10 recording requires the gate's designated approver"
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
                rationale=f"stage 10 asset {asset} approved for {scope}",
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
