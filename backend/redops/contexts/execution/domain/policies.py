"""Completion policy for the Execution bounded context (pure domain).

SPEC.md section 4, stage 8 "Integrate": the "Funnel Complete" checkpoint
requires a test prospect to complete capture, engagement and conversion handoffs
with reliable records and ownership, and the stage is grounded on the approved
stage 7 Authority Amplifier (SPEC.md section 3: production requires approved
dependencies). Phase 4 TDD example: "failed prospect routing prevents Funnel
Complete".
"""

from __future__ import annotations

from datetime import date

from redops.contexts.execution.domain.entities import (
    FunnelIntegration,
    LaunchQA,
    PerformanceBaseline,
)
from redops.contexts.execution.domain.errors import (
    ComplianceTenantBoundaryError,
    ExpiredComplianceWaiverError,
    FunnelDependencyError,
    FunnelIncompleteError,
    LaunchQAAuthorityError,
    LaunchQADependencyError,
    LaunchQAIncompleteError,
    MissingComplianceAssetError,
    PerformanceBaselineDependencyError,
    PerformanceBaselineIncompleteError,
    PerformanceBaselinePrecedenceError,
    PerformanceClaimSupportError,
)
from redops.contexts.execution.domain.value_objects import (
    HANDOFF_ORDER,
    MILESTONE_ORDER,
    QA_CHECK_ORDER,
    ClaimKind,
    MilestoneKind,
    PerformanceClaim,
    ProspectPathDryRun,
    TrafficAuthorization,
)


class FunnelCompletionPolicy:
    """Refuses "Funnel Complete" on an under-grounded or incomplete funnel.

    Completion requires the stage 7 Authority Amplifier to have received its
    creative acceptance and to belong to the same tenant, and the prospect path
    dry run to have routed every canonical handoff. A failed or missing handoff,
    or an unapproved stage 7 dependency, leaves the funnel incomplete rather than
    being represented as ready for launch QA.
    """

    def require(
        self, integration: FunnelIntegration, dry_run: ProspectPathDryRun
    ) -> None:
        if integration.state.is_terminal:
            raise FunnelDependencyError(
                f"terminal funnel {integration.integration_id!r} cannot complete"
            )
        amplifier = integration.amplifier
        if amplifier.tenant_id != integration.tenant_id:
            raise FunnelDependencyError(
                "a funnel cannot be grounded on another tenant's authority "
                "amplifier"
            )
        if not amplifier.is_approved:
            raise FunnelDependencyError(
                f"funnel {integration.integration_id!r} cannot complete: it is "
                "grounded on a stage 7 Authority Amplifier that has not received "
                "creative acceptance"
            )
        if dry_run.tenant_id != integration.tenant_id:
            raise FunnelDependencyError(
                "a funnel cannot complete on another tenant's prospect path dry "
                "run"
            )
        if not dry_run.is_complete:
            raise FunnelIncompleteError(
                f"funnel {integration.integration_id!r} cannot complete: the "
                f"prospect path is incomplete ({_describe(dry_run)})"
            )


def _describe(dry_run: ProspectPathDryRun) -> str:
    parts = []
    for kind in HANDOFF_ORDER:
        if kind in dry_run.failed_kinds:
            parts.append(f"{kind.value} failed")
        elif kind in dry_run.missing_kinds:
            parts.append(f"{kind.value} missing")
    return ", ".join(parts) if parts else "no routed handoffs"


class LaunchApprovedPolicy:
    """Refuses "Launch Approved" on an under-grounded or failing stage 9 QA.

    SPEC.md section 4, stage 9: all critical path checks must pass, exceptions
    must have owners, and the designated human authority must authorize traffic,
    grounded on the completed stage 8 funnel. A failed or excepted critical path
    check, a missing check, an incomplete funnel, or a non-designated authorizer
    leaves the QA not ready for traffic (Phase 4 TDD example: "failed message,
    technical or commercial QA prevents Launch Approved"). An exception never
    makes an absent critical path check appear present.
    """

    def require(
        self, qa: LaunchQA, authorization: TrafficAuthorization
    ) -> None:
        if qa.state.is_terminal:
            raise LaunchQADependencyError(
                f"terminal launch QA {qa.qa_id!r} cannot authorize traffic"
            )
        funnel = qa.funnel
        if funnel.tenant_id != qa.tenant_id:
            raise LaunchQADependencyError(
                "a launch QA cannot be grounded on another tenant's funnel"
            )
        if not funnel.is_complete:
            raise LaunchQADependencyError(
                f"launch QA {qa.qa_id!r} cannot authorize traffic: it is "
                "grounded on a stage 8 funnel that has not passed Funnel Complete"
            )

        present = {check.kind for check in qa.checks}
        missing = [kind for kind in QA_CHECK_ORDER if kind not in present]
        if missing:
            names = ", ".join(kind.value for kind in missing)
            raise LaunchQAIncompleteError(
                f"launch QA {qa.qa_id!r} cannot authorize traffic: missing "
                f"checks: {names}"
            )

        for check in qa.checks:
            if check.is_passing:
                continue
            if check.kind.is_critical_path:
                raise LaunchQAIncompleteError(
                    f"launch QA {qa.qa_id!r} cannot authorize traffic: critical "
                    f"path check {check.kind.value!r} "
                    f"{check.outcome.value} and cannot be excepted"
                )
            if not check.owner or not check.owner.strip():
                raise LaunchQAIncompleteError(
                    f"launch QA {qa.qa_id!r} cannot authorize traffic: check "
                    f"{check.kind.value!r} {check.outcome.value} has no owner"
                )

        if authorization.authorized_by != qa.designated_authority:
            raise LaunchQAAuthorityError(
                f"traffic for launch QA {qa.qa_id!r} was not authorized by the "
                f"designated authority {qa.designated_authority!r}"
            )


class ComplianceRequiredPolicy:
    """Refuses "Launch Approved" traffic without the launch compliance assets.

    SPEC.md section 4, stage 9 "QA" requires "consent where applicable" before
    the checkpoint authorizes traffic, and section 9 requires retention, export
    and deletion policies before onboarding production clients. The canon (SPEC.md
    section 12.3: stage 9 uses canon files 01, 08, 21, 22 and 24; the compliance
    suite is seeded from canon files 21 and 34) treats the GDPR consent, Facebook
    advertising disclaimer, income and FTC disclaimer, privacy policy, terms of
    use and attorney review as launch-blocking assets.

    The reviewed ``CompliancePackage`` must be present and complete for the QA's
    declared target markets, or a live scoped human waiver must cover each absent
    asset. A missing required asset refuses launch, and an expired waiver stops
    covering its asset and refuses launch with a distinct named error (SPEC.md
    section 4: "a failed or expired prerequisite blocks dependent authorization
    until resolved"; a waiver never makes an absent asset appear present). The
    policy is pure: it reads the QA's pinned package and mutates nothing.
    """

    def require(self, qa: LaunchQA, *, on: date) -> None:
        package = qa.compliance
        if package is None:
            raise MissingComplianceAssetError(
                f"launch QA {qa.qa_id!r} cannot authorize traffic: no reviewed "
                "compliance and consent package is pinned"
            )
        if package.tenant_id != qa.tenant_id:
            raise ComplianceTenantBoundaryError(
                "a launch QA cannot authorize traffic with another tenant's "
                "compliance package"
            )
        expired = sorted(
            kind.value for kind in package.expired_waived_kinds(on=on)
        )
        if expired:
            raise ExpiredComplianceWaiverError(
                f"launch QA {qa.qa_id!r} cannot authorize traffic: compliance "
                f"waiver for {', '.join(expired)} has expired"
            )
        missing = sorted(
            kind.value for kind in package.uncovered_kinds(on=on)
        )
        if missing:
            raise MissingComplianceAssetError(
                f"launch QA {qa.qa_id!r} cannot authorize traffic: missing "
                f"required compliance assets: {', '.join(missing)}"
            )


class PerformanceBaselinePolicy:
    """Refuses "Performance Baseline Established" on an ungrounded or incomplete
    stage 10 baseline.

    SPEC.md section 4, stage 10: the checkpoint requires the stage 9 launch QA to
    have authorized traffic and first qualified traffic to be observed, with the
    later lead, appointment and sale milestones recorded as distinct milestones
    (pending is allowed). A baseline that omits a milestone, or that claims
    establishment from campaign activation alone, is refused (Phase 5 TDD example:
    "launch alone cannot complete the engagement").
    """

    def require(self, baseline: PerformanceBaseline, on: date) -> None:
        if baseline.state.is_terminal:
            raise PerformanceBaselineDependencyError(
                f"terminal performance baseline {baseline.baseline_id!r} cannot "
                "be established"
            )
        qa = baseline.launch_qa
        if qa.tenant_id != baseline.tenant_id:
            raise PerformanceBaselineDependencyError(
                "a performance baseline cannot be grounded on another tenant's "
                "launch QA"
            )
        if not qa.is_ready_for_traffic:
            raise PerformanceBaselineDependencyError(
                f"performance baseline {baseline.baseline_id!r} cannot be "
                "established: the stage 9 launch QA has not authorized traffic"
            )
        if baseline.missing_kinds:
            names = ", ".join(
                kind.value
                for kind in MILESTONE_ORDER
                if kind in baseline.missing_kinds
            )
            raise PerformanceBaselineIncompleteError(
                f"performance baseline {baseline.baseline_id!r} cannot be "
                f"established: missing observations must be recorded as pending: "
                f"{names}"
            )
        if MilestoneKind.FIRST_QUALIFIED_TRAFFIC not in baseline.observed_kinds:
            raise PerformanceBaselineIncompleteError(
                f"performance baseline {baseline.baseline_id!r} cannot be "
                "established: first qualified traffic has not been observed"
            )
        traffic = next(
            observation
            for observation in baseline.milestones
            if observation.kind is MilestoneKind.FIRST_QUALIFIED_TRAFFIC
        )
        evidence_on = max(
            qa.authorization.authorized_on, traffic.observed_on
        )
        if on < evidence_on:
            raise PerformanceBaselinePrecedenceError(
                f"performance baseline {baseline.baseline_id!r} cannot be "
                f"established on {on.isoformat()}: the traffic it reports was "
                f"authorized and observed on {evidence_on.isoformat()}"
            )


class PerformanceClaimPolicy:
    """Refuses a causal claim without an established baseline or adequate sample.

    SPEC.md section 3, Measurement invariant: observations are distinct from
    causal conclusions. A before-and-after causal claim requires an established
    performance baseline, and a low sample size cannot support a causal
    conclusion at all; the same movement may be recorded as an interpretation
    (Phase 5 TDD examples: "missing baseline blocks a before and after claim" and
    "low sample size keeps causal claim as interpretation").
    """

    def require(
        self,
        claim: PerformanceClaim,
        baseline: PerformanceBaseline | None,
        *,
        minimum_sample: int,
    ) -> None:
        if minimum_sample < 1:
            raise PerformanceClaimSupportError(
                "a causal minimum sample must be at least one"
            )
        if baseline is not None:
            if baseline.tenant_id != claim.tenant_id:
                raise PerformanceClaimSupportError(
                    "a performance claim cannot cite another tenant's baseline"
                )
            if (
                claim.baseline_id is not None
                and claim.baseline_id != baseline.baseline_id
            ):
                raise PerformanceClaimSupportError(
                    "a performance claim cites a different baseline than the one "
                    "supplied"
                )
        if claim.kind is not ClaimKind.CAUSAL_CONCLUSION:
            return
        if baseline is None or not baseline.is_established:
            raise PerformanceClaimSupportError(
                "a before-and-after causal claim requires an established "
                "performance baseline"
            )
        if claim.sample_size < minimum_sample:
            raise PerformanceClaimSupportError(
                f"sample size {claim.sample_size} is below the minimum "
                f"{minimum_sample}; a low sample cannot support a causal "
                "conclusion, record the movement as an interpretation"
            )
