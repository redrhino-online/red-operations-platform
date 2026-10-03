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

from typing import Any, Mapping

from redops.contexts.execution.domain.entities import FunnelIntegration
from redops.contexts.execution.domain.value_objects import (
    FunnelAssetPackage,
    FunnelState,
    HandoffKind,
    HandoffOutcome,
    HandoffRecord,
    ProspectPathDryRun,
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
