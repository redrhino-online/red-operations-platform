"""Behavioral tests for the Operations notification delivery policy.

Rules under test come from SPEC.md section 7, "Command center intervention
fields":

- "Notifications are deduplicated and respect owner and quiet hours."

The policy is a pure Operations domain object. It reads open command center
intervention cards and caller-supplied quiet-hour preferences and decides, for
one local delivery moment, which cards become notifications. It never invents an
operator schedule: quiet hours are supplied by the caller and an owner without a
preference is treated as having none (SPEC.md sections 3, 9 and 12.2). A card
suppressed by quiet hours is recorded as a suppression rather than silently
dropped, and a previously delivered card is not delivered again across query
evaluations.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, time

from redops.contexts.operations.domain.errors import (
    InvalidNotificationError,
    InvalidQuietHoursError,
)
from redops.contexts.operations.domain.policies import (
    NotificationDeliveryPolicy,
    delivered_intervention_keys,
)
from redops.contexts.operations.domain.value_objects import (
    Intervention,
    InterventionReason,
    InterventionState,
    Notification,
    NotificationState,
    QuietHours,
)

ENGAGEMENT = "engagement-3f"
NINE_AM = datetime(2026, 10, 3, 9, 0)
MIDNIGHT = datetime(2026, 10, 3, 0, 0)


def card(
    *,
    reason: InterventionReason = InterventionReason.BLOCKED_CRITICAL_PATH,
    subject: str = "stage-0",
    owner: str = "production-manager",
    state: InterventionState = InterventionState.OPEN,
) -> Intervention:
    return Intervention(
        client=ENGAGEMENT,
        reason=reason,
        severity=reason.severity,
        subject=subject,
        explanation="surfaced for a stated reason",
        evidence=frozenset({"evidence-1"}),
        owner=owner,
        next_action="resolve it",
        state=state,
        resolution_note="handled" if state is InterventionState.DISMISSED else "",
    )


class DeliveryTests(unittest.TestCase):
    def test_an_open_card_outside_quiet_hours_is_delivered(self):
        hours = QuietHours(owner="production-manager", starts_at=time(20, 0), ends_at=time(8, 0))

        notifications = NotificationDeliveryPolicy().deliver(
            (card(),), at=NINE_AM, quiet_hours=(hours,)
        )

        self.assertEqual(1, len(notifications))
        notification = notifications[0]
        self.assertIs(NotificationState.DELIVERED, notification.state)
        self.assertEqual(ENGAGEMENT, notification.client)
        self.assertEqual("stage-0", notification.subject)
        self.assertEqual("production-manager", notification.owner)
        self.assertEqual(NINE_AM, notification.at)
        self.assertFalse(notification.suppression_reason)

    def test_a_card_inside_quiet_hours_is_suppressed_and_recorded(self):
        hours = QuietHours(owner="production-manager", starts_at=time(8, 0), ends_at=time(18, 0))

        notifications = NotificationDeliveryPolicy().deliver(
            (card(),), at=NINE_AM, quiet_hours=(hours,)
        )

        self.assertEqual(1, len(notifications))
        notification = notifications[0]
        self.assertIs(NotificationState.SUPPRESSED, notification.state)
        self.assertTrue(notification.suppression_reason)
        self.assertIn("production-manager", notification.suppression_reason)

    def test_quiet_hours_crossing_midnight_suppress_on_both_sides(self):
        hours = QuietHours(owner="production-manager", starts_at=time(22, 0), ends_at=time(7, 0))
        policy = NotificationDeliveryPolicy()

        late = policy.deliver((card(),), at=datetime(2026, 10, 3, 23, 0), quiet_hours=(hours,))
        early = policy.deliver((card(),), at=datetime(2026, 10, 3, 6, 0), quiet_hours=(hours,))
        midday = policy.deliver((card(),), at=datetime(2026, 10, 3, 12, 0), quiet_hours=(hours,))

        self.assertIs(NotificationState.SUPPRESSED, late[0].state)
        self.assertIs(NotificationState.SUPPRESSED, early[0].state)
        self.assertIs(NotificationState.DELIVERED, midday[0].state)

    def test_quiet_hours_are_half_open_at_start_and_end(self):
        hours = QuietHours(owner="production-manager", starts_at=time(9, 0), ends_at=time(9, 30))
        policy = NotificationDeliveryPolicy()

        at_start = policy.deliver((card(),), at=datetime(2026, 10, 3, 9, 0), quiet_hours=(hours,))
        at_end = policy.deliver((card(),), at=datetime(2026, 10, 3, 9, 30), quiet_hours=(hours,))

        self.assertIs(NotificationState.SUPPRESSED, at_start[0].state)
        self.assertIs(NotificationState.DELIVERED, at_end[0].state)

    def test_an_owner_without_a_preference_has_no_quiet_hours(self):
        notifications = NotificationDeliveryPolicy().deliver((card(),), at=NINE_AM)

        self.assertIs(NotificationState.DELIVERED, notifications[0].state)

    def test_quiet_hours_for_another_owner_do_not_suppress_this_owner(self):
        hours = QuietHours(owner="other-operator", starts_at=time(8, 0), ends_at=time(18, 0))

        notifications = NotificationDeliveryPolicy().deliver(
            (card(),), at=NINE_AM, quiet_hours=(hours,)
        )

        self.assertIs(NotificationState.DELIVERED, notifications[0].state)

    def test_each_open_card_produces_its_own_notification(self):
        cards = (
            card(subject="stage-0"),
            card(reason=InterventionReason.OVERDUE_APPROVAL, subject="stage-1"),
        )

        notifications = NotificationDeliveryPolicy().deliver(cards, at=NINE_AM)

        self.assertEqual(2, len(notifications))
        self.assertEqual(
            ("stage-0", "stage-1"),
            tuple(n.subject for n in notifications),
        )


class DeduplicationTests(unittest.TestCase):
    def test_a_previously_delivered_card_is_not_notified_again(self):
        first = NotificationDeliveryPolicy().deliver((card(),), at=NINE_AM)
        delivered = delivered_intervention_keys(first)

        second = NotificationDeliveryPolicy().deliver(
            (card(),), at=NINE_AM, already_delivered=delivered
        )

        self.assertEqual(1, len(first))
        self.assertEqual((), second)

    def test_duplicate_cards_within_one_batch_produce_one_notification(self):
        notifications = NotificationDeliveryPolicy().deliver(
            (card(), card()), at=NINE_AM
        )

        self.assertEqual(1, len(notifications))

    def test_the_same_subject_under_a_different_reason_is_not_deduplicated(self):
        cards = (
            card(reason=InterventionReason.BLOCKED_CRITICAL_PATH, subject="stage-0"),
            card(reason=InterventionReason.OVERDUE_APPROVAL, subject="stage-0"),
        )

        notifications = NotificationDeliveryPolicy().deliver(cards, at=NINE_AM)

        self.assertEqual(2, len(notifications))

    def test_a_suppressed_card_is_not_treated_as_delivered(self):
        hours = QuietHours(owner="production-manager", starts_at=time(8, 0), ends_at=time(18, 0))
        policy = NotificationDeliveryPolicy()

        suppressed = policy.deliver((card(),), at=NINE_AM, quiet_hours=(hours,))
        delivered = delivered_intervention_keys(suppressed)
        later = policy.deliver(
            (card(),),
            at=datetime(2026, 10, 3, 19, 0),
            quiet_hours=(hours,),
            already_delivered=delivered,
        )

        self.assertEqual(frozenset(), delivered)
        self.assertIs(NotificationState.DELIVERED, later[0].state)


class OnlyOpenCardsNotifyTests(unittest.TestCase):
    def test_a_dismissed_card_is_not_notified(self):
        dismissed = card().dismiss("already handled")

        notifications = NotificationDeliveryPolicy().deliver((dismissed,), at=NINE_AM)

        self.assertEqual((), notifications)

    def test_a_resolved_card_is_not_notified(self):
        resolved = Intervention(
            client=ENGAGEMENT,
            reason=InterventionReason.BLOCKED_CRITICAL_PATH,
            severity=InterventionReason.BLOCKED_CRITICAL_PATH.severity,
            subject="stage-0",
            explanation="resolved already",
            evidence=frozenset({"evidence-1"}),
            owner="production-manager",
            next_action="none",
            state=InterventionState.RESOLVED,
            resolution_note="resolved by the operator",
        )

        notifications = NotificationDeliveryPolicy().deliver((resolved,), at=NINE_AM)

        self.assertEqual((), notifications)


class QuietHoursInvariantTests(unittest.TestCase):
    def test_quiet_hours_require_an_owner(self):
        with self.assertRaises(InvalidQuietHoursError):
            QuietHours(owner="  ", starts_at=time(8, 0), ends_at=time(18, 0))

    def test_quiet_hours_cannot_start_and_end_at_the_same_time(self):
        with self.assertRaises(InvalidQuietHoursError):
            QuietHours(owner="production-manager", starts_at=time(8, 0), ends_at=time(8, 0))

    def test_quiet_hours_require_time_values(self):
        with self.assertRaises(InvalidQuietHoursError):
            QuietHours(owner="production-manager", starts_at="08:00", ends_at=time(18, 0))

    def test_duplicate_preferences_for_one_owner_are_refused(self):
        hours = QuietHours(owner="production-manager", starts_at=time(8, 0), ends_at=time(18, 0))

        with self.assertRaises(InvalidQuietHoursError):
            NotificationDeliveryPolicy().deliver(
                (card(),), at=NINE_AM, quiet_hours=(hours, hours)
            )


class NotificationInvariantTests(unittest.TestCase):
    def test_a_delivered_notification_cannot_carry_a_suppression_reason(self):
        with self.assertRaises(InvalidNotificationError):
            Notification(
                client=ENGAGEMENT,
                reason=InterventionReason.BLOCKED_CRITICAL_PATH,
                subject="stage-0",
                owner="production-manager",
                at=NINE_AM,
                state=NotificationState.DELIVERED,
                suppression_reason="quiet hours",
            )

    def test_a_suppressed_notification_requires_a_reason(self):
        with self.assertRaises(InvalidNotificationError):
            Notification(
                client=ENGAGEMENT,
                reason=InterventionReason.BLOCKED_CRITICAL_PATH,
                subject="stage-0",
                owner="production-manager",
                at=NINE_AM,
                state=NotificationState.SUPPRESSED,
            )

    def test_a_notification_requires_its_identification_fields(self):
        base = {
            "client": ENGAGEMENT,
            "reason": InterventionReason.BLOCKED_CRITICAL_PATH,
            "subject": "stage-0",
            "owner": "production-manager",
            "at": NINE_AM,
            "state": NotificationState.DELIVERED,
        }
        for field in ("client", "subject", "owner"):
            broken = dict(base)
            broken[field] = " "
            with self.subTest(field=field):
                with self.assertRaises(InvalidNotificationError):
                    Notification(**broken)

    def test_a_notification_is_immutable(self):
        notification = Notification(
            client=ENGAGEMENT,
            reason=InterventionReason.BLOCKED_CRITICAL_PATH,
            subject="stage-0",
            owner="production-manager",
            at=NINE_AM,
            state=NotificationState.DELIVERED,
        )

        with self.assertRaises(FrozenInstanceError):
            notification.owner = "other"

    def test_a_notification_key_matches_the_intervention_key(self):
        notification = Notification(
            client=ENGAGEMENT,
            reason=InterventionReason.BLOCKED_CRITICAL_PATH,
            subject="stage-0",
            owner="production-manager",
            at=NINE_AM,
            state=NotificationState.DELIVERED,
        )

        self.assertEqual(card().key, notification.key)


if __name__ == "__main__":
    unittest.main()
