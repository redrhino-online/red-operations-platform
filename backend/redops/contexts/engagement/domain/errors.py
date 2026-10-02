"""Named domain errors for the Engagement bounded context (pure domain)."""

from __future__ import annotations


class EngagementError(Exception):
    """Base class for engagement domain rule violations."""


class InvalidClientWorkspaceError(EngagementError, ValueError):
    """A ClientWorkspace was built or changed without its required identity.

    SPEC.md section 3: the ClientWorkspace aggregate carries an id, a tenant, its
    authorities and a lifecycle. A workspace that leaves its opaque id, tenant or
    authority registry unspecified cannot anchor any client-owned resource.
    """


class InvalidAuthorityError(EngagementError, ValueError):
    """A ClientAuthority was built without a named actor or authority.

    SPEC.md section 3: the workspace records its authorities, and SPEC.md section
    4 requires named human owners. An authority entry that names neither an actor
    nor the authority it holds is not a usable authority record.
    """


class TenantBoundaryError(EngagementError):
    """A child resource from another client was attached to this workspace.

    SPEC.md section 3: "Every child resource belongs to exactly one client." A
    child whose tenant is not this workspace's tenant belongs to a different
    client and cannot be attached here.
    """


class ChildAlreadyAttachedError(EngagementError):
    """A child resource was attached to the same workspace more than once.

    SPEC.md section 3: every child resource belongs to exactly one client. A
    child already attached to this workspace cannot be attached a second time,
    which would leave its ownership ambiguous.
    """


class IllegalLifecycleTransitionError(EngagementError):
    """A ClientWorkspace was asked to move between lifecycle states its rules forbid.

    SPEC.md section 4: the engagement lifecycle must reject illegal transitions
    rather than silently coercing state. A workspace cannot skip, reverse or leave
    its terminal state.
    """
