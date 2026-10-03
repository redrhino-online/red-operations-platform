"""Behavioral tests for the intervention dismissal decision (Operations domain).

SPEC.md section 7 allows a command center card to be dismissed with rationale;
SPEC.md section 9 keeps an operator decision from being lost. The derived cards
are recomputed on every read, so the durable value object is the dismissal
decision itself. These tests pin its fields, its tenant/client boundary and its
deduplication key.
"""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.operations.domain.errors import (
    InvalidInterventionDismissalError,
)
from redops.contexts.operations.domain.value_objects import (
    InterventionDismissal,
    InterventionReason,
)

DISMISSED_ON = date(2026, 10, 3)


def dismissal(**overrides) -> InterventionDismissal:
    values = {
        "tenant_id": "tenant-3f",
        "client": "engagement-3f",
        "reason": InterventionReason.BLOCKED_CRITICAL_PATH,
        "subject": "stage-3",
        "rationale": "the blocker is being handled off-platform",
        "actor": "production-manager",
        "dismissed_on": DISMISSED_ON,
    }
    values.update(overrides)
    return InterventionDismissal(**values)


class InterventionDismissalTests(unittest.TestCase):
    def test_a_dismissal_exposes_the_card_key_it_suppresses(self):
        record = dismissal()

        self.assertEqual(
            ("engagement-3f", "blocked_critical_path", "stage-3"), record.key
        )

    def test_every_required_field_is_enforced(self):
        for field in (
            "tenant_id",
            "client",
            "subject",
            "rationale",
            "actor",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidInterventionDismissalError):
                    dismissal(**{field: "   "})

    def test_the_reason_must_be_typed(self):
        with self.assertRaises(InvalidInterventionDismissalError):
            dismissal(reason="blocked_critical_path")

    def test_the_dismissal_date_must_be_a_date(self):
        with self.assertRaises(InvalidInterventionDismissalError):
            dismissal(dismissed_on="2026-10-03")

    def test_a_dismissal_is_immutable(self):
        record = dismissal()

        with self.assertRaises(FrozenInstanceError):
            record.rationale = "changed"  # type: ignore[misc]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
