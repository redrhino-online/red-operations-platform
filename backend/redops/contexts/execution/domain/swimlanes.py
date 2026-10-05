"""The canon Swimlanes channel model over the stage 8 to 10 journey (pure domain).

SPEC.md section 12.5 records the canon's Swimlanes channel model -- messages, ads,
human outreach, offline and direct mail, content (canon files 13, 14, 33 and 34)
-- as a canon gap "cross-cutting over stages 8 to 10" whose intended use is to
"recover stalled prospects across all channels, not only digital ads". SPEC.md
section 12.3 maps canon files 13, 14, 33 and 34 onto stages 8 and 10.

The canon calls it the "five swim lanes sales funnel system" (canon files 13 and
14): "five different modalities or vehicles you can use to drive prospects through
your funnel" when they do not move forward, so "wherever they're stuck, we're going
to gently move them to the next step". The canon's lanes are messages (email,
messenger, text), ads (the retargeting layer), content (simple content that drives
to the next call to action), human outreach (a person calls a stalled lead) and
offline or direct mail (postcards and print); canon file 34 warns "you can't just
rely on email" and "you can't be single source dependent".

This is a cross-cutting planning asset over the same-tenant stage 8
``FunnelIntegration`` used to recover stalled prospects across stages 8 to 10. The
methodology owner ruled it a canon-informed required asset kind of the stage 8
"Funnel Complete" gate (owner decision 2026-10-04; SPEC.md sections 4 and 12.5),
so ``SwimlanesPlan.as_stage_asset`` projects the reviewed plan onto exact
``swimlanes-plan`` evidence. It does not authorize sending, publishing, spend or
traffic (SPEC.md sections 4 and 9) and it is never an observation (SPEC.md
section 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from redops.contexts.execution.domain.entities import FunnelIntegration
from redops.contexts.execution.domain.errors import (
    InvalidSwimlanesError,
    SwimlanesDependencyError,
    SwimlanesObservationError,
    SwimlanesTenantBoundaryError,
)
from redops.contexts.governance.domain.value_objects import StageAssetVersion


SWIMLANES_PLAN_KIND = "swimlanes-plan"


class SwimlaneChannel(Enum):
    """The canon's five swimlane channels (SPEC.md section 12.5; canon 13, 14).

    The canon names five modalities that drive a stalled prospect to the next step
    (canon files 13 and 14): messages (email, messenger bots, text), ads (the
    retargeting layer that carries the message's intent), content (simple content
    that drives to the calendar or the cart), human outreach (a person calls a
    stalled lead) and offline or direct mail (postcards and print advertising).
    SPEC.md section 12.5 keeps these as RED's canonical channel set, so a move is
    tied to one typed channel rather than an untyped label.
    """

    MESSAGES = "messages"
    ADS = "ads"
    HUMAN_OUTREACH = "human_outreach"
    OFFLINE_DIRECT_MAIL = "offline_direct_mail"
    CONTENT = "content"


SWIMLANE_CHANNELS: tuple[SwimlaneChannel, ...] = (
    SwimlaneChannel.MESSAGES,
    SwimlaneChannel.ADS,
    SwimlaneChannel.HUMAN_OUTREACH,
    SwimlaneChannel.OFFLINE_DIRECT_MAIL,
    SwimlaneChannel.CONTENT,
)


@dataclass(frozen=True)
class SwimlaneMove:
    """One recovery move down a swimlane for a stalled prospect (canon 13, 14).

    The canon's swimlanes take a prospect who got stuck at one funnel step and
    "gently move them to the next step" (canon file 13), choosing what to present
    on a given channel: a message, an ad that carries the message's intent, a piece
    of content, a human call or an offline touch. A move is frozen and reject-only,
    so a blank identity, an untyped channel, a blank stall or next step, a blank
    vehicle or action, and a move whose next step is the step the prospect already
    occupies (which moves no one) cannot be represented as a recovery move.
    """

    move_id: str
    tenant_id: str
    channel: SwimlaneChannel
    stalled_step: str
    next_step: str
    vehicle: str
    next_action: str

    def __post_init__(self) -> None:
        for label, value in (
            ("swimlane move id", self.move_id),
            ("swimlane move tenant id", self.tenant_id),
            ("swimlane move stalled step", self.stalled_step),
            ("swimlane move next step", self.next_step),
            ("swimlane move vehicle", self.vehicle),
            ("swimlane move next action", self.next_action),
        ):
            if not value or not value.strip():
                raise InvalidSwimlanesError(f"{label} is required")
        if not isinstance(self.channel, SwimlaneChannel):
            raise InvalidSwimlanesError(
                "a swimlane move must name one of the canon channels"
            )
        if self.stalled_step == self.next_step:
            raise InvalidSwimlanesError(
                f"swimlane move {self.move_id!r} keeps the prospect on "
                f"{self.stalled_step!r}; a swimlane move must drive them to a "
                "different next step"
            )


@dataclass(frozen=True)
class SwimlanesPlan:
    """The canon's five-channel recovery plan over the stage 8 funnel.

    SPEC.md section 12.5 records the Swimlanes channel model as a canon gap
    cross-cutting over stages 8 to 10, used to recover stalled prospects across all
    channels. The plan is grounded on a same-tenant stage 8 ``FunnelIntegration``,
    binds a named owner and carries at least one typed ``SwimlaneMove`` per channel
    it uses. It reports the canon channels it covers and misses, so a plan that
    relies on one channel is visible as incomplete rather than presented as a whole
    recovery strategy.

    It is a planning decision, not a new required gate kind (a methodology-owner
    decision, SPEC.md section 12.5). It does not authorize sending, publishing,
    spend or traffic (SPEC.md sections 4 and 9) and it is never an observation
    (SPEC.md section 3).
    """

    plan_id: str
    tenant_id: str
    owner: str
    funnel: FunnelIntegration
    moves: tuple[SwimlaneMove, ...]

    def __post_init__(self) -> None:
        for label, value in (
            ("swimlanes plan id", self.plan_id),
            ("swimlanes plan tenant id", self.tenant_id),
            ("swimlanes plan owner", self.owner),
        ):
            if not value or not value.strip():
                raise InvalidSwimlanesError(f"{label} is required")
        if not isinstance(self.funnel, FunnelIntegration):
            raise SwimlanesDependencyError(
                "a swimlanes plan must be grounded on a typed stage 8 funnel, "
                "not a free-text reference"
            )
        if self.funnel.tenant_id != self.tenant_id:
            raise SwimlanesTenantBoundaryError(
                f"swimlanes plan {self.plan_id!r} belongs to tenant "
                f"{self.tenant_id!r}, but its funnel "
                f"{self.funnel.integration_id!r} belongs to tenant "
                f"{self.funnel.tenant_id!r}"
            )
        if not self.moves:
            raise InvalidSwimlanesError(
                "a swimlanes plan requires at least one recovery move"
            )
        seen: set[str] = set()
        for move in self.moves:
            if not isinstance(move, SwimlaneMove):
                raise InvalidSwimlanesError(
                    "a swimlanes plan move must be a typed swimlane move"
                )
            if move.tenant_id != self.tenant_id:
                raise SwimlanesTenantBoundaryError(
                    f"swimlanes plan {self.plan_id!r} belongs to tenant "
                    f"{self.tenant_id!r}, but move {move.move_id!r} belongs to "
                    f"tenant {move.tenant_id!r}"
                )
            if move.move_id in seen:
                raise InvalidSwimlanesError(
                    f"swimlanes plan {self.plan_id!r} repeats move id "
                    f"{move.move_id!r}"
                )
            seen.add(move.move_id)

    @property
    def covered_channels(self) -> tuple[SwimlaneChannel, ...]:
        """The canon channels the plan's moves already use, in canon order."""
        used = {move.channel for move in self.moves}
        return tuple(
            channel for channel in SWIMLANE_CHANNELS if channel in used
        )

    def missing_channels(self) -> tuple[SwimlaneChannel, ...]:
        """Canon channels the plan does not yet use."""
        covered = set(self.covered_channels)
        return tuple(
            channel for channel in SWIMLANE_CHANNELS if channel not in covered
        )

    @property
    def is_complete(self) -> bool:
        """True when the plan uses every canon channel, not a single source."""
        return not self.missing_channels()

    def moves_for(self, channel: SwimlaneChannel) -> tuple[SwimlaneMove, ...]:
        """The plan's recovery moves on one canon channel."""
        return tuple(move for move in self.moves if move.channel is channel)

    @property
    def is_plan(self) -> bool:
        """A swimlanes plan is a plan, not activity or an observed result."""
        return True

    def as_observation(self, *, claim_id: str) -> None:
        """Refuse to represent a swimlanes plan as an observed result.

        SPEC.md section 3 keeps observations distinct from conclusions. The plan
        describes the recovery moves that will run, while any measured movement is
        a separate observation, so a plan is never an observation.
        """
        raise SwimlanesObservationError(
            f"swimlanes plan {claim_id!r} is a recovery strategy to run, not an "
            "observed result, and cannot be recorded as an observation"
        )

    def as_stage_asset(self, *, version: int) -> StageAssetVersion:
        """Project the reviewed plan onto exact ``swimlanes-plan`` evidence.

        The methodology owner ruled the canon Swimlanes channel model a
        canon-informed required asset kind of the stage 8 "Funnel Complete" gate
        (owner decision 2026-10-04; SPEC.md sections 4 and 12.5). The reviewed plan
        is projected at a positive integer version, and a versionless projection is
        refused rather than silently pinned, so a passing stage 8 gate records the
        exact recovery strategy it approved (SPEC.md sections 3 and 4).
        """
        if not isinstance(version, int) or version < 1:
            raise InvalidSwimlanesError(
                "the swimlanes plan version must be a positive integer so the "
                "stage 8 gate can pin the reviewed asset at an exact version"
            )
        return StageAssetVersion(
            asset_id=self.plan_id,
            tenant_id=self.tenant_id,
            kind=SWIMLANES_PLAN_KIND,
            version=version,
        )
