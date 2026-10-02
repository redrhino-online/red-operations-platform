"""Aggregates for the Engagement bounded context (pure domain).

The ClientWorkspace is the tenant root described in SPEC.md section 3. Its
invariant is that "every child resource belongs to exactly one client": a child
may attach only once and only when its tenant matches the workspace tenant. It
also records the workspace authorities and the engagement lifecycle, so the whole
stage 0-10 pipeline has a client-owned anchor to attach to and a named owner
registry to approve against.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from redops.contexts.engagement.domain.errors import (
    ChildAlreadyAttachedError,
    InvalidClientWorkspaceError,
    TenantBoundaryError,
)
from redops.contexts.engagement.domain.policies import WorkspaceLifecyclePolicy
from redops.contexts.engagement.domain.value_objects import (
    ClientAuthority,
    EngagementLifecycle,
    LifecycleTransition,
)


@dataclass
class ClientWorkspace:
    """The tenant root for one client engagement (SPEC.md section 3).

    Required fields come from the aggregate table: an opaque id, the tenant, the
    authorities and a lifecycle. The workspace is the boundary every stage 0-10
    asset and later cross-context reference belongs to. A child resource attaches
    only when its tenant matches, and only once, so a resource cannot belong to
    two clients. Named approver identities are supplied by the caller; the
    aggregate never invents a human authority (SPEC.md section 11).
    """

    workspace_id: str
    tenant_id: str
    authorities: tuple[ClientAuthority, ...]
    lifecycle: EngagementLifecycle = EngagementLifecycle.INTAKE
    _children: dict[str, str] = field(
        default_factory=dict, repr=False, compare=False
    )
    _paused_from: EngagementLifecycle | None = field(
        default=None, repr=False, compare=False
    )
    _transitions: list[LifecycleTransition] = field(
        default_factory=list, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not self.workspace_id or not self.workspace_id.strip():
            raise InvalidClientWorkspaceError(
                "client workspace id is required"
            )
        if not self.tenant_id or not self.tenant_id.strip():
            raise InvalidClientWorkspaceError(
                "client workspace tenant id is required"
            )
        if not self.authorities:
            raise InvalidClientWorkspaceError(
                "a client workspace requires at least one authority"
            )
        seen: set[ClientAuthority] = set()
        for entry in self.authorities:
            if entry in seen:
                raise InvalidClientWorkspaceError(
                    f"client workspace repeats authority {entry.actor!r} / "
                    f"{entry.authority!r}"
                )
            seen.add(entry)

    @property
    def transitions(self) -> tuple[LifecycleTransition, ...]:
        return tuple(self._transitions)

    def owns(self, tenant_id: str) -> bool:
        """Whether a resource tenant belongs to this client."""
        return bool(tenant_id) and tenant_id == self.tenant_id

    def attach(self, child_id: str, tenant_id: str) -> None:
        """Attach a child resource to this client, enforcing the tenant boundary.

        SPEC.md section 3: every child resource belongs to exactly one client. A
        blank child id, a child already attached here, or a child from another
        tenant is refused rather than silently attached.
        """
        if not child_id or not child_id.strip():
            raise InvalidClientWorkspaceError(
                "an attached child resource requires a non-empty id"
            )
        if not self.owns(tenant_id):
            raise TenantBoundaryError(
                f"child {child_id!r} belongs to tenant {tenant_id!r}, not "
                f"workspace tenant {self.tenant_id!r}"
            )
        if child_id in self._children:
            raise ChildAlreadyAttachedError(
                f"child {child_id!r} is already attached to workspace "
                f"{self.workspace_id!r}"
            )
        self._children[child_id] = tenant_id

    def is_attached(self, child_id: str) -> bool:
        return child_id in self._children

    def child_tenant(self, child_id: str) -> str | None:
        return self._children.get(child_id)

    @property
    def children(self) -> tuple[str, ...]:
        return tuple(self._children)

    def designate(self, entry: ClientAuthority) -> None:
        """Add a named authority to the workspace, refusing a duplicate."""
        if entry in self.authorities:
            raise InvalidClientWorkspaceError(
                f"client workspace already records authority {entry.actor!r} / "
                f"{entry.authority!r}"
            )
        self.authorities = (*self.authorities, entry)

    def has_authority(self, actor: str, authority: str | None = None) -> bool:
        return any(
            entry.actor == actor
            and (authority is None or entry.authority == authority)
            for entry in self.authorities
        )

    def advance_to(
        self,
        target: EngagementLifecycle,
        *,
        actor: str,
        reason: str,
        on: date,
        correlation_id: str,
    ) -> LifecycleTransition:
        """Move the engagement forward one canonical state and record it."""
        WorkspaceLifecyclePolicy().require_advance(self.lifecycle, target)
        return self._transition(
            target,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )

    def pause(
        self,
        *,
        actor: str,
        reason: str,
        on: date,
        correlation_id: str,
    ) -> LifecycleTransition:
        """Pause an active engagement, remembering the state to resume to."""
        WorkspaceLifecyclePolicy().require_pause(self.lifecycle)
        paused_from = self.lifecycle
        transition = self._transition(
            EngagementLifecycle.PAUSED,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )
        self._paused_from = paused_from
        return transition

    def resume(
        self,
        *,
        actor: str,
        reason: str,
        on: date,
        correlation_id: str,
    ) -> LifecycleTransition:
        """Resume a paused engagement to the state it paused from."""
        WorkspaceLifecyclePolicy().require_resume(self.lifecycle)
        target = self._paused_from or EngagementLifecycle.INTAKE
        transition = self._transition(
            target,
            actor=actor,
            reason=reason,
            on=on,
            correlation_id=correlation_id,
        )
        self._paused_from = None
        return transition

    def _transition(
        self,
        target: EngagementLifecycle,
        *,
        actor: str,
        reason: str,
        on: date,
        correlation_id: str,
    ) -> LifecycleTransition:
        previous = self.lifecycle
        self.lifecycle = target
        transition = LifecycleTransition(
            actor=actor,
            reason=reason,
            occurred_at=on,
            old_lifecycle=previous,
            new_lifecycle=target,
            correlation_id=correlation_id,
        )
        self._transitions.append(transition)
        return transition
