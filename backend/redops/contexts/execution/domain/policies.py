"""Completion policy for the Execution bounded context (pure domain).

SPEC.md section 4, stage 8 "Integrate": the "Funnel Complete" checkpoint
requires a test prospect to complete capture, engagement and conversion handoffs
with reliable records and ownership, and the stage is grounded on the approved
stage 7 Authority Amplifier (SPEC.md section 3: production requires approved
dependencies). Phase 4 TDD example: "failed prospect routing prevents Funnel
Complete".
"""

from __future__ import annotations

from redops.contexts.execution.domain.entities import FunnelIntegration
from redops.contexts.execution.domain.errors import (
    FunnelDependencyError,
    FunnelIncompleteError,
)
from redops.contexts.execution.domain.value_objects import (
    HANDOFF_ORDER,
    ProspectPathDryRun,
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
