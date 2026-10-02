"""Completion policy for the Execution bounded context (pure domain).

SPEC.md section 4, stage 8 "Integrate": the "Funnel Complete" checkpoint
requires a test prospect to complete capture, engagement and conversion handoffs
with reliable records and ownership, and the stage is grounded on the approved
stage 7 Authority Amplifier (SPEC.md section 3: production requires approved
dependencies). Phase 4 TDD example: "failed prospect routing prevents Funnel
Complete".
"""

from __future__ import annotations

from redops.contexts.execution.domain.entities import (
    FunnelIntegration,
    LaunchQA,
)
from redops.contexts.execution.domain.errors import (
    FunnelDependencyError,
    FunnelIncompleteError,
    LaunchQAAuthorityError,
    LaunchQADependencyError,
    LaunchQAIncompleteError,
)
from redops.contexts.execution.domain.value_objects import (
    HANDOFF_ORDER,
    QA_CHECK_ORDER,
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
