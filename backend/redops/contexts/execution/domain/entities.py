"""Aggregates for the Execution bounded context (pure domain).

FunnelIntegration is the stage 8 funnel integration, completed at the "Funnel
Complete" checkpoint (SPEC.md section 4). Its invariant is that the funnel is
grounded on the approved stage 7 Authority Amplifier and that it only becomes
complete after a test prospect completes the capture, engagement and conversion
handoffs with reliable records and ownership.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from redops.contexts.execution.domain.errors import (
    FunnelDependencyError,
    InvalidFunnelError,
)
from redops.contexts.execution.domain.value_objects import (
    FunnelAssetPackage,
    FunnelState,
    ProspectPathDryRun,
)
from redops.contexts.production.domain.entities import AuthorityAmplifier


@dataclass(frozen=True)
class FunnelIntegration:
    """The stage 8 funnel integration, approved at "Funnel Complete".

    SPEC.md section 4, stage 8 "Integrate": the required asset package is the
    campaign architecture, pages, forms, qualification, booking, sequences, CRM,
    tags, automation, analytics, tracking, sales handoff and SOPs. The "Funnel
    Complete" checkpoint requires a test prospect to complete capture, engagement
    and conversion handoffs with reliable records and ownership.

    The funnel is grounded on the approved stage 7 `AuthorityAmplifier` (SPEC.md
    section 3: production requires approved dependencies), so a funnel cannot be
    completed on an amplifier that has not received creative acceptance. It is
    frozen: completion pins an exact asset and the dry run evidence rather than
    mutating them, and an upstream change returns it to review required.
    """

    integration_id: str
    tenant_id: str
    amplifier: AuthorityAmplifier
    owner: str
    assets: FunnelAssetPackage
    state: FunnelState = FunnelState.DRAFT
    dry_run: ProspectPathDryRun | None = field(default=None)
    review_reason: str | None = field(default=None)

    def __post_init__(self) -> None:
        for label, value in (
            ("funnel integration id", self.integration_id),
            ("funnel integration tenant id", self.tenant_id),
            ("funnel integration owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidFunnelError(f"{label} is required")
        if self.amplifier.tenant_id != self.tenant_id:
            raise FunnelDependencyError(
                "a funnel cannot be grounded on another tenant's authority "
                "amplifier"
            )
        if self.dry_run is not None and self.dry_run.tenant_id != self.tenant_id:
            raise FunnelDependencyError(
                "a funnel cannot pin another tenant's prospect path dry run"
            )

    @property
    def is_complete(self) -> bool:
        return self.state is FunnelState.COMPLETE

    @property
    def is_terminal(self) -> bool:
        return self.state.is_terminal

    def mark_funnel_complete(
        self, dry_run: ProspectPathDryRun
    ) -> "FunnelIntegration":
        """Return a complete funnel once the stage 8 checkpoint passes.

        SPEC.md section 4, stage 8: the "Funnel Complete" checkpoint requires the
        approved stage 7 dependency and a test prospect that completes capture,
        engagement and conversion handoffs with reliable records and ownership. A
        failed or missing handoff prevents completion (Phase 4 TDD example:
        "failed prospect routing prevents Funnel Complete"). The dry run evidence
        is pinned so completion is traceable to the observed prospect path.
        """
        from redops.contexts.execution.domain.policies import (
            FunnelCompletionPolicy,
        )

        FunnelCompletionPolicy().require(self, dry_run)
        return replace(
            self,
            state=FunnelState.COMPLETE,
            dry_run=dry_run,
            review_reason=None,
        )

    def mark_review_required(self, *, reason: str) -> "FunnelIntegration":
        """Return this funnel marked review required after a change upstream.

        SPEC.md section 4: changing an approved upstream asset marks dependent
        assets review required. A complete funnel loses that completion until the
        dependency is reviewed again, and a terminal funnel stays terminal.
        """
        if not reason or not reason.strip():
            raise InvalidFunnelError("funnel review reason is required")
        if self.state.is_terminal:
            raise InvalidFunnelError(
                "a terminal funnel cannot be marked review required"
            )
        return replace(
            self, state=FunnelState.REVIEW_REQUIRED, review_reason=reason
        )
