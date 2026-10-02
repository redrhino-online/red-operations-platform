"""Behavioral tests for the StageRun aggregate (pure domain, Governance context).

Rules under test come from SPEC.md sections 3 and 4:
- StageRun records engagement, stage number, template version, owner, status,
  entered and exited timestamps (SPEC.md section 3 aggregate table).
- Stage completion requires gate acceptance, not merely activity.
- Passing a gate pins the exact required asset versions and downstream use.
- A failed or unapproved prerequisite blocks dependent authorization.
- Record transition actor, reason, timestamp, old and new version, correlation ID.
- Reject illegal transitions rather than silently coercing state.
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    StageRun,
)
from redops.contexts.governance.domain.errors import (
    IllegalStageTransitionError,
    StageGateNotAcceptedError,
)
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateDisposition,
    StageStatus,
    Waiver,
)

SCRIPT_V1 = AssetVersionRef("authority-amplifier-script", 1)
TODAY = date(2026, 10, 2)
DATE_DUE = date(2026, 10, 16)
CORRELATION = "corr-123"
SCOPE = "stage-8-funnel-integration"


def script_approval(expires_on=None):
    request = ApprovalRequest(
        asset=SCRIPT_V1,
        scope=SCOPE,
        requested_by="specialist-1",
        approver="client-approver-1",
        expires_on=expires_on,
    )
    request.approve(actor="client-approver-1", on=TODAY)
    return request


def accepted_decision(
    stage_number: int = 7,
    template_version: str = "2026.1",
    expires_on=None,
) -> GateDecision:
    return GateDecision(
        stage_number=stage_number,
        template_version=template_version,
        required_assets=frozenset({SCRIPT_V1}),
        checkpoint="Authority Amplifier Approved",
        checkpoint_evidence="authority-amplifier-approved-rubric passed",
        reviewer="client-approver-1",
        scope=SCOPE,
        disposition=GateDisposition.APPROVED,
        rationale="script and supported claims reviewed with the client",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=DATE_DUE,
        asset_approvals=(script_approval(expires_on),),
    )


def stage_run(**overrides) -> StageRun:
    values = {
        "engagement": "3f",
        "stage_number": 7,
        "template_version": "2026.1",
        "assigned_owner": "production-manager",
    }
    values.update(overrides)
    return StageRun(**values)


class StageRunLifecycleTests(unittest.TestCase):
    def test_new_stage_run_is_not_started(self):
        run = stage_run()

        self.assertIs(StageStatus.NOT_STARTED, run.status)
        self.assertIsNone(run.entered_at)
        self.assertIsNone(run.exited_at)

    def test_activity_starts_the_stage_but_never_completes_it(self):
        run = stage_run()

        run.record_activity(
            actor="specialist-1",
            reason="drafting the script",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        self.assertIs(StageStatus.WORKING, run.status)
        self.assertEqual(TODAY, run.entered_at)
        self.assertFalse(run.is_complete)

    def test_activity_on_an_in_review_stage_does_not_complete_it(self):
        run = stage_run()
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)
        run.submit_for_review(
            actor="specialist-1", reason="ready for review", on=TODAY, correlation_id=CORRELATION
        )

        run.record_activity(
            actor="specialist-1",
            reason="more edits while waiting",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        self.assertIs(StageStatus.IN_REVIEW, run.status)
        self.assertFalse(run.is_complete)


class StageCompletionRequiresGateTests(unittest.TestCase):
    def test_working_stage_cannot_complete_without_a_passing_decision(self):
        run = stage_run()
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)

        blocked = GateDecision(
            stage_number=7,
            template_version="2026.1",
            required_assets=frozenset({SCRIPT_V1}),
            checkpoint="Authority Amplifier Approved",
            checkpoint_evidence="review outstanding",
            reviewer="client-approver-1",
            scope="stage-8-funnel-integration",
            disposition=GateDisposition.BLOCKED,
            rationale="dependency not approved",
            decided_on=TODAY,
            assigned_owner="production-manager",
            due_on=DATE_DUE,
        )

        with self.assertRaises(StageGateNotAcceptedError):
            run.complete(
                decision=blocked,
                actor="specialist-1",
                reason="looks done",
                on=TODAY,
                correlation_id=CORRELATION,
            )

        self.assertIs(StageStatus.WORKING, run.status)
        self.assertFalse(run.is_complete)

    def test_a_waived_decision_never_completes_a_stage(self):
        run = stage_run()
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)

        waived = GateDecision(
            stage_number=7,
            template_version="2026.1",
            required_assets=frozenset({SCRIPT_V1}),
            checkpoint="Authority Amplifier Approved",
            checkpoint_evidence="video delayed by vendor",
            reviewer="client-approver-1",
            scope="stage-8-funnel-integration",
            disposition=GateDisposition.WAIVED,
            rationale="scoped client waiver",
            decided_on=TODAY,
            assigned_owner="production-manager",
            due_on=DATE_DUE,
            waiver=Waiver(
                reason="video delayed by vendor",
                risk_owner="production-manager",
                review_trigger="vendor delivery",
            ),
        )

        with self.assertRaises(StageGateNotAcceptedError):
            run.complete(
                decision=waived,
                actor="specialist-1",
                reason="waived",
                on=TODAY,
                correlation_id=CORRELATION,
            )

        self.assertFalse(run.is_complete)

    def test_completion_requires_the_decision_for_this_exact_stage(self):
        run = stage_run(stage_number=7)
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)

        with self.assertRaises(StageGateNotAcceptedError):
            run.complete(
                decision=accepted_decision(stage_number=6),
                actor="specialist-1",
                reason="wrong stage decision",
                on=TODAY,
                correlation_id=CORRELATION,
            )

        self.assertFalse(run.is_complete)

    def test_completion_requires_the_decision_for_this_template_version(self):
        run = stage_run(template_version="2026.1")
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)

        with self.assertRaises(StageGateNotAcceptedError):
            run.complete(
                decision=accepted_decision(template_version="2025.9"),
                actor="specialist-1",
                reason="stale template decision",
                on=TODAY,
                correlation_id=CORRELATION,
            )

        self.assertFalse(run.is_complete)

    def test_a_passing_decision_completes_the_stage_and_pins_evidence(self):
        run = stage_run()
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)
        decision = accepted_decision(stage_number=7)

        run.complete(
            decision=decision,
            actor="client-approver-1",
            reason="gate approved",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        self.assertIs(StageStatus.COMPLETE, run.status)
        self.assertTrue(run.is_complete)
        self.assertEqual(TODAY, run.exited_at)
        self.assertIs(decision, run.accepted_decision)


class StageCompletionExpiryTests(unittest.TestCase):
    """Stage completion is evaluated at the transition instant.

    SPEC.md section 4: "a failed or expired prerequisite blocks dependent
    authorization until resolved". Completing the stage is exactly the
    downstream authorization the accepted decision grants, so stale, expired
    evidence can no longer be used to complete a stage on a later date.
    """

    AFTER_EXPIRY = date(2026, 10, 17)

    def test_a_stage_cannot_complete_on_expired_accepted_evidence(self):
        run = stage_run()
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)
        decision = accepted_decision(expires_on=DATE_DUE)

        with self.assertRaises(StageGateNotAcceptedError):
            run.complete(
                decision=decision,
                actor="client-approver-1",
                reason="accepting after the approvals lapsed",
                on=self.AFTER_EXPIRY,
                correlation_id=CORRELATION,
            )

        self.assertIs(StageStatus.WORKING, run.status)
        self.assertFalse(run.is_complete)
        self.assertIsNone(run.exited_at)
        self.assertIsNone(run.accepted_decision)

    def test_a_stage_can_complete_while_accepted_evidence_is_effective(self):
        run = stage_run()
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)
        decision = accepted_decision(expires_on=DATE_DUE)

        run.complete(
            decision=decision,
            actor="client-approver-1",
            reason="gate approved within the evidence window",
            on=DATE_DUE,
            correlation_id=CORRELATION,
        )

        self.assertIs(StageStatus.COMPLETE, run.status)
        self.assertIs(decision, run.accepted_decision)


class StageTransitionIntegrityTests(unittest.TestCase):
    def test_starting_an_already_working_stage_is_rejected(self):
        run = stage_run()
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)

        with self.assertRaises(IllegalStageTransitionError):
            run.start(actor="specialist-1", reason="begin again", on=TODAY, correlation_id=CORRELATION)

    def test_completing_a_not_started_stage_is_rejected(self):
        with self.assertRaises(IllegalStageTransitionError):
            stage_run().complete(
                decision=accepted_decision(stage_number=7),
                actor="client-approver-1",
                reason="nothing was produced",
                on=TODAY,
                correlation_id=CORRELATION,
            )

    def test_superseded_stage_cannot_transition_again(self):
        run = stage_run()
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)
        run.complete(
            decision=accepted_decision(stage_number=7),
            actor="client-approver-1",
            reason="approved",
            on=TODAY,
            correlation_id=CORRELATION,
        )
        run.supersede(actor="governance-manager", reason="method changed", on=TODAY, correlation_id=CORRELATION)

        with self.assertRaises(IllegalStageTransitionError):
            run.start(actor="specialist-1", reason="restart", on=TODAY, correlation_id=CORRELATION)


class StageTransitionRecordTests(unittest.TestCase):
    def test_transitions_record_actor_reason_time_and_correlation_id(self):
        run = stage_run()
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)

        self.assertEqual(1, len(run.transitions))
        transition = run.transitions[0]
        self.assertEqual("specialist-1", transition.actor)
        self.assertEqual("begin", transition.reason)
        self.assertEqual(TODAY, transition.occurred_at)
        self.assertEqual(CORRELATION, transition.correlation_id)
        self.assertIs(StageStatus.NOT_STARTED, transition.old_status)
        self.assertIs(StageStatus.WORKING, transition.new_status)

    def test_transition_history_is_immutable(self):
        run = stage_run()
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)

        self.assertIsInstance(run.transitions, tuple)


if __name__ == "__main__":
    unittest.main()
