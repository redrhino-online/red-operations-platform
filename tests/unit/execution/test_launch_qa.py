"""Behavioral tests for the LaunchQA aggregate (Execution domain).

Rules under test come from SPEC.md section 4, stage 9 "QA":
- The stage 9 checkpoint covers the recorded message, technical and commercial
  tests on desktop and mobile, forms, CRM, email, automation, booking, tracking,
  payment when relevant, handoff, client approval, budget, creative, dashboard
  and the launch decision.
- The "Launch Approved" checkpoint requires all critical path checks to pass,
  exceptions to have owners, and the designated human authority to authorize
  traffic.
- Phase 4 TDD example: "failed message, technical or commercial QA prevents
  Launch Approved".
- Stage 9 shows "Ready for Traffic", not live traffic or completion.
- The stage is grounded on the completed stage 8 FunnelIntegration (SPEC.md
  section 3: production requires approved dependencies).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.execution.domain.errors import (
    InvalidLaunchQAError,
    LaunchQAAuthorityError,
    LaunchQADependencyError,
    LaunchQAIncompleteError,
)
from redops.contexts.execution.domain.value_objects import (
    LaunchQAState,
    QACheckKind,
    QACheckOutcome,
)

from .fixtures import (
    authorization,
    complete_funnel,
    funnel_integration,
    launch_check,
    launch_checks,
    launch_qa,
    ready_for_traffic,
)


class LaunchApprovalTests(unittest.TestCase):
    def test_a_grounded_qa_with_passing_checks_is_ready_for_traffic(self):
        qa = launch_qa()

        approved = qa.authorize_traffic(authorization=authorization())

        self.assertIs(LaunchQAState.READY_FOR_TRAFFIC, approved.state)
        self.assertTrue(approved.is_ready_for_traffic)
        self.assertIsNotNone(approved.authorization)

    def test_failed_recorded_message_prevents_launch_approved(self):
        self._assert_failed_check_blocks(QACheckKind.RECORDED_MESSAGE)

    def test_failed_technical_qa_prevents_launch_approved(self):
        self._assert_failed_check_blocks(QACheckKind.TECHNICAL_DESKTOP)

    def test_failed_commercial_qa_prevents_launch_approved(self):
        self._assert_failed_check_blocks(QACheckKind.COMMERCIAL_DESKTOP)

    def _assert_failed_check_blocks(self, kind):
        checks = launch_checks({kind: QACheckOutcome.FAILED})

        with self.assertRaises(LaunchQAIncompleteError):
            launch_qa(checks=checks).authorize_traffic(
                authorization=authorization()
            )

    def test_a_missing_critical_check_prevents_launch_approved(self):
        partial = tuple(
            check
            for check in launch_checks()
            if check.kind is not QACheckKind.CRM
        )

        with self.assertRaises(LaunchQAIncompleteError):
            launch_qa(checks=partial).authorize_traffic(
                authorization=authorization()
            )

    def test_an_excepted_non_critical_check_with_an_owner_still_launches(self):
        checks = launch_checks({QACheckKind.PAYMENT: QACheckOutcome.EXCEPTED})

        approved = launch_qa(checks=checks).authorize_traffic(
            authorization=authorization()
        )

        self.assertIs(LaunchQAState.READY_FOR_TRAFFIC, approved.state)

    def test_an_exception_on_the_critical_path_does_not_launch(self):
        checks = launch_checks({QACheckKind.CRM: QACheckOutcome.EXCEPTED})

        with self.assertRaises(LaunchQAIncompleteError):
            launch_qa(checks=checks).authorize_traffic(
                authorization=authorization()
            )

    def test_an_exception_requires_a_named_owner(self):
        with self.assertRaises(InvalidLaunchQAError):
            launch_check(
                QACheckKind.PAYMENT,
                outcome=QACheckOutcome.EXCEPTED,
                owner="",
            )

    def test_launch_requires_a_complete_stage_8_funnel(self):
        draft = funnel_integration()

        with self.assertRaises(LaunchQADependencyError):
            launch_qa(funnel=draft).authorize_traffic(
                authorization=authorization()
            )

    def test_only_the_designated_authority_can_authorize_traffic(self):
        with self.assertRaises(LaunchQAAuthorityError):
            launch_qa().authorize_traffic(
                authorization=authorization(authorized_by="someone-else")
            )

    def test_the_qa_owner_cannot_be_the_designated_authority(self):
        with self.assertRaises(LaunchQAAuthorityError):
            launch_qa(designated_authority="qa-owner")

    def test_a_terminal_qa_cannot_authorize_traffic(self):
        with self.assertRaises(LaunchQADependencyError):
            launch_qa(state=LaunchQAState.ARCHIVED).authorize_traffic(
                authorization=authorization()
            )

    def test_duplicate_checks_are_rejected(self):
        duplicate = launch_checks() + (launch_check(QACheckKind.CRM),)

        with self.assertRaises(InvalidLaunchQAError):
            launch_qa(checks=duplicate)


class LaunchQAInvariantTests(unittest.TestCase):
    def test_a_qa_cannot_be_grounded_on_another_tenants_funnel(self):
        with self.assertRaises(LaunchQADependencyError):
            launch_qa(tenant_id="client-other")

    def test_a_qa_requires_identity_owner_and_authority(self):
        for override in (
            {"qa_id": "  "},
            {"owner": ""},
            {"designated_authority": "  "},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidLaunchQAError):
                    launch_qa(**override)

    def test_a_ready_qa_is_immutable(self):
        approved = ready_for_traffic()

        with self.assertRaises(FrozenInstanceError):
            approved.owner = "tampered"

    def test_a_ready_qa_can_be_marked_review_required(self):
        marked = ready_for_traffic().mark_review_required(
            reason="funnel changed"
        )

        self.assertIs(LaunchQAState.REVIEW_REQUIRED, marked.state)
        self.assertFalse(marked.is_ready_for_traffic)
        self.assertTrue(marked.review_reason)

    def test_marking_review_required_needs_a_reason(self):
        with self.assertRaises(InvalidLaunchQAError):
            ready_for_traffic().mark_review_required(reason="  ")

    def test_ready_for_traffic_is_not_live_traffic(self):
        approved = ready_for_traffic()

        self.assertIs(LaunchQAState.READY_FOR_TRAFFIC, approved.state)
        self.assertTrue(all(state.name != "LIVE" for state in LaunchQAState))

    def test_a_complete_funnel_is_grounded_by_default(self):
        self.assertTrue(complete_funnel().is_complete)


if __name__ == "__main__":
    unittest.main()
