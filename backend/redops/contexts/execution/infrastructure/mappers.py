"""Map the Execution ``FunnelIntegration`` aggregate to and from a durable payload.

SPEC.md section 6 keeps mapping in the infrastructure layer: the domain must not
know about JSONB or table columns. The PostgreSQL adapter stores a completed
stage 8 ``FunnelIntegration`` as a JSONB payload plus a few indexed columns, and
rebuilds the aggregate on load by going through ``FunnelIntegration.__post_init__``
and ``mark_funnel_complete``. Serialising every authority-bearing field -- the
grounding stage 7 ``AuthorityAmplifier``, the thirteen canonical funnel asset
references, the pinned ``ProspectPathDryRun`` with each handoff record and owner,
and the funnel state -- is what lets a reloaded funnel re-validate rather than
trust what storage claims (SPEC.md sections 3 and 4: a passing gate pins the exact
approved asset versions and intended use, and a previous approved version stays
historically identifiable). A round trip that silently dropped the dry run or one
of the asset references would turn a stale or incomplete funnel back into a
completed one on reload.

The nested stage 7 amplifier is serialised with the Production context's own
mapper helper so the two contexts cannot drift on the shape of that shared asset.

Canon: not applicable. This is a persistence mapper for an execution aggregate,
not a method artifact, so no reference-model file informs its shape.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from redops.contexts.execution.domain.entities import (
    FunnelIntegration,
    LaunchQA,
)
from redops.contexts.execution.domain.value_objects import (
    ComplianceAsset,
    ComplianceAssetKind,
    CompliancePackage,
    ComplianceWaiver,
    FunnelAssetPackage,
    FunnelState,
    HandoffKind,
    HandoffOutcome,
    HandoffRecord,
    LaunchQAState,
    ProspectPathDryRun,
    QACheck,
    QACheckKind,
    QACheckOutcome,
    TrafficAuthorization,
)
from redops.contexts.production.infrastructure.mappers import (
    authority_amplifier_from_payload,
    authority_amplifier_to_payload,
)


def _assets_to_payload(assets: FunnelAssetPackage) -> dict[str, Any]:
    return {
        "campaign_architecture": assets.campaign_architecture,
        "pages": assets.pages,
        "forms": assets.forms,
        "qualification": assets.qualification,
        "booking": assets.booking,
        "sequences": assets.sequences,
        "crm": assets.crm,
        "tags": assets.tags,
        "automation": assets.automation,
        "analytics": assets.analytics,
        "tracking": assets.tracking,
        "sales_handoff": assets.sales_handoff,
        "sops": assets.sops,
    }


def _assets_from_payload(payload: Mapping[str, Any]) -> FunnelAssetPackage:
    return FunnelAssetPackage(
        campaign_architecture=str(payload["campaign_architecture"]),
        pages=str(payload["pages"]),
        forms=str(payload["forms"]),
        qualification=str(payload["qualification"]),
        booking=str(payload["booking"]),
        sequences=str(payload["sequences"]),
        crm=str(payload["crm"]),
        tags=str(payload["tags"]),
        automation=str(payload["automation"]),
        analytics=str(payload["analytics"]),
        tracking=str(payload["tracking"]),
        sales_handoff=str(payload["sales_handoff"]),
        sops=str(payload["sops"]),
    )


def _dry_run_to_payload(
    dry_run: ProspectPathDryRun | None,
) -> dict[str, Any] | None:
    if dry_run is None:
        return None
    return {
        "dry_run_id": dry_run.dry_run_id,
        "tenant_id": dry_run.tenant_id,
        "handoffs": [
            {
                "kind": record.kind.value,
                "outcome": record.outcome.value,
                "tenant_id": record.tenant_id,
                "record_id": record.record_id,
                "owner": record.owner,
                "detail": record.detail,
            }
            for record in dry_run.handoffs
        ],
    }


def _dry_run_from_payload(
    payload: Mapping[str, Any] | None,
) -> ProspectPathDryRun | None:
    if payload is None:
        return None
    return ProspectPathDryRun(
        dry_run_id=str(payload["dry_run_id"]),
        tenant_id=str(payload["tenant_id"]),
        handoffs=tuple(
            HandoffRecord(
                kind=HandoffKind(str(entry["kind"])),
                outcome=HandoffOutcome(str(entry["outcome"])),
                tenant_id=str(entry["tenant_id"]),
                record_id=str(entry["record_id"]),
                owner=str(entry["owner"]),
                detail=str(entry["detail"]),
            )
            for entry in payload["handoffs"]
        ),
    )


def funnel_integration_to_payload(funnel: FunnelIntegration) -> dict[str, Any]:
    """Serialise a completed funnel into the JSONB payload the table stores.

    The grounding amplifier is emitted through ``authority_amplifier_to_payload``
    so the funnel cannot drift from the amplifier shape, and all thirteen asset
    references keep their canonical field names. The optional dry run is emitted
    as ``None`` rather than dropped, so a reload cannot confuse an absent asset
    with a malformed one.
    """

    return {
        "integration_id": funnel.integration_id,
        "tenant_id": funnel.tenant_id,
        "amplifier": authority_amplifier_to_payload(funnel.amplifier),
        "owner": funnel.owner,
        "assets": _assets_to_payload(funnel.assets),
        "state": funnel.state.value,
        "dry_run": _dry_run_to_payload(funnel.dry_run),
        "review_reason": funnel.review_reason,
    }


def funnel_integration_from_payload(
    payload: Mapping[str, Any],
) -> FunnelIntegration:
    """Rebuild a funnel from a stored payload for re-validation.

    Construction re-runs the aggregate invariants, so a payload that storage
    cannot legally hold (a blank identity, a grounding amplifier from another
    tenant, a dry run from another tenant) raises here rather than being read back
    as a completed funnel.
    """

    return FunnelIntegration(
        integration_id=str(payload["integration_id"]),
        tenant_id=str(payload["tenant_id"]),
        amplifier=authority_amplifier_from_payload(payload["amplifier"]),
        owner=str(payload["owner"]),
        assets=_assets_from_payload(payload["assets"]),
        state=FunnelState(str(payload["state"])),
        dry_run=_dry_run_from_payload(payload.get("dry_run")),
        review_reason=payload.get("review_reason"),
    )


def _compliance_to_payload(compliance: CompliancePackage | None) -> dict[str, Any] | None:
    if compliance is None:
        return None
    return {
        "package_id": compliance.package_id,
        "tenant_id": compliance.tenant_id,
        "target_markets": list(compliance.target_markets),
        "assets": [
            {
                "kind": asset.kind.value,
                "tenant_id": asset.tenant_id,
                "reference": asset.reference,
                "version": asset.version,
            }
            for asset in compliance.assets
        ],
        "waivers": [
            {
                "kind": waiver.kind.value,
                "reason": waiver.reason,
                "risk_owner": waiver.risk_owner,
                "review_trigger": waiver.review_trigger,
                "expires_on": (
                    waiver.expires_on.isoformat()
                    if waiver.expires_on is not None
                    else None
                ),
            }
            for waiver in compliance.waivers
        ],
    }


def _compliance_from_payload(
    payload: Mapping[str, Any] | None,
) -> CompliancePackage | None:
    if payload is None:
        return None
    return CompliancePackage(
        package_id=str(payload["package_id"]),
        tenant_id=str(payload["tenant_id"]),
        target_markets=tuple(str(m) for m in payload["target_markets"]),
        assets=tuple(
            ComplianceAsset(
                kind=ComplianceAssetKind(str(entry["kind"])),
                tenant_id=str(entry["tenant_id"]),
                reference=str(entry["reference"]),
                version=int(entry["version"]),
            )
            for entry in payload["assets"]
        ),
        waivers=tuple(
            ComplianceWaiver(
                kind=ComplianceAssetKind(str(entry["kind"])),
                reason=str(entry["reason"]),
                risk_owner=str(entry["risk_owner"]),
                review_trigger=str(entry["review_trigger"]),
                expires_on=(
                    date.fromisoformat(str(entry["expires_on"]))
                    if entry.get("expires_on") is not None
                    else None
                ),
            )
            for entry in payload["waivers"]
        ),
    )


def _qa_checks_to_payload(checks: tuple[QACheck, ...]) -> list[dict[str, Any]]:
    return [
        {
            "kind": check.kind.value,
            "outcome": check.outcome.value,
            "evidence": check.evidence,
            "owner": check.owner,
            "detail": check.detail,
        }
        for check in checks
    ]


def _qa_checks_from_payload(
    payload: list[Mapping[str, Any]],
) -> tuple[QACheck, ...]:
    return tuple(
        QACheck(
            kind=QACheckKind(str(entry["kind"])),
            outcome=QACheckOutcome(str(entry["outcome"])),
            evidence=str(entry["evidence"]),
            owner=str(entry.get("owner", "")),
            detail=str(entry.get("detail", "")),
        )
        for entry in payload
    )


def _authorization_to_payload(
    authorization: TrafficAuthorization | None,
) -> dict[str, Any] | None:
    if authorization is None:
        return None
    return {
        "authorized_by": authorization.authorized_by,
        "intended_use": authorization.intended_use,
        "authorized_on": authorization.authorized_on.isoformat(),
    }


def _authorization_from_payload(
    payload: Mapping[str, Any] | None,
) -> TrafficAuthorization | None:
    if payload is None:
        return None
    return TrafficAuthorization(
        authorized_by=str(payload["authorized_by"]),
        intended_use=str(payload["intended_use"]),
        authorized_on=date.fromisoformat(str(payload["authorized_on"])),
    )


def launch_qa_to_payload(qa: LaunchQA) -> dict[str, Any]:
    """Serialise an authorized stage 9 launch QA into the JSONB payload.

    The grounding stage 8 ``FunnelIntegration`` is emitted through the funnel
    mapper and the compliance package keeps its own canonical field names, so the
    QA cannot drift from the shapes of the assets it pins. A reload re-validates
    through ``LaunchQA`` construction: a QA that storage cannot legally hold (a
    blank identity, a grounding funnel from another tenant, a ready QA with no
    compliance package) raises rather than being read back as authorized.
    """

    return {
        "qa_id": qa.qa_id,
        "tenant_id": qa.tenant_id,
        "funnel": funnel_integration_to_payload(qa.funnel),
        "owner": qa.owner,
        "designated_authority": qa.designated_authority,
        "checks": _qa_checks_to_payload(qa.checks),
        "state": qa.state.value,
        "authorization": _authorization_to_payload(qa.authorization),
        "compliance": _compliance_to_payload(qa.compliance),
        "review_reason": qa.review_reason,
    }


def launch_qa_from_payload(payload: Mapping[str, Any]) -> LaunchQA:
    """Rebuild a launch QA from a stored payload for re-validation."""

    return LaunchQA(
        qa_id=str(payload["qa_id"]),
        tenant_id=str(payload["tenant_id"]),
        funnel=funnel_integration_from_payload(payload["funnel"]),
        owner=str(payload["owner"]),
        designated_authority=str(payload["designated_authority"]),
        checks=_qa_checks_from_payload(payload["checks"]),
        state=LaunchQAState(str(payload["state"])),
        authorization=_authorization_from_payload(payload.get("authorization")),
        compliance=_compliance_from_payload(payload.get("compliance")),
        review_reason=payload.get("review_reason"),
    )
