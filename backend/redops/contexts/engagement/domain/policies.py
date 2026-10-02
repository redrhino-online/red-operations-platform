"""Lifecycle policy for the Engagement bounded context (pure domain).

SPEC.md section 4 names the engagement summary states and requires illegal
transitions to be rejected rather than silently coerced. The canonical
progression is forward-only, one step at a time; a workspace may pause from an
active state and resume to the state it paused from, and a completed workspace is
terminal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from redops.contexts.engagement.domain.errors import (
    GateApproverNotAuthorizedError,
    IllegalLifecycleTransitionError,
    IncompleteIntakePackageError,
    IntakeOwnerNotAuthorizedError,
    TenantBoundaryError,
    UnsourcedIntakeEvidenceError,
)
from redops.contexts.engagement.domain.value_objects import (
    CANONICAL_PROGRESSION,
    EngagementLifecycle,
    IntakePackage,
)
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.policies import sourced_claim_ids

if TYPE_CHECKING:
    from redops.contexts.engagement.domain.entities import ClientWorkspace
    from redops.contexts.governance.domain.entities import StageGate


class WorkspaceLifecyclePolicy:
    """Evaluates whether an engagement lifecycle transition is legal."""

    def can_advance(
        self, current: EngagementLifecycle, target: EngagementLifecycle
    ) -> bool:
        if current.is_terminal or current is EngagementLifecycle.PAUSED:
            return False
        if target is EngagementLifecycle.PAUSED:
            return False
        if target is EngagementLifecycle.COMPLETED:
            return current in {
                EngagementLifecycle.OPTIMIZATION,
                EngagementLifecycle.EXPANSION,
            }
        if target.is_terminal:
            return False
        try:
            current_index = CANONICAL_PROGRESSION.index(current)
            target_index = CANONICAL_PROGRESSION.index(target)
        except ValueError:
            return False
        return target_index == current_index + 1

    def require_advance(
        self, current: EngagementLifecycle, target: EngagementLifecycle
    ) -> None:
        if not self.can_advance(current, target):
            raise IllegalLifecycleTransitionError(
                f"engagement cannot advance from {current.value!r} to "
                f"{target.value!r}"
            )

    def require_pause(self, current: EngagementLifecycle) -> None:
        if not current.is_active:
            raise IllegalLifecycleTransitionError(
                f"engagement in {current.value!r} cannot be paused"
            )

    def require_resume(self, current: EngagementLifecycle) -> None:
        if current is not EngagementLifecycle.PAUSED:
            raise IllegalLifecycleTransitionError(
                f"engagement in {current.value!r} is not paused and cannot resume"
            )


class ProductionReadyPolicy:
    """Evaluates the stage 0 "Production Ready" checkpoint for an intake package.

    SPEC.md section 4, stage 0 "Intake" and its "Production Ready" checkpoint:
    "building for whom, success measure, owners, boundaries, and prerequisites
    are explicit", and the stage is complete only when its required assets exist.
    The policy refuses to declare an intake package production ready unless every
    canonical stage 0 asset kind is present, each asset's named owner is a
    designated authority on the same client workspace, and each asset's evidence
    is a known, directly sourced Knowledge claim of the same client. A missing
    asset, an unaccountable owner or unsourced evidence is surfaced rather than
    hidden behind a passed gate (SPEC.md sections 1, 3 and 4).
    """

    def require(
        self,
        package: IntakePackage,
        workspace: "ClientWorkspace",
        claims: Iterable[Claim],
    ) -> None:
        if package.tenant_id != workspace.tenant_id:
            raise TenantBoundaryError(
                f"intake package {package.package_id!r} belongs to tenant "
                f"{package.tenant_id!r}, not workspace tenant "
                f"{workspace.tenant_id!r}"
            )
        missing = package.missing_kinds()
        if missing:
            names = ", ".join(kind.value for kind in missing)
            raise IncompleteIntakePackageError(
                f"intake package {package.package_id!r} cannot be production "
                f"ready: missing required assets {names}"
            )
        sourced = sourced_claim_ids(package.tenant_id, claims)
        for asset in package.assets:
            if not workspace.has_authority(asset.owner):
                raise IntakeOwnerNotAuthorizedError(
                    f"intake asset {asset.asset_id!r} names owner "
                    f"{asset.owner!r}, who holds no authority on workspace "
                    f"{workspace.workspace_id!r}"
                )
            for claim_id in asset.evidence_claim_ids:
                if claim_id not in sourced:
                    raise UnsourcedIntakeEvidenceError(
                        f"intake asset {asset.asset_id!r} cannot be evidenced: "
                        f"claim {claim_id!r} is not a known, directly sourced "
                        "claim for this tenant"
                    )


class GateApproverAuthorityPolicy:
    """Evaluates that a stage gate is approved by a client-designated authority.

    SPEC.md sections 4 and 5: a gate is approved by the client-designated
    authority, and an agent cannot confer human approval upon itself. The
    governance ``StageGate`` carries a free ``approver`` string, and the
    ``GateIntegrityPolicy`` only requires it to be non-empty and distinct from the
    author, so nothing yet binds it to the client. This policy refuses a gate
    whose designated approver is absent, or names an actor who is not a named
    authority on the ``ClientWorkspace``, before the stage 0 "Production Ready"
    (or any other stage) ``GateDecision`` can be recorded. It never invents a
    concrete approver identity or authority role; the workspace registry supplies
    the named people (SPEC.md section 11).
    """

    def require(
        self,
        gate: "StageGate",
        workspace: "ClientWorkspace",
    ) -> None:
        approver = gate.approver
        if not approver or not approver.strip():
            raise GateApproverNotAuthorizedError(
                "a stage gate requires a designated approver who holds a named "
                f"authority on workspace {workspace.workspace_id!r}"
            )
        if not workspace.has_authority(approver):
            raise GateApproverNotAuthorizedError(
                f"gate approver {approver!r} holds no authority on workspace "
                f"{workspace.workspace_id!r} for tenant {workspace.tenant_id!r}"
            )
