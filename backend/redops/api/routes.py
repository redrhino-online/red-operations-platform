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
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from redops.api.schemas import RecordStageZeroGateRequest
from redops.contexts.engagement.application.commands import (
    RecordStageZeroGateCommand,
)
from redops.contexts.engagement.application.handlers import (
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
from redops.contexts.governance.domain.entities import StageRun
from redops.contexts.governance.domain.errors import GovernanceError
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
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
