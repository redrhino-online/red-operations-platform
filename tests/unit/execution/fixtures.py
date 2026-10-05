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
    PerformanceBaseline,
)
from redops.contexts.execution.domain.swimlanes import (
    SWIMLANE_CHANNELS,
    SwimlaneChannel,
    SwimlaneMove,
    SwimlanesPlan,
)
from redops.contexts.execution.domain.value_objects import (
    HANDOFF_ORDER,
    MILESTONE_ORDER,
    QA_CHECK_ORDER,
    ClaimKind,
    ComplianceAsset,
    ComplianceAssetKind,
    CompliancePackage,
    ComplianceWaiver,
    FunnelAssetPackage,
    HandoffKind,
    HandoffOutcome,
    HandoffRecord,
    LaunchAssetPackage,
    MilestoneKind,
    MilestoneObservation,
    ObservationStatus,
    PerformanceClaim,
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


def swimlane_move(
    channel: SwimlaneChannel = SwimlaneChannel.MESSAGES,
    *,
    tenant_id: str = TENANT,
    stalled_step: str = "traffic",
    next_step: str = "opt_in",
    **overrides,
) -> SwimlaneMove:
    values = {
        "move_id": f"move-{channel.value}",
        "tenant_id": tenant_id,
        "channel": channel,
        "stalled_step": stalled_step,
        "next_step": next_step,
        "vehicle": "email",
        "next_action": "send the reason to take the next step",
    }
    values.update(overrides)
    return SwimlaneMove(**values)


def swimlane_moves(
    *, tenant_id: str = TENANT, channels=SWIMLANE_CHANNELS
) -> tuple[SwimlaneMove, ...]:
    return tuple(
        swimlane_move(channel, tenant_id=tenant_id)
        for channel in channels
    )


def swimlanes_plan(funnel=None, moves=None, **overrides) -> SwimlanesPlan:
    values = {
        "plan_id": "swimlanes-3f",
        "tenant_id": TENANT,
        "owner": "recovery-owner",
        "funnel": complete_funnel() if funnel is None else funnel,
        "moves": swimlane_moves() if moves is None else moves,
    }
    values.update(overrides)
    return SwimlanesPlan(**values)


def compliance_asset(
    kind: ComplianceAssetKind,
    *,
    tenant_id: str = TENANT,
        reference: str | None = None,
    version: int = 1,
) -> ComplianceAsset:
    return ComplianceAsset(
        kind=kind,
        tenant_id=tenant_id,
        reference=(
            reference
            if reference is not None
            else f"asset://compliance/{kind.value}"
        ),
        version=version,
    )


def compliance_assets(
    *,
    tenant_id: str = TENANT,
    version: int = 1,
    kinds=None,
) -> tuple[ComplianceAsset, ...]:
    kinds = tuple(ComplianceAssetKind) if kinds is None else tuple(kinds)
    return tuple(
        compliance_asset(kind, tenant_id=tenant_id, version=version)
        for kind in kinds
    )


def compliance_waiver(
    kind: ComplianceAssetKind,
    *,
    reason: str = "reviewed exception",
    risk_owner: str = "risk-owner",
    review_trigger: str = "before the next campaign",
    expires_on=None,
) -> ComplianceWaiver:
    return ComplianceWaiver(
        kind=kind,
        reason=reason,
        risk_owner=risk_owner,
        review_trigger=review_trigger,
        expires_on=expires_on,
    )


def compliance_package(
    *,
    package_id: str = "compliance-3f",
    tenant_id: str = TENANT,
    target_markets: tuple[str, ...] = ("us",),
    assets=None,
    waivers: tuple[ComplianceWaiver, ...] = (),
) -> CompliancePackage:
    return CompliancePackage(
        package_id=package_id,
        tenant_id=tenant_id,
        target_markets=target_markets,
        assets=(
            compliance_assets(tenant_id=tenant_id) if assets is None else assets
        ),
        waivers=waivers,
    )


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
    if "compliance" not in overrides:
        values["compliance"] = compliance_package(
            tenant_id=values["tenant_id"]
        )
    return LaunchQA(**values)


def ready_for_traffic(**overrides) -> LaunchQA:
    return launch_qa(**overrides).authorize_traffic(
        authorization=authorization()
    )


def launch_assets(**overrides) -> LaunchAssetPackage:
    values = {
        "live_campaign": "asset://launch/campaign",
        "spend_records": "asset://launch/spend",
        "lead_records": "asset://launch/leads",
        "conversion_measures": "asset://launch/conversions",
        "engagement_measures": "asset://launch/engagement",
        "applications": "asset://launch/applications",
        "bookings": "asset://launch/bookings",
        "shows": "asset://launch/shows",
        "closes": "asset://launch/closes",
        "acquisition_cost": "asset://launch/acquisition-cost",
        "attribution": "asset://launch/attribution",
        "issue_log": "asset://launch/issues",
    }
    values.update(overrides)
    return LaunchAssetPackage(**values)


def milestone(
    kind: MilestoneKind,
    *,
    status: ObservationStatus = ObservationStatus.OBSERVED,
    tenant_id: str = TENANT,
    observed_on=TODAY,
    source: str = "analytics://observation",
    detail: str = "",
) -> MilestoneObservation:
    return MilestoneObservation(
        kind=kind,
        status=status,
        tenant_id=tenant_id,
        observed_on=observed_on if status is ObservationStatus.OBSERVED else None,
        source=source if status is ObservationStatus.OBSERVED else "",
        detail=detail,
    )


def milestone_observations(outcomes=None) -> tuple[MilestoneObservation, ...]:
    outcomes = outcomes or {}
    return tuple(
        milestone(
            kind,
            status=outcomes.get(
                kind,
                (
                    ObservationStatus.OBSERVED
                    if kind is MilestoneKind.FIRST_QUALIFIED_TRAFFIC
                    else ObservationStatus.PENDING
                ),
            ),
        )
        for kind in MILESTONE_ORDER
    )


def performance_baseline(
    launch_qa=None, milestones=None, **overrides
) -> PerformanceBaseline:
    values = {
        "baseline_id": "baseline-3f",
        "tenant_id": TENANT,
        "launch_qa": ready_for_traffic() if launch_qa is None else launch_qa,
        "owner": "performance-owner",
        "assets": launch_assets(),
        "milestones": (
            milestone_observations() if milestones is None else milestones
        ),
    }
    values.update(overrides)
    return PerformanceBaseline(**values)


def established_baseline(**overrides) -> PerformanceBaseline:
    return performance_baseline(**overrides).establish(on=TODAY)


def performance_claim(
    *,
    claim_id: str = "claim-3f",
    tenant_id: str = TENANT,
    subject: str = "first campaign",
    statement: str = "leads rose after the campaign launched",
    kind: ClaimKind = ClaimKind.OBSERVATION,
    sample_size: int = 40,
    source: str = "analytics://observation",
    baseline_id: str | None = "baseline-3f",
) -> PerformanceClaim:
    return PerformanceClaim(
        claim_id=claim_id,
        tenant_id=tenant_id,
        subject=subject,
        statement=statement,
        kind=kind,
        sample_size=sample_size,
        source=source,
        baseline_id=baseline_id,
    )
