"""Behavioral tests for version-specific approvals and the append-only decision record.

Rules under test come from SPEC.md sections 3, 4 and 11:
- Approval is version specific: approving version A cannot approve version B.
- An author cannot impersonate the approver; an unauthorized approval is rejected.
- Approval pins the exact asset version and intended downstream use (scope).
- Expired or superseded approvals do not authorize.
- Decision history is append only; a superseded approval's entry remains.
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    DecisionLog,
)
from redops.contexts.governance.domain.errors import (
    ApprovalAuthorityError,
    ApprovalExpiredError,
    SelfApprovalError,
)
from redops.contexts.governance.domain.value_objects import (
    ApprovalOutcome,
    AssetVersionRef,
)

SCRIPT_V1 = AssetVersionRef("authority-amplifier-script", 1)
SCRIPT_V2 = AssetVersionRef("authority-amplifier-script", 2)
SCOPE = "authority-amplifier-script-production"
TODAY = date(2026, 10, 2)


def request(**overrides):
    values = {
        "asset": SCRIPT_V1,
        "scope": SCOPE,
        "requested_by": "specialist-1",
        "approver": "client-approver-1",
    }
    values.update(overrides)
    return ApprovalRequest(**values)


class ApprovalVersionSpecificityTests(unittest.TestCase):
    def test_approving_version_one_does_not_authorize_version_two(self):
        approval = request()
        approval.approve(actor="client-approver-1", on=TODAY)

        self.assertTrue(approval.authorizes(SCRIPT_V1, SCOPE, TODAY))
        self.assertFalse(approval.authorizes(SCRIPT_V2, SCOPE, TODAY))

    def test_approval_only_authorizes_its_declared_scope(self):
        approval = request()
        approval.approve(actor="client-approver-1", on=TODAY)

        self.assertFalse(approval.authorizes(SCRIPT_V1, "different-use", TODAY))

    def test_pending_approval_does_not_authorize(self):
        approval = request()

        self.assertFalse(approval.authorizes(SCRIPT_V1, SCOPE, TODAY))


class ApprovalAuthorityTests(unittest.TestCase):
    def test_author_cannot_be_the_designated_approver(self):
        with self.assertRaises(SelfApprovalError):
            request(approver="specialist-1")

    def test_only_the_designated_approver_can_approve(self):
        approval = request()

        with self.assertRaises(ApprovalAuthorityError):
            approval.approve(actor="someone-else", on=TODAY)

    def test_expired_approval_cannot_be_approved_or_authorize(self):
        approval = request(expires_on=date(2026, 9, 30))

        with self.assertRaises(ApprovalExpiredError):
            approval.approve(actor="client-approver-1", on=TODAY)
        self.assertFalse(approval.authorizes(SCRIPT_V1, SCOPE, TODAY))

    def test_approval_stops_authorizing_after_expiry(self):
        approval = request(expires_on=date(2026, 10, 1))
        approval.approve(actor="client-approver-1", on=date(2026, 10, 1))

        self.assertFalse(approval.authorizes(SCRIPT_V1, SCOPE, date(2026, 10, 2)))


class DecisionHistoryTests(unittest.TestCase):
    def test_superseding_retains_the_earlier_decision(self):
        log = DecisionLog()
        approval = request()
        log.record(approval.approve(actor="client-approver-1", on=TODAY))

        approval.supersede(
            actor="governance-manager",
            on=TODAY,
            rationale="method changed",
            log=log,
        )

        history = log.for_subject(SCRIPT_V1.asset_id)
        self.assertEqual(2, len(history))
        self.assertIn(ApprovalOutcome.APPROVED.value, [d.choice for d in history])
        self.assertIn(ApprovalOutcome.SUPERSEDED.value, [d.choice for d in history])

    def test_superseded_approval_does_not_authorize(self):
        approval = request()
        approval.approve(actor="client-approver-1", on=TODAY)
        approval.supersede(actor="governance-manager", on=TODAY, rationale="method changed")

        self.assertFalse(approval.authorizes(SCRIPT_V1, SCOPE, TODAY))

    def test_decision_log_exposes_an_immutable_history(self):
        log = DecisionLog()
        log.record(request().approve(actor="client-approver-1", on=TODAY))

        entries = log.entries
        self.assertIsInstance(entries, tuple)
        self.assertEqual(1, len(log.for_subject(SCRIPT_V1.asset_id)))


if __name__ == "__main__":
    unittest.main()
