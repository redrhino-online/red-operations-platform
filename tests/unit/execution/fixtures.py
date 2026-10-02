"""Shared pure-domain fixtures for Execution tests.

These build a stage 8 `FunnelIntegration` grounded on an approved stage 7
`AuthorityAmplifier`, a complete funnel asset package and a prospect path dry run
whose capture, engagement and conversion handoffs all route, so tests that
exercise the "Funnel Complete" checkpoint do not restate the same content in
every file. They are test data only and carry no behavior.
"""

from __future__ import annotations

from redops.contexts.execution.domain.entities import (
    FunnelIntegration,
    LaunchQA,
)
from redops.contexts.execution.domain.value_objects import (
    HANDOFF_ORDER,
    QA_CHECK_ORDER,
    FunnelAssetPackage,
    HandoffKind,
    HandoffOutcome,
    HandoffRecord,
    ProspectPathDryRun,
    QACheck,
    QACheckKind,
    QACheckOutcome,
    TrafficAuthorization,
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


def launch_check(
    kind: QACheckKind,
    *,
    outcome: QACheckOutcome = QACheckOutcome.PASSED,
    evidence: str = "evidence://qa",
    owner: str = "",
    detail: str = "",
) -> QACheck:
    return QACheck(
        kind=kind,
        outcome=outcome,
        evidence=evidence,
        owner=owner,
        detail=detail,
    )


def launch_checks(outcomes=None) -> tuple[QACheck, ...]:
    outcomes = outcomes or {}
    return tuple(
        launch_check(
            kind,
            outcome=outcomes.get(kind, QACheckOutcome.PASSED),
            owner=(
                "risk-owner"
                if outcomes.get(kind) is QACheckOutcome.EXCEPTED
                else ""
            ),
        )
        for kind in QA_CHECK_ORDER
    )


def authorization(
    *,
    authorized_by: str = "client-authority",
    intended_use: str = USE,
    authorized_on=TODAY,
) -> TrafficAuthorization:
    return TrafficAuthorization(
        authorized_by=authorized_by,
        intended_use=intended_use,
        authorized_on=authorized_on,
    )


def launch_qa(funnel=None, checks=None, **overrides) -> LaunchQA:
    values = {
        "qa_id": "qa-3f",
        "tenant_id": TENANT,
        "funnel": complete_funnel() if funnel is None else funnel,
        "owner": "qa-owner",
        "designated_authority": "client-authority",
        "checks": launch_checks() if checks is None else checks,
    }
    values.update(overrides)
    return LaunchQA(**values)


def ready_for_traffic(**overrides) -> LaunchQA:
    return launch_qa(**overrides).authorize_traffic(
        authorization=authorization()
    )
