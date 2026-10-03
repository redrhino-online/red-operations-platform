"""RED HTTP routes.

These routes are thin adapters. The stages route exposes the canonical 0-10
production template as read-only reference data from the pure Governance domain
(`stage_zero_to_ten_template`, SPEC.md section 4); it computes no domain rule,
holds no state and mutates nothing. Gate integrity, approval authority and
tenant scoping stay in the domain and application layers where they are
enforced and tested.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from redops.api.schemas import (
    EngagementProductionViewResponse,
    RecordStageFourGateRequest,
    RecordStageOneGateRequest,
    RecordStageThreeGateRequest,
    RecordStageTwoGateRequest,
    RecordStageZeroGateRequest,
)
from redops.contexts.commercial.domain.errors import CommercialError
from redops.contexts.commercial.domain.value_objects import (
    AvatarProfile,
    BusinessSnapshot,
    CurrencyInventory,
    CurrencyPackage,
    DiagnosisPackage,
    DiagnosticPackage,
    MillionDollarMessage,
    OfferFunnelAudit,
    PositioningDecision,
    SignaturePackage,
)
from redops.contexts.engagement.application.commands import (
    RecordStageFourGateCommand,
    RecordStageOneGateCommand,
    RecordStageThreeGateCommand,
    RecordStageTwoGateCommand,
    RecordStageZeroGateCommand,
)
from redops.contexts.engagement.application.handlers import (
    RecordStageFourGateHandler,
    RecordStageOneGateHandler,
    RecordStageThreeGateHandler,
    RecordStageTwoGateHandler,
    RecordStageZeroGateHandler,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import EngagementError
from redops.contexts.engagement.domain.value_objects import (
    ClientAuthority,
    IntakeAsset,
    IntakeAssetKind,
    IntakePackage,
)
from redops.contexts.governance.application.ports import (
    GateLedgerRepository,
    StageRunRepository,
)
from redops.contexts.governance.application.queries import (
    EngagementProductionViewQuery,
    GetEngagementProductionViewHandler,
)
from redops.contexts.governance.domain.entities import StageRun
from redops.contexts.governance.domain.errors import GovernanceError
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    EngagementProductionView,
    MetricReportingView,
    StageProductionView,
)
from redops.contexts.governance.infrastructure.repositories import (
    gate_ledger_repository_from_env,
    stage_run_repository_from_env,
)
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.errors import KnowledgeError
from redops.contexts.knowledge.domain.value_objects import (
    ProvenanceClass,
    SourceCitation,
)
from redops.contexts.method.domain.entities import (
    DiagnosticModel,
    SignatureSolution,
)
from redops.contexts.method.domain.errors import MethodError
from redops.contexts.method.domain.value_objects import (
    PrimaryCurrency,
    ProfitPyramidLevel,
    SignatureStep,
    TransformationPhase,
)

router = APIRouter(prefix="/red", tags=["red"])

# The adapter is selected from configuration through an overridable dependency
# so the API is wired to the ``GateLedgerRepository`` port, not to a concrete
# store. ADR 0003 gives RED durable gate records: when ``DATABASE_URL`` is set
# the process serving traffic records into PostgreSQL, and without it (local
# development, the domain-only test interpreter) the process-local reference
# adapter stands in.
def get_gate_ledger_repository() -> Iterator[GateLedgerRepository]:
    """Provide the configured gate ledger seam to the API (SPEC.md section 6).

    The dependency owns one adapter for the request and releases any connection
    it opened when the request ends, so a durable write is committed per gate
    (SPEC.md sections 3 and 4). The store is chosen once from ``DATABASE_URL``;
    a request cannot silently downgrade to the process-local ledger, because a
    set-but-unusable configuration raises before the route runs.
    """

    repository = gate_ledger_repository_from_env(os.environ.get("DATABASE_URL"))
    try:
        yield repository
    finally:
        repository.close()


def get_stage_run_repository() -> Iterator[StageRunRepository]:
    """Provide the configured stage run seam to the API (SPEC.md section 6).

    The dependency owns one adapter for the request and releases any connection
    it opened when the request ends. The store is chosen once from
    ``DATABASE_URL``; a set-but-unusable configuration raises before the route
    runs, so a deployment cannot mistake a process-local stage run store for a
    durable one (SPEC.md sections 3 and 4).
    """

    repository = stage_run_repository_from_env(os.environ.get("DATABASE_URL"))
    try:
        yield repository
    finally:
        repository.close()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for the RED app."""

    return {"status": "ok"}


@router.get("/stages")
def stages() -> list[dict[str, Any]]:
    """Return the canonical stages 0-10 and their checkpoints.

    The template is data: it names roles, not people, and confers no authority.
    """

    template = stage_zero_to_ten_template()
    return [
        {
            "stage_number": stage.stage_number,
            "name": stage.name,
            "checkpoint": stage.checkpoint,
            "required_asset_kinds": sorted(stage.required_asset_kinds),
            "accountable_role": stage.accountable_role,
            "approver_role": stage.approver_role,
            "dependencies": sorted(stage.dependencies),
        }
        for stage in template.stages
    ]


@router.post("/clients/{tenant_id}/stages/0/gate", status_code=201)
def record_stage_zero_gate(
    tenant_id: str,
    body: RecordStageZeroGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
) -> dict[str, Any]:
    """Record the stage 0 "Production Ready" gate through the use case seam.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageZeroGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageZeroGateHandler`` and
    appends the resulting ``GateDecision``. The response reports the pinned
    decision (exact asset versions, reviewer, disposition) the gate authorized
    downstream use with. The stage 0 ``StageRun`` is loaded-or-created and
    upserted through the ``StageRunRepository`` port in the same operation, so
    the stage's assigned owner, status, entered/exited timestamps and transition
    log are durable alongside the decision, not synthesised per request.
    Every integrity rule -- canonical kinds, exact versions,
    owner/approver authority, sourced evidence and the tenant boundary -- is
    enforced by the domain; a rejection is a named 422 and never a partial write
    (SPEC.md sections 3, 4, 9 and 11). The path tenant, not the body, is the
    authoritative client scope for the ledger.
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = ClientWorkspace(
            workspace_id=body.workspace_id,
            tenant_id=tenant_id,
            authorities=tuple(
                ClientAuthority(actor=entry.actor, authority=entry.authority)
                for entry in body.authorities
            ),
        )
        claims = tuple(
            Claim(
                claim_id=item.claim_id,
                tenant_id=tenant_id,
                statement=item.statement,
                provenance=ProvenanceClass(item.provenance),
                citations=frozenset(
                    SourceCitation(
                        source_id=citation.source_id,
                        checksum=citation.checksum,
                        location=citation.location,
                    )
                    for citation in item.citations
                ),
                confidence_note=item.confidence_note,
            )
            for item in body.claims
        )
        package = IntakePackage(
            package_id=body.intake_package_id,
            tenant_id=tenant_id,
            assets=tuple(
                IntakeAsset(
                    asset_id=asset.asset_id,
                    tenant_id=tenant_id,
                    kind=IntakeAssetKind(asset.kind),
                    version=asset.version,
                    owner=asset.owner,
                    summary=asset.summary,
                    evidence_claim_ids=tuple(asset.evidence_claim_ids),
                )
                for asset in body.assets
            ),
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 0, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=0,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 0 intake work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageZeroGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            claims=claims,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageZeroGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except (EngagementError, GovernanceError, KnowledgeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.post("/clients/{tenant_id}/stages/1/gate", status_code=201)
def record_stage_one_gate(
    tenant_id: str,
    body: RecordStageOneGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
) -> dict[str, Any]:
    """Record the stage 1 "Avatar Locked" gate through the use case seam.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageOneGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageOneGateHandler`` and appends
    the resulting ``GateDecision``. Stage 1 depends on stage 0, so governance
    refuses the decision unless the ledger already holds a passing stage 0
    decision (SPEC.md section 4). The stage 1 ``StageRun`` is loaded-or-created
    and upserted through the ``StageRunRepository`` port in the same operation,
    so its assigned owner, status and timestamps stay durable alongside the
    decision. Every integrity rule -- canonical kinds, exact versions,
    owner/approver authority, sourced evidence and the tenant boundary -- is
    enforced by the domain; a rejection is a named 422 and never a partial write.
    The path tenant, not the body, is the authoritative client scope.
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = ClientWorkspace(
            workspace_id=body.workspace_id,
            tenant_id=tenant_id,
            authorities=tuple(
                ClientAuthority(actor=entry.actor, authority=entry.authority)
                for entry in body.authorities
            ),
        )
        claims = tuple(
            Claim(
                claim_id=item.claim_id,
                tenant_id=tenant_id,
                statement=item.statement,
                provenance=ProvenanceClass(item.provenance),
                citations=frozenset(
                    SourceCitation(
                        source_id=citation.source_id,
                        checksum=citation.checksum,
                        location=citation.location,
                    )
                    for citation in item.citations
                ),
                confidence_note=item.confidence_note,
            )
            for item in body.claims
        )
        package = DiagnosisPackage(
            package_id=body.diagnosis_package_id,
            tenant_id=tenant_id,
            avatar=AvatarProfile(
                avatar_id=body.avatar.avatar_id,
                tenant_id=tenant_id,
                name=body.avatar.name,
                demographics=body.avatar.demographics,
                psychographics=body.avatar.psychographics,
                pains=tuple(body.avatar.pains),
                goals=tuple(body.avatar.goals),
                consequences_of_inaction=tuple(
                    body.avatar.consequences_of_inaction
                ),
                awareness=body.avatar.awareness,
                customer_evidence_claim_ids=tuple(
                    body.avatar.customer_evidence_claim_ids
                ),
                voice_notes=tuple(body.avatar.voice_notes),
            ),
            avatar_version=body.avatar.version,
            business_snapshot=BusinessSnapshot(
                snapshot_id=body.business_snapshot.snapshot_id,
                tenant_id=tenant_id,
                business_model=body.business_snapshot.business_model,
                current_offers=tuple(body.business_snapshot.current_offers),
                lead_sources=tuple(body.business_snapshot.lead_sources),
                constraints=tuple(body.business_snapshot.constraints),
                narrative=body.business_snapshot.narrative,
                evidence_claim_ids=tuple(body.business_snapshot.evidence_claim_ids),
            ),
            business_snapshot_version=body.business_snapshot.version,
            offer_funnel_audit=OfferFunnelAudit(
                audit_id=body.offer_funnel_audit.audit_id,
                tenant_id=tenant_id,
                offer_findings=tuple(body.offer_funnel_audit.offer_findings),
                funnel_steps=tuple(body.offer_funnel_audit.funnel_steps),
                conversion_evidence=tuple(
                    body.offer_funnel_audit.conversion_evidence
                ),
                gaps=tuple(body.offer_funnel_audit.gaps),
                narrative=body.offer_funnel_audit.narrative,
                evidence_claim_ids=tuple(
                    body.offer_funnel_audit.evidence_claim_ids
                ),
            ),
            offer_funnel_audit_version=body.offer_funnel_audit.version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 1, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=1,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 1 diagnosis work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageOneGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            claims=claims,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageOneGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except (
        CommercialError,
        EngagementError,
        GovernanceError,
        KnowledgeError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


def _metric_reporting_payload(row: MetricReportingView) -> dict[str, Any]:
    movement = None
    if row.movement is not None:
        movement = {
            "improvement_id": row.movement.improvement_id,
            "before": row.movement.before,
            "after": row.movement.after,
            "measured_on": row.movement.measured_on.isoformat(),
        }
    return {
        "metric_id": row.metric_id,
        "tenant_id": row.tenant_id,
        "name": row.name,
        "funnel_step": row.funnel_step,
        "unit": row.unit,
        "direction": row.direction,
        "value": row.value,
        "window_start": row.window_start.isoformat(),
        "window_end": row.window_end.isoformat(),
        "sample_size": row.sample_size,
        "source": row.source,
        "recorded_on": row.recorded_on.isoformat(),
        "basis": row.basis.value,
        "movement": movement,
    }


def _stage_production_view_payload(stage: StageProductionView) -> dict[str, Any]:
    return {
        "stage_number": stage.stage_number,
        "name": stage.name,
        "checkpoint": stage.checkpoint,
        "status": stage.status.value,
        "required_asset_kinds": sorted(stage.required_asset_kinds),
        "approved_assets": sorted(
            (
                {"asset_id": asset.asset_id, "version": asset.version}
                for asset in stage.approved_assets
            ),
            key=lambda asset: (asset["asset_id"], asset["version"]),
        ),
        "missing_asset_kinds": sorted(stage.missing_asset_kinds),
        "accountable_role": stage.accountable_role,
        "approver_role": stage.approver_role,
        "dependencies": sorted(stage.dependencies),
        "blocking_dependencies": sorted(stage.blocking_dependencies),
        "assigned_owner": stage.assigned_owner,
        "recorded_approver": stage.recorded_approver,
        "due_on": stage.due_on.isoformat() if stage.due_on else None,
        "next_action": stage.next_action,
        "blockers": sorted(stage.blockers),
        "entered_at": stage.entered_at.isoformat() if stage.entered_at else None,
        "is_approved": stage.is_approved,
    }


def _production_view_payload(view: EngagementProductionView) -> dict[str, Any]:
    current = view.current_stage
    next_approval = view.next_approval
    return {
        "engagement": view.engagement,
        "tenant_id": view.tenant_id,
        "template_version": view.template_version,
        "current_stage_number": current.stage_number if current else None,
        "next_approval_stage_number": (
            next_approval.stage_number if next_approval else None
        ),
        "blocked_stage_numbers": [
            stage.stage_number for stage in view.blocked_stages
        ],
        "progress": {
            "approved_gates": view.progress.approved_gates,
            "total_gates": view.progress.total_gates,
            "verified_post_launch_milestones": (
                view.progress.verified_post_launch_milestones
            ),
            "activity_entries": view.progress.activity_entries,
            "verified_progress": view.progress.verified_progress,
            "gates_remaining": view.progress.gates_remaining,
        },
        "stages": [
            _stage_production_view_payload(stage) for stage in view.stages
        ],
        "metric_reporting": [
            _metric_reporting_payload(row) for row in view.metric_reporting
        ],
    }


@router.post("/clients/{tenant_id}/stages/2/gate", status_code=201)
def record_stage_two_gate(
    tenant_id: str,
    body: RecordStageTwoGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
) -> dict[str, Any]:
    """Record the stage 2 "Currency Locked" gate through the use case seam.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageTwoGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageTwoGateHandler`` and appends
    the resulting ``GateDecision``. Stage 2 depends on stage 1, so governance
    refuses the decision unless the ledger already holds a passing stage 1
    decision (SPEC.md section 4). The stage 2 ``StageRun`` is loaded-or-created
    and upserted through the ``StageRunRepository`` port in the same operation,
    so its assigned owner, status and timestamps stay durable alongside the
    decision. Every integrity rule -- canonical kinds, exact versions,
    owner/approver authority, the primary currency's internal specificity and
    the tenant boundary -- is enforced by the domain; a rejection is a named 422
    and never a partial write. The path tenant, not the body, is the
    authoritative client scope. Stage 2 carries no claims: the checkpoint turns
    on the locked currency, not on external customer evidence.
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = ClientWorkspace(
            workspace_id=body.workspace_id,
            tenant_id=tenant_id,
            authorities=tuple(
                ClientAuthority(actor=entry.actor, authority=entry.authority)
                for entry in body.authorities
            ),
        )
        package = CurrencyPackage(
            package_id=body.currency_package_id,
            tenant_id=tenant_id,
            inventory=CurrencyInventory(
                inventory_id=body.inventory.inventory_id,
                tenant_id=tenant_id,
                category=body.inventory.category,
                currencies_to_increase=tuple(
                    body.inventory.currencies_to_increase
                ),
                currencies_to_decrease=tuple(
                    body.inventory.currencies_to_decrease
                ),
            ),
            inventory_version=body.inventory.version,
            positioning=PositioningDecision(
                decision_id=body.positioning.decision_id,
                tenant_id=tenant_id,
                core_problem=body.positioning.core_problem,
                transformation_statement=(
                    body.positioning.transformation_statement
                ),
                horizon=body.positioning.horizon,
                qualifications=tuple(body.positioning.qualifications),
                disqualifications=tuple(body.positioning.disqualifications),
            ),
            positioning_version=body.positioning.version,
            primary_currency=PrimaryCurrency(
                tenant_id=tenant_id,
                currency=body.primary_currency.currency,
                audience=body.primary_currency.audience,
                current_measure=body.primary_currency.current_measure,
                desired_measure=body.primary_currency.desired_measure,
                mechanism=body.primary_currency.mechanism,
            ),
            primary_currency_version=body.primary_currency.version,
            million_dollar_message=MillionDollarMessage(
                message_id=body.million_dollar_message.message_id,
                tenant_id=tenant_id,
                avatar=body.million_dollar_message.avatar,
                currency=body.million_dollar_message.currency,
                metric=body.million_dollar_message.metric,
                timeline=body.million_dollar_message.timeline,
                pain=body.million_dollar_message.pain,
                message=body.million_dollar_message.message,
            ),
            million_dollar_message_version=body.million_dollar_message.version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 2, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=2,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 2 positioning work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageTwoGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageTwoGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except (
        CommercialError,
        EngagementError,
        GovernanceError,
        MethodError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.post("/clients/{tenant_id}/stages/3/gate", status_code=201)
def record_stage_three_gate(
    tenant_id: str,
    body: RecordStageThreeGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
) -> dict[str, Any]:
    """Record the stage 3 "Diagnostic Model Approved" gate through the use case.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageThreeGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageThreeGateHandler`` and
    appends the resulting ``GateDecision``. Stage 3 depends on stage 2, so
    governance refuses the decision unless the ledger already holds a passing
    stage 2 decision (SPEC.md section 4). The stage 3 ``StageRun`` is
    loaded-or-created and upserted through the ``StageRunRepository`` port in the
    same operation, so its assigned owner, status and timestamps stay durable
    alongside the decision. Every integrity rule -- canonical kinds, exact
    versions, owner/approver authority, adjacent-level observable
    distinguishability and the tenant boundary -- is enforced by the domain; a
    rejection is a named 422 and never a partial write. The path tenant, not the
    body, is the authoritative client scope. Stage 3 carries no claims: the
    checkpoint turns on the model's own observable differences, not external
    customer evidence.
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = ClientWorkspace(
            workspace_id=body.workspace_id,
            tenant_id=tenant_id,
            authorities=tuple(
                ClientAuthority(actor=entry.actor, authority=entry.authority)
                for entry in body.authorities
            ),
        )
        package = DiagnosticPackage(
            package_id=body.diagnostic_package_id,
            tenant_id=tenant_id,
            model=DiagnosticModel(
                model_id=body.model.model_id,
                tenant_id=tenant_id,
                name=body.model.name,
                levels=tuple(
                    ProfitPyramidLevel(
                        level_id=level.level_id,
                        tenant_id=tenant_id,
                        name=level.name,
                        observable_measures=tuple(level.observable_measures),
                        symptoms=tuple(level.symptoms),
                        behaviors=tuple(level.behaviors),
                        problems=tuple(level.problems),
                    )
                    for level in body.model.levels
                ),
                progression=body.model.progression,
                qualification_logic=body.model.qualification_logic,
                visual=body.model.visual,
                explanatory_copy=body.model.explanatory_copy,
            ),
            model_version=body.model.version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 3, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=3,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 3 diagnostic modeling work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageThreeGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageThreeGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except (
        CommercialError,
        EngagementError,
        GovernanceError,
        MethodError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.post("/clients/{tenant_id}/stages/4/gate", status_code=201)
def record_stage_four_gate(
    tenant_id: str,
    body: RecordStageFourGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
) -> dict[str, Any]:
    """Record the stage 4 "IP Architecture Locked" gate through the use case.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageFourGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageFourGateHandler`` and
    appends the resulting ``GateDecision``. Stage 4 depends on stage 3, so
    governance refuses the decision unless the ledger already holds a passing
    stage 3 decision (SPEC.md section 4). The stage 4 ``StageRun`` is
    loaded-or-created and upserted through the ``StageRunRepository`` port in the
    same operation, so its assigned owner, status and timestamps stay durable
    alongside the decision. Every integrity rule -- canonical kinds, exact
    versions, owner/approver authority, the three phase/nine step shape, the
    continuity of the named stages from the declared starting to final state and
    the tenant boundary -- is enforced by the domain; a rejection is a named 422
    and never a partial write. The path tenant, not the body, is the authoritative
    client scope. Stage 4 carries no claims: the checkpoint turns on the coherence
    and continuity of the reviewed transformation, not external customer evidence.
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = ClientWorkspace(
            workspace_id=body.workspace_id,
            tenant_id=tenant_id,
            authorities=tuple(
                ClientAuthority(actor=entry.actor, authority=entry.authority)
                for entry in body.authorities
            ),
        )
        package = SignaturePackage(
            package_id=body.signature_package_id,
            tenant_id=tenant_id,
            solution=SignatureSolution(
                solution_id=body.solution.solution_id,
                tenant_id=tenant_id,
                transformation_map=body.solution.transformation_map,
                process_inventory=tuple(body.solution.process_inventory),
                phases=tuple(
                    TransformationPhase(
                        phase_id=phase.phase_id,
                        tenant_id=tenant_id,
                        name=phase.name,
                        steps=tuple(
                            SignatureStep(
                                step_id=step.step_id,
                                tenant_id=tenant_id,
                                name=step.name,
                                starting_state=step.starting_state,
                                final_state=step.final_state,
                                inputs=tuple(step.inputs),
                                actions=tuple(step.actions),
                                outputs=tuple(step.outputs),
                            )
                            for step in phase.steps
                        ),
                    )
                    for phase in body.solution.phases
                ),
                starting_state=body.solution.starting_state,
                final_state=body.solution.final_state,
                narrative=body.solution.narrative,
                visual=body.solution.visual,
            ),
            solution_version=body.solution.version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 4, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=4,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 4 IP packaging work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageFourGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageFourGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except (
        CommercialError,
        EngagementError,
        GovernanceError,
        MethodError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.get(
    "/clients/{tenant_id}/engagements/{engagement}/production-view",
    response_model=EngagementProductionViewResponse,
)
def get_engagement_production_view(
    tenant_id: str,
    engagement: str,
    on: date,
    verified_post_launch_milestones: int = 0,
    activity_entries: int = 0,
    ledger_repository: GateLedgerRepository = Depends(
        get_gate_ledger_repository
    ),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
) -> EngagementProductionViewResponse:
    """Serve the production-manager view for one client engagement.

    SPEC.md section 4 requires the production view to answer, per client, the
    current stage, what should exist, what is present and approved, what is
    missing, who is accountable, which dependency blocks work, what approval is
    next and when it is due, and SPEC.md section 6 requires the API to call a use
    case through ports rather than read a store directly. This route maps the
    request to the Governance ``EngagementProductionViewQuery``, runs
    ``GetEngagementProductionViewHandler`` through the ``GateLedgerRepository``
    and ``StageRunRepository`` seams and returns the projected view. Every
    integrity rule -- the tenant boundary, the stage dependency graph, exact
    pinned versions and the separation of activity from verified progress -- stays
    enforced by the pure domain view; the route computes none of it. The
    evaluation instant ``on`` is required because a prerequisite's expiry is only
    meaningful against a fixed time (SPEC.md section 4).
    """

    query = EngagementProductionViewQuery(
        template=stage_zero_to_ten_template(),
        engagement=engagement,
        tenant_id=tenant_id,
        on=on,
        verified_post_launch_milestones=verified_post_launch_milestones,
        activity_entries=activity_entries,
    )
    try:
        view = GetEngagementProductionViewHandler(
            ledger_repository=ledger_repository,
            run_repository=run_repository,
        ).handle(query)
    except (GovernanceError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return _production_view_payload(view)
