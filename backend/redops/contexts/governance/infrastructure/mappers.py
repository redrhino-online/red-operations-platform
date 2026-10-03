"""Map the Governance ``GateDecision`` aggregate to and from a durable payload.

SPEC.md section 6 keeps mapping in the infrastructure layer: the domain must not
know about JSONB or table columns. The PostgreSQL adapter stores a
``GateDecision`` as a JSONB payload plus a few indexed columns, and rebuilds the
aggregate on load by going through ``GateDecision.__post_init__`` and
``GateLedger.record``. Serialising every field that carries authority — the
exact required asset versions, the per-asset ``ApprovalRequest`` outcomes, a
waiver, the prerequisites, the blockers and the tenant — is what lets a reloaded
ledger re-validate rather than trust what storage claims (SPEC.md section 4:
a passing gate pins the exact evidence and intended downstream use; section 3:
history is append-only). A round trip that silently dropped such a field would
turn an unapproved or expired decision back into an approved one on reload.

Canon: not applicable. This is a persistence mapper for a governance aggregate,
not a method artifact, so no reference-model file informs its shape.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    StageRun,
)
from redops.contexts.governance.domain.value_objects import (
    ApprovalOutcome,
    AssetVersionRef,
    GateDisposition,
    StageStatus,
    StageTransition,
    Waiver,
)


def _date_to_text(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _date_from_text(value: Any) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(str(value))


def _asset_to_payload(asset: AssetVersionRef) -> dict[str, Any]:
    return {"asset_id": asset.asset_id, "version": asset.version}


def _asset_from_payload(payload: Mapping[str, Any]) -> AssetVersionRef:
    return AssetVersionRef(
        asset_id=str(payload["asset_id"]), version=int(payload["version"])
    )


def _approval_to_payload(approval: ApprovalRequest) -> dict[str, Any]:
    return {
        "asset": _asset_to_payload(approval.asset),
        "scope": approval.scope,
        "requested_by": approval.requested_by,
        "approver": approval.approver,
        "outcome": approval.outcome.value,
        "expires_on": _date_to_text(approval.expires_on),
    }


def _approval_from_payload(payload: Mapping[str, Any]) -> ApprovalRequest:
    return ApprovalRequest(
        asset=_asset_from_payload(payload["asset"]),
        scope=str(payload["scope"]),
        requested_by=str(payload["requested_by"]),
        approver=str(payload["approver"]),
        outcome=ApprovalOutcome(str(payload["outcome"])),
        expires_on=_date_from_text(payload.get("expires_on")),
    )


def _waiver_to_payload(waiver: Waiver | None) -> dict[str, Any] | None:
    if waiver is None:
        return None
    return {
        "reason": waiver.reason,
        "risk_owner": waiver.risk_owner,
        "downstream_effects": sorted(waiver.downstream_effects),
        "review_trigger": waiver.review_trigger,
        "expires_on": _date_to_text(waiver.expires_on),
    }


def _waiver_from_payload(
    payload: Mapping[str, Any] | None,
) -> Waiver | None:
    if payload is None:
        return None
    return Waiver(
        reason=str(payload["reason"]),
        risk_owner=str(payload["risk_owner"]),
        downstream_effects=frozenset(
            str(effect) for effect in payload.get("downstream_effects", ())
        ),
        review_trigger=str(payload.get("review_trigger", "")),
        expires_on=_date_from_text(payload.get("expires_on")),
    )


def decision_to_payload(decision: GateDecision) -> dict[str, Any]:
    """Serialise a decision into the JSONB payload the table stores.

    Required assets and dependencies are emitted in a stable sorted order so the
    payload is deterministic; the domain treats both as sets, so order carries
    no meaning and a round trip must not depend on insertion order.
    """
    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "required_assets": [
            _asset_to_payload(asset)
            for asset in sorted(
                decision.required_assets, key=lambda a: (a.asset_id, a.version)
            )
        ],
        "checkpoint": decision.checkpoint,
        "checkpoint_evidence": decision.checkpoint_evidence,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "disposition": decision.disposition.value,
        "rationale": decision.rationale,
        "decided_on": decision.decided_on.isoformat(),
        "assigned_owner": decision.assigned_owner,
        "due_on": decision.due_on.isoformat(),
        "dependencies": sorted(decision.dependencies),
        "next_action": decision.next_action,
        "waiver": _waiver_to_payload(decision.waiver),
        "asset_approvals": [
            _approval_to_payload(approval)
            for approval in decision.asset_approvals
        ],
        "blockers": sorted(decision.blockers),
        "tenant_id": decision.tenant_id,
    }


def decision_from_payload(payload: Mapping[str, Any]) -> GateDecision:
    """Rebuild a decision from a stored payload for re-validation.

    Construction re-runs the aggregate invariants. A payload that storage
    cannot legally hold (a missing field, an unknown disposition, a versionless
    asset) raises here rather than being read back as an approved gate.
    """
    return GateDecision(
        stage_number=int(payload["stage_number"]),
        template_version=str(payload["template_version"]),
        required_assets=frozenset(
            _asset_from_payload(asset) for asset in payload["required_assets"]
        ),
        checkpoint=str(payload["checkpoint"]),
        checkpoint_evidence=str(payload.get("checkpoint_evidence", "")),
        reviewer=str(payload["reviewer"]),
        scope=str(payload["scope"]),
        disposition=GateDisposition(str(payload["disposition"])),
        rationale=str(payload["rationale"]),
        decided_on=date.fromisoformat(str(payload["decided_on"])),
        assigned_owner=str(payload["assigned_owner"]),
        due_on=date.fromisoformat(str(payload["due_on"])),
        dependencies=frozenset(
            int(stage) for stage in payload.get("dependencies", ())
        ),
        next_action=str(payload.get("next_action", "")),
        waiver=_waiver_from_payload(payload.get("waiver")),
        asset_approvals=tuple(
            _approval_from_payload(approval)
            for approval in payload.get("asset_approvals", ())
        ),
        blockers=frozenset(
            str(blocker) for blocker in payload.get("blockers", ())
        ),
        tenant_id=str(payload.get("tenant_id", "")),
    )


def _transition_to_payload(transition: StageTransition) -> dict[str, Any]:
    return {
        "actor": transition.actor,
        "reason": transition.reason,
        "occurred_at": transition.occurred_at.isoformat(),
        "old_status": transition.old_status.value,
        "new_status": transition.new_status.value,
        "correlation_id": transition.correlation_id,
    }


def _transition_from_payload(payload: Mapping[str, Any]) -> StageTransition:
    return StageTransition(
        actor=str(payload["actor"]),
        reason=str(payload["reason"]),
        occurred_at=date.fromisoformat(str(payload["occurred_at"])),
        old_status=StageStatus(str(payload["old_status"])),
        new_status=StageStatus(str(payload["new_status"])),
        correlation_id=str(payload["correlation_id"]),
    )


def stage_run_to_payload(run: StageRun) -> dict[str, Any]:
    """Serialise a ``StageRun`` into the JSONB payload the table stores.

    Every authority- and progress-bearing field is emitted -- the assigned
    owner, status, entered and exited timestamps, the exact accepted or waived
    ``GateDecision`` the stage completed on, and the full transition log -- so a
    reloaded run reports the same verified progress and audit history rather
    than a synthesised placeholder (SPEC.md sections 3 and 4). The nested
    decisions reuse ``decision_to_payload``, so a run cannot round-trip a laxer
    decision than the ledger stores.
    """
    return {
        "engagement": run.engagement,
        "stage_number": run.stage_number,
        "template_version": run.template_version,
        "assigned_owner": run.assigned_owner,
        "tenant_id": run.tenant_id,
        "status": run.status.value,
        "entered_at": _date_to_text(run.entered_at),
        "exited_at": _date_to_text(run.exited_at),
        "accepted_decision": (
            decision_to_payload(run.accepted_decision)
            if run.accepted_decision is not None
            else None
        ),
        "waiver_decision": (
            decision_to_payload(run.waiver_decision)
            if run.waiver_decision is not None
            else None
        ),
        "transitions": [
            _transition_to_payload(transition) for transition in run.transitions
        ],
    }


def stage_run_from_payload(payload: Mapping[str, Any]) -> StageRun:
    """Rebuild a ``StageRun`` from a stored payload.

    Construction re-runs the aggregate invariants and the persisted transition
    log is restored through ``restore_history`` so the audit history is not
    replayed through the state machine. A payload storage cannot legally hold
    (a blank owner, an unknown status, a versionless nested decision) raises
    here rather than being read back as a completed stage.
    """
    accepted = payload.get("accepted_decision")
    waiver = payload.get("waiver_decision")
    run = StageRun(
        engagement=str(payload["engagement"]),
        stage_number=int(payload["stage_number"]),
        template_version=str(payload["template_version"]),
        assigned_owner=str(payload["assigned_owner"]),
        tenant_id=str(payload.get("tenant_id", "")),
        status=StageStatus(str(payload["status"])),
        entered_at=_date_from_text(payload.get("entered_at")),
        exited_at=_date_from_text(payload.get("exited_at")),
        accepted_decision=(
            decision_from_payload(accepted) if accepted is not None else None
        ),
        waiver_decision=(
            decision_from_payload(waiver) if waiver is not None else None
        ),
    )
    run.restore_history(
        tuple(
            _transition_from_payload(transition)
            for transition in payload.get("transitions", ())
        )
    )
    return run
