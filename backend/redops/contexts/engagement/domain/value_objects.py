"""Value objects for the Engagement bounded context (pure domain).

The ClientWorkspace aggregate is the tenant root every client-owned resource
attaches to. Its lifecycle mirrors the engagement summary state in SPEC.md
section 4 ("Engagement: Intake, Diagnosis, ... Paused, Completed"); the stages 0
to 10 are the production checkpoints, and parallel BuildObjects may sit in
different build states while the engagement summary is elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from redops.contexts.engagement.domain.errors import InvalidAuthorityError


class EngagementLifecycle(Enum):
    """The engagement summary state from SPEC.md section 4.

    The states follow the canonical engagement progression: the stage 0-10 names
    in order, then Optimization and Expansion for the post-launch measurement and
    portfolio work, with Paused and Completed as the non-linear states. Completed
    is terminal.
    """

    INTAKE = "intake"
    DIAGNOSIS = "diagnosis"
    POSITIONING = "positioning"
    DIAGNOSTIC_MODELING = "diagnostic_modeling"
    IP_PACKAGING = "ip_packaging"
    PRODUCTIZATION = "productization"
    CAMPAIGN_MESSAGING = "campaign_messaging"
    AUTHORITY_AMPLIFIER_PRODUCTION = "authority_amplifier_production"
    FUNNEL_INTEGRATION = "funnel_integration"
    LAUNCH_QA = "launch_qa"
    FIRST_CAMPAIGN_LAUNCH = "first_campaign_launch"
    OPTIMIZATION = "optimization"
    EXPANSION = "expansion"
    PAUSED = "paused"
    COMPLETED = "completed"

    @property
    def is_terminal(self) -> bool:
        return self is EngagementLifecycle.COMPLETED

    @property
    def is_active(self) -> bool:
        return self not in {EngagementLifecycle.PAUSED, EngagementLifecycle.COMPLETED}


CANONICAL_PROGRESSION: tuple[EngagementLifecycle, ...] = (
    EngagementLifecycle.INTAKE,
    EngagementLifecycle.DIAGNOSIS,
    EngagementLifecycle.POSITIONING,
    EngagementLifecycle.DIAGNOSTIC_MODELING,
    EngagementLifecycle.IP_PACKAGING,
    EngagementLifecycle.PRODUCTIZATION,
    EngagementLifecycle.CAMPAIGN_MESSAGING,
    EngagementLifecycle.AUTHORITY_AMPLIFIER_PRODUCTION,
    EngagementLifecycle.FUNNEL_INTEGRATION,
    EngagementLifecycle.LAUNCH_QA,
    EngagementLifecycle.FIRST_CAMPAIGN_LAUNCH,
    EngagementLifecycle.OPTIMIZATION,
    EngagementLifecycle.EXPANSION,
)


@dataclass(frozen=True)
class ClientAuthority:
    """A named actor and the authority they hold in a client workspace.

    SPEC.md section 3 records a workspace's authorities, and SPEC.md section 4
    requires named human owners and a client-designated authority. The value
    object names the actor and the authority; it does not invent the concrete
    authority roles, which remain an open decision (SPEC.md section 11).
    """

    actor: str
    authority: str

    def __post_init__(self) -> None:
        if not self.actor or not self.actor.strip():
            raise InvalidAuthorityError("client authority actor is required")
        if not self.authority or not self.authority.strip():
            raise InvalidAuthorityError("client authority name is required")


@dataclass(frozen=True)
class LifecycleTransition:
    """One recorded engagement lifecycle change (SPEC.md section 4).

    Records the actor, reason, timestamp, old and new state and correlation ID so
    the workspace history can be reconstructed and audited, mirroring the other
    context state machines.
    """

    actor: str
    reason: str
    occurred_at: date
    old_lifecycle: EngagementLifecycle
    new_lifecycle: EngagementLifecycle
    correlation_id: str

    def __post_init__(self) -> None:
        if not self.actor or not self.actor.strip():
            raise ValueError("lifecycle transition actor is required")
        if not self.reason or not self.reason.strip():
            raise ValueError("lifecycle transition reason is required")
        if not self.correlation_id or not self.correlation_id.strip():
            raise ValueError("lifecycle transition correlation id is required")
