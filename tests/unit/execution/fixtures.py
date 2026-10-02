"""Shared pure-domain fixtures for Execution tests.

These build a stage 8 `FunnelIntegration` grounded on an approved stage 7
`AuthorityAmplifier`, a complete funnel asset package and a prospect path dry run
whose capture, engagement and conversion handoffs all route, so tests that
exercise the "Funnel Complete" checkpoint do not restate the same content in
every file. They are test data only and carry no behavior.
"""

from __future__ import annotations

from redops.contexts.execution.domain.entities import FunnelIntegration
from redops.contexts.execution.domain.value_objects import (
    HANDOFF_ORDER,
    FunnelAssetPackage,
    HandoffKind,
    HandoffOutcome,
    HandoffRecord,
    ProspectPathDryRun,
)

from ..production.fixtures import (
    TODAY,
    USE,
    script_approved_amplifier,
    visual_package,
)

TENANT = "client-3f"


def approved_amplifier(**overrides):
    return (
        script_approved_amplifier(**overrides)
        .produce_visuals(package=visual_package())
        .approve_creative(
            approved_by="client-authority", intended_use=USE, on=TODAY
        )
    )


def funnel_assets(**overrides) -> FunnelAssetPackage:
    values = {
        "campaign_architecture": "asset://funnel/architecture",
        "pages": "asset://funnel/pages",
        "forms": "asset://funnel/forms",
        "qualification": "asset://funnel/qualification",
        "booking": "asset://funnel/booking",
        "sequences": "asset://funnel/sequences",
        "crm": "asset://funnel/crm",
        "tags": "asset://funnel/tags",
        "automation": "asset://funnel/automation",
        "analytics": "asset://funnel/analytics",
        "tracking": "asset://funnel/tracking",
        "sales_handoff": "asset://funnel/sales-handoff",
        "sops": "asset://funnel/sops",
    }
    values.update(overrides)
    return FunnelAssetPackage(**values)


def handoff(
    kind: HandoffKind,
    *,
    outcome: HandoffOutcome = HandoffOutcome.ROUTED,
    tenant_id: str = TENANT,
    record_id: str = "record-1",
    owner: str = "funnel-owner",
    detail: str = "",
) -> HandoffRecord:
    return HandoffRecord(
        kind=kind,
        outcome=outcome,
        tenant_id=tenant_id,
        record_id=record_id,
        owner=owner,
        detail=detail,
    )


def dry_run(handoffs=None, **overrides) -> ProspectPathDryRun:
    values = {
        "dry_run_id": "dry-run-3f",
        "tenant_id": TENANT,
        "handoffs": (
            tuple(handoff(kind) for kind in HANDOFF_ORDER)
            if handoffs is None
            else handoffs
        ),
    }
    values.update(overrides)
    return ProspectPathDryRun(**values)


def funnel_integration(amplifier=None, **overrides) -> FunnelIntegration:
    values = {
        "integration_id": "funnel-3f",
        "tenant_id": TENANT,
        "amplifier": approved_amplifier() if amplifier is None else amplifier,
        "owner": "funnel-owner",
        "assets": funnel_assets(),
    }
    values.update(overrides)
    return FunnelIntegration(**values)


def complete_funnel(**overrides) -> FunnelIntegration:
    return funnel_integration(**overrides).mark_funnel_complete(dry_run())
