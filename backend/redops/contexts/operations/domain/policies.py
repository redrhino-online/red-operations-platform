"""Command center intervention query and ranking (Operations pure domain).

SPEC.md section 7 requires the command center to surface, per client, the
blocked critical path, overdue approvals, failed live journeys and nearing
commitments, to show why each card is surfaced, to allow dismissal with
rationale, and to deduplicate notifications. This policy is a pure read over the
Governance ``EngagementProductionView`` (the stage status, owner, dependency and
due-date read model) plus caller-supplied live-journey and commitment signals;
the Execution, Measurement and Engagement contexts own those signals and this
query never invents them (SPEC.md sections 7, 12.1 and 12.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

from redops.contexts.governance.domain.value_objects import (
    EngagementProductionView,
    GateState,
    StageProductionView,
)
from redops.contexts.operations.domain.errors import (
    InvalidInterventionQueryError,
    InvalidQuietHoursError,
)
from redops.contexts.operations.domain.value_objects import (
    Commitment,
    Intervention,
    InterventionReason,
    InterventionState,
    JourneyFailure,
    Notification,
    NotificationState,
    QuietHours,
)

DEFAULT_NEARING_COMMITMENT_WINDOW_DAYS = 14


@dataclass(frozen=True)
class InterventionRankingPolicy:
    """Derive and rank command center intervention cards (SPEC.md section 7).

    The ranking follows the SPEC's stated favor: blocked critical path, overdue
    approvals, failed live journeys and nearing commitments. Cards are
    deduplicated on ``(client, reason, subject)`` so a signal reported twice (for
    example a retried worker) produces one card. The policy is a pure domain
    object: it reads the production view and the supplied signals, mutates
    nothing, and never fabricates an owner, a metric or a journey result.
    """

    nearing_commitment_window_days: int = DEFAULT_NEARING_COMMITMENT_WINDOW_DAYS

    def __post_init__(self) -> None:
        window = self.nearing_commitment_window_days
        if not isinstance(window, int) or isinstance(window, bool) or window < 1:
            raise InvalidInterventionQueryError(
                "the nearing-commitment window must be a positive number of days"
            )

    def rank(
        self,
        view: EngagementProductionView,
        *,
        on: date,
        failed_journeys: Iterable[JourneyFailure] = (),
        commitments: Iterable[Commitment] = (),
    ) -> tuple[Intervention, ...]:
        """Return the client's intervention cards, highest priority first."""
        candidates: list[Intervention] = []
        candidates.extend(self._blocked_cards(view))
        candidates.extend(self._overdue_cards(view, on=on))
        candidates.extend(self._journey_cards(view, failed_journeys))
        candidates.extend(self._commitment_cards(view, on=on, commitments=commitments))

        deduplicated: dict[tuple[str, str, str], Intervention] = {}
        for card in candidates:
            deduplicated.setdefault(card.key, card)
        return tuple(
            sorted(deduplicated.values(), key=self._sort_key)
        )

    def _blocked_cards(
        self, view: EngagementProductionView
    ) -> list[Intervention]:
        cards: list[Intervention] = []
        for stage in view.stages:
            if stage.status is not GateState.BLOCKED:
                continue
            evidence = set(stage.blockers)
            evidence.add(
                f"stage {stage.stage_number} ({stage.name}) is blocked at "
                f"checkpoint {stage.checkpoint}"
            )
            if stage.blocking_dependencies:
                blocked_by = ", ".join(
                    f"stage {number}"
                    for number in sorted(stage.blocking_dependencies)
                )
                evidence.add(f"blocked by {blocked_by}")
            cards.append(
                Intervention(
                    client=view.engagement,
                    reason=InterventionReason.BLOCKED_CRITICAL_PATH,
                    severity=InterventionReason.BLOCKED_CRITICAL_PATH.severity,
                    subject=f"stage-{stage.stage_number}",
                    explanation=(
                        f"Stage {stage.stage_number} ({stage.name}) is blocked at "
                        f"checkpoint {stage.checkpoint}; downstream work cannot be "
                        "authorized until it is resolved."
                    ),
                    evidence=frozenset(evidence),
                    owner=self._stage_owner(stage),
                    next_action=stage.next_action
                    or (
                        f"Resolve the blocker and record the {stage.checkpoint} "
                        "gate decision."
                    ),
                    due_on=stage.due_on,
                    affected_builds=self._dependent_stages(
                        view, stage.stage_number
                    ),
                )
            )
        return cards

    def _overdue_cards(
        self, view: EngagementProductionView, *, on: date
    ) -> list[Intervention]:
        cards: list[Intervention] = []
        for stage in view.stages:
            if stage.is_approved or stage.due_on is None or stage.due_on >= on:
                continue
            cards.append(
                Intervention(
                    client=view.engagement,
                    reason=InterventionReason.OVERDUE_APPROVAL,
                    severity=InterventionReason.OVERDUE_APPROVAL.severity,
                    subject=f"stage-{stage.stage_number}",
                    explanation=(
                        f"Stage {stage.stage_number} ({stage.name}) checkpoint "
                        f"{stage.checkpoint} was due {stage.due_on.isoformat()} and "
                        "is not approved."
                    ),
                    evidence=frozenset(
                        {f"{stage.checkpoint} due {stage.due_on.isoformat()}"}
                    ),
                    owner=self._stage_owner(stage),
                    next_action=stage.next_action
                    or f"Record the {stage.checkpoint} gate decision.",
                    due_on=stage.due_on,
                    affected_builds=self._dependent_stages(
                        view, stage.stage_number
                    ),
                )
            )
        return cards

    def _journey_cards(
        self,
        view: EngagementProductionView,
        failed_journeys: Iterable[JourneyFailure],
    ) -> list[Intervention]:
        cards: list[Intervention] = []
        for failure in failed_journeys:
            if failure.client != view.engagement:
                continue
            cards.append(
                Intervention(
                    client=view.engagement,
                    reason=InterventionReason.FAILED_LIVE_JOURNEY,
                    severity=InterventionReason.FAILED_LIVE_JOURNEY.severity,
                    subject=failure.journey_id,
                    explanation=(
                        f"Live journey {failure.journey_id} failed; the customer "
                        "path is not reliably converting."
                    ),
                    evidence=failure.evidence,
                    owner=failure.owner,
                    next_action=failure.next_action,
                    affected_builds=failure.affected_builds,
                )
            )
        return cards

    def _commitment_cards(
        self,
        view: EngagementProductionView,
        *,
        on: date,
        commitments: Iterable[Commitment],
    ) -> list[Intervention]:
        window_end = on + timedelta(days=self.nearing_commitment_window_days)
        cards: list[Intervention] = []
        for commitment in commitments:
            if commitment.client != view.engagement:
                continue
            if commitment.due_on < on or commitment.due_on > window_end:
                continue
            cards.append(
                Intervention(
                    client=view.engagement,
                    reason=InterventionReason.NEARING_COMMITMENT,
                    severity=InterventionReason.NEARING_COMMITMENT.severity,
                    subject=commitment.commitment_id,
                    explanation=(
                        f"Commitment {commitment.commitment_id!r} "
                        f"({commitment.description}) is due "
                        f"{commitment.due_on.isoformat()}."
                    ),
                    evidence=frozenset(
                        {f"{commitment.description} due {commitment.due_on.isoformat()}"}
                    ),
                    owner=commitment.owner,
                    next_action=commitment.next_action,
                    due_on=commitment.due_on,
                    affected_builds=commitment.affected_builds,
                )
            )
        return cards

    @staticmethod
    def _stage_owner(stage: StageProductionView) -> str:
        return stage.assigned_owner or stage.accountable_role

    @staticmethod
    def _dependent_stages(
        view: EngagementProductionView, stage_number: int
    ) -> frozenset[str]:
        """Stage keys of the stages blocked downstream of ``stage_number``.

        A blocked or overdue stage holds back the stages that depend on it,
        directly or transitively. The template is acyclic and every dependency
        points to an earlier stage, so the walk terminates.
        """
        dependents: set[int] = set()
        frontier = [stage_number]
        while frontier:
            current = frontier.pop()
            for stage in view.stages:
                if (
                    current in stage.dependencies
                    and stage.stage_number not in dependents
                ):
                    dependents.add(stage.stage_number)
                    frontier.append(stage.stage_number)
        return frozenset(f"stage-{number}" for number in dependents)

    @staticmethod
    def _sort_key(card: Intervention):
        return (
            card.reason.priority,
            card.due_on or date.max,
            card.key,
        )


def delivered_intervention_keys(
    notifications: Iterable[Notification],
) -> frozenset[tuple[str, str, str]]:
    """The keys of notifications that were actually delivered.

    A suppressed notification never reached its owner, so it must not count as
    delivered when deduplicating a later query evaluation: the card should be
    delivered once the owner is out of quiet hours (SPEC.md section 7).
    """
    return frozenset(
        notification.key
        for notification in notifications
        if notification.state is NotificationState.DELIVERED
    )


@dataclass(frozen=True)
class NotificationDeliveryPolicy:
    """Decide which intervention cards become notifications (SPEC.md section 7).

    SPEC.md section 7 requires notifications to be deduplicated and to respect
    owner and quiet hours. Given the open cards from one query evaluation, the
    caller-supplied quiet-hour preferences, the keys already delivered on prior
    evaluations, and the local delivery moment, this policy returns one
    notification per open card that has not already been delivered. A card whose
    owner is inside quiet hours is returned as a recorded suppression, never
    dropped, and re-evaluates as deliverable later. It is a pure domain object:
    it reads the cards and preferences, mutates nothing, and never invents an
    operator schedule.
    """

    def deliver(
        self,
        cards: Iterable[Intervention],
        *,
        at: datetime,
        quiet_hours: Iterable[QuietHours] = (),
        already_delivered: Iterable[tuple[str, str, str]] = (),
    ) -> tuple[Notification, ...]:
        """Return the notifications for one local delivery moment."""
        schedule = self._schedule(quiet_hours)
        notified = set(already_delivered)
        notifications: list[Notification] = []
        for card in cards:
            if card.state is not InterventionState.OPEN:
                continue
            if card.key in notified:
                continue
            notified.add(card.key)
            preference = schedule.get(card.owner)
            if preference is not None and preference.covers(at.time()):
                notifications.append(
                    Notification(
                        client=card.client,
                        reason=card.reason,
                        subject=card.subject,
                        owner=card.owner,
                        at=at,
                        state=NotificationState.SUPPRESSED,
                        suppression_reason=(
                            f"{card.owner} is inside quiet hours "
                            f"{preference.starts_at.strftime('%H:%M')}-"
                            f"{preference.ends_at.strftime('%H:%M')}"
                        ),
                    )
                )
                continue
            notifications.append(
                Notification(
                    client=card.client,
                    reason=card.reason,
                    subject=card.subject,
                    owner=card.owner,
                    at=at,
                    state=NotificationState.DELIVERED,
                )
            )
        return tuple(notifications)

    @staticmethod
    def _schedule(
        quiet_hours: Iterable[QuietHours],
    ) -> dict[str, QuietHours]:
        schedule: dict[str, QuietHours] = {}
        for preference in quiet_hours:
            if preference.owner in schedule:
                raise InvalidQuietHoursError(
                    f"owner {preference.owner!r} has more than one quiet-hours "
                    "preference"
                )
            schedule[preference.owner] = preference
        return schedule
