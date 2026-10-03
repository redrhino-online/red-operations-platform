"""Behavioral tests for the command center intervention query (Operations domain).

Rules under test come from SPEC.md section 7, "Command center intervention
fields":

- The intervention fields are "client, severity, reason, evidence, owner, next
  action, due time, state, affected builds".
- "Ranking favors blocked critical path, overdue approvals, failed live
  journeys, and nearing commitments."
- "Show why each card is surfaced and allow dismissal with rationale."
- "Notifications are deduplicated."

The query is a pure Operations read over the Governance production-manager view
plus caller-supplied live-journey and commitment signals. It never invents a
metric, an owner or a live-journey result: the Measurement and Execution
contexts own those signals and supply them.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    EngagementProductionView,
    GateDisposition,
)
from redops.contexts.operations.domain.errors import (
    InterventionDismissalError,
    InvalidInterventionError,
)
from redops.contexts.operations.domain.policies import InterventionRankingPolicy
from redops.contexts.operations.domain.value_objects import (
    Commitment,
    Intervention,
    InterventionReason,
    InterventionSeverity,
    InterventionState,
    JourneyFailure,
)

VERSION = "2026.1"
TODAY = date(2026, 10, 2)
DUE_IN_PAST = date(2026, 9, 25)
DUE_LATER = date(2026, 10, 16)
OVERDUE_ON = date(2026, 10, 20)
ENGAGEMENT = "engagement-3f"
TENANT = "tenant-3f"


def canonical_assets(stage_number: int) -> frozenset[AssetVersionRef]:
    kinds = stage_zero_to_ten_template(VERSION).required_asset_kinds(stage_number)
    return frozenset(AssetVersionRef(kind, 1) for kind in kinds)


def decision(
    stage_number: int,
    disposition: GateDisposition = GateDisposition.APPROVED,
    *,
    due_on: date = DUE_LATER,
    blockers=frozenset(),
) -> GateDecision:
    definition = stage_zero_to_ten_template(VERSION).definition_for(stage_number)
    assets = canonical_assets(stage_number)
    scope = f"stage-{stage_number + 1}-downstream"
    approvals = []
    for asset in assets:
        request = ApprovalRequest(
            asset=asset,
            scope=scope,
            requested_by="specialist-1",
            approver="client-approver-1",
        )
        request.approve(actor="client-approver-1", on=TODAY)
        approvals.append(request)
    return GateDecision(
        stage_number=stage_number,
        template_version=VERSION,
        required_assets=assets,
        checkpoint=definition.checkpoint,
        checkpoint_evidence=f"stage {stage_number} rubric result",
        reviewer="client-approver-1",
        scope=scope,
        disposition=disposition,
        rationale="recorded for the intervention query",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=due_on,
        dependencies=stage_zero_to_ten_template(VERSION).dependencies_of(
            stage_number
        ),
        next_action=f"advance stage {stage_number + 1}",
        asset_approvals=tuple(approvals),
        blockers=frozenset(blockers),
    )


def view(ledger: GateLedger) -> EngagementProductionView:
    return EngagementProductionView.from_ledger(
        ledger, engagement=ENGAGEMENT, tenant_id=TENANT, on=TODAY
    )


class EmptyPipelineInterventionTests(unittest.TestCase):
    def test_an_untouched_pipeline_surfaces_no_intervention(self):
        result = InterventionRankingPolicy().rank(
            view(GateLedger(stage_zero_to_ten_template(VERSION))), on=TODAY
        )

        self.assertEqual((), result)


class BlockedCriticalPathTests(unittest.TestCase):
    def test_a_blocked_stage_surfaces_a_blocked_critical_path_card(self):
        ledger = GateLedger(stage_zero_to_ten_template(VERSION))
        ledger.record(
            decision(
                0,
                GateDisposition.BLOCKED,
                blockers=frozenset({"required asset versions not approved"}),
            )
        )

        cards = InterventionRankingPolicy().rank(view(ledger), on=TODAY)

        self.assertEqual(1, len(cards))
        card = cards[0]
        self.assertEqual(ENGAGEMENT, card.client)
        self.assertIs(InterventionReason.BLOCKED_CRITICAL_PATH, card.reason)
        self.assertIs(InterventionSeverity.CRITICAL, card.severity)
        self.assertEqual("production-manager", card.owner)
        self.assertIn("required asset versions not approved", card.evidence)
        self.assertTrue(card.explanation)
        self.assertIn("stage-1", card.affected_builds)
        self.assertIn("stage-10", card.affected_builds)

    def test_a_blocked_stage_surfaces_once_not_once_per_dependent(self):
        ledger = GateLedger(stage_zero_to_ten_template(VERSION))
        ledger.record(decision(0, GateDisposition.BLOCKED))

        cards = InterventionRankingPolicy().rank(view(ledger), on=TODAY)

        blocked = [
            c for c in cards if c.reason is InterventionReason.BLOCKED_CRITICAL_PATH
        ]
        self.assertEqual(1, len(blocked))
        self.assertEqual("production-manager", blocked[0].owner)
        self.assertTrue(blocked[0].affected_builds)


class OverdueApprovalTests(unittest.TestCase):
    def test_a_stage_past_its_due_date_is_an_overdue_approval(self):
        ledger = GateLedger(stage_zero_to_ten_template(VERSION))
        ledger.record(
            decision(0, GateDisposition.CHANGES_REQUIRED, due_on=DUE_IN_PAST)
        )

        cards = InterventionRankingPolicy().rank(view(ledger), on=OVERDUE_ON)

        overdue = [c for c in cards if c.reason is InterventionReason.OVERDUE_APPROVAL]
        self.assertEqual(1, len(overdue))
        card = overdue[0]
        self.assertIs(InterventionSeverity.HIGH, card.severity)
        self.assertEqual(DUE_IN_PAST, card.due_on)
        self.assertEqual("production-manager", card.owner)
        self.assertIn("Production Ready", card.explanation)

    def test_a_future_due_date_is_not_overdue(self):
        ledger = GateLedger(stage_zero_to_ten_template(VERSION))
        ledger.record(
            decision(0, GateDisposition.CHANGES_REQUIRED, due_on=DUE_LATER)
        )

        cards = InterventionRankingPolicy().rank(view(ledger), on=TODAY)

        self.assertEqual((), cards)


class LiveJourneyAndCommitmentTests(unittest.TestCase):
    def test_a_failed_live_journey_surfaces_with_its_evidence(self):
        failure = JourneyFailure(
            journey_id="journey-3f",
            client=ENGAGEMENT,
            owner="campaign-operator",
            next_action="restore the conversion handoff",
            evidence=frozenset({"booking form returned 500"}),
            affected_builds=frozenset({"stage-8"}),
        )

        cards = InterventionRankingPolicy().rank(
            view(GateLedger(stage_zero_to_ten_template(VERSION))),
            on=TODAY,
            failed_journeys=(failure,),
        )

        self.assertEqual(1, len(cards))
        card = cards[0]
        self.assertIs(InterventionReason.FAILED_LIVE_JOURNEY, card.reason)
        self.assertEqual("journey-3f", card.subject)
        self.assertEqual("campaign-operator", card.owner)
        self.assertIn("booking form returned 500", card.evidence)
        self.assertEqual(frozenset({"stage-8"}), card.affected_builds)

    def test_a_journey_failure_for_another_client_is_not_surfaced(self):
        failure = JourneyFailure(
            journey_id="journey-other",
            client="engagement-other",
            owner="campaign-operator",
            next_action="restore",
            evidence=frozenset({"failed"}),
        )

        cards = InterventionRankingPolicy().rank(
            view(GateLedger(stage_zero_to_ten_template(VERSION))),
            on=TODAY,
            failed_journeys=(failure,),
        )

        self.assertEqual((), cards)

    def test_a_commitment_within_the_window_is_nearing(self):
        commitment = Commitment(
            commitment_id="launch-date",
            client=ENGAGEMENT,
            description="campaign live date",
            due_on=date(2026, 10, 9),
            owner="production-manager",
            next_action="confirm launch readiness",
        )

        cards = InterventionRankingPolicy(
            nearing_commitment_window_days=14
        ).rank(
            view(GateLedger(stage_zero_to_ten_template(VERSION))),
            on=TODAY,
            commitments=(commitment,),
        )

        self.assertEqual(1, len(cards))
        card = cards[0]
        self.assertIs(InterventionReason.NEARING_COMMITMENT, card.reason)
        self.assertEqual("launch-date", card.subject)
        self.assertEqual(date(2026, 10, 9), card.due_on)

    def test_a_commitment_beyond_the_window_is_not_nearing(self):
        commitment = Commitment(
            commitment_id="later-date",
            client=ENGAGEMENT,
            description="future commitment",
            due_on=date(2026, 12, 1),
            owner="production-manager",
            next_action="keep tracking",
        )

        cards = InterventionRankingPolicy().rank(
            view(GateLedger(stage_zero_to_ten_template(VERSION))),
            on=TODAY,
            commitments=(commitment,),
        )

        self.assertEqual((), cards)


class RankingAndDeduplicationTests(unittest.TestCase):
    def test_ranking_favors_blocked_then_overdue_then_failed_then_nearing(self):
        ledger = GateLedger(stage_zero_to_ten_template(VERSION))
        ledger.record(
            decision(0, GateDisposition.BLOCKED, due_on=DUE_IN_PAST)
        )
        failure = JourneyFailure(
            journey_id="journey-3f",
            client=ENGAGEMENT,
            owner="campaign-operator",
            next_action="restore",
            evidence=frozenset({"failed"}),
        )
        commitment = Commitment(
            commitment_id="live-date",
            client=ENGAGEMENT,
            description="live date",
            due_on=date(2026, 10, 25),
            owner="production-manager",
            next_action="confirm",
        )

        cards = InterventionRankingPolicy().rank(
            view(ledger),
            on=OVERDUE_ON,
            failed_journeys=(failure,),
            commitments=(commitment,),
        )

        self.assertEqual(
            (
                InterventionReason.BLOCKED_CRITICAL_PATH,
                InterventionReason.OVERDUE_APPROVAL,
                InterventionReason.FAILED_LIVE_JOURNEY,
                InterventionReason.NEARING_COMMITMENT,
            ),
            tuple(card.reason for card in cards),
        )

    def test_identical_signals_are_deduplicated(self):
        failure = JourneyFailure(
            journey_id="journey-3f",
            client=ENGAGEMENT,
            owner="campaign-operator",
            next_action="restore",
            evidence=frozenset({"failed"}),
        )

        cards = InterventionRankingPolicy().rank(
            view(GateLedger(stage_zero_to_ten_template(VERSION))),
            on=TODAY,
            failed_journeys=(failure, failure),
        )

        self.assertEqual(1, len(cards))

    def test_a_non_positive_window_is_refused(self):
        with self.assertRaises(ValueError):
            InterventionRankingPolicy(nearing_commitment_window_days=0)


class DismissalTests(unittest.TestCase):
    def test_a_card_can_be_dismissed_with_a_rationale(self):
        failure = JourneyFailure(
            journey_id="journey-3f",
            client=ENGAGEMENT,
            owner="campaign-operator",
            next_action="restore",
            evidence=frozenset({"failed"}),
        )
        card = InterventionRankingPolicy().rank(
            view(GateLedger(stage_zero_to_ten_template(VERSION))),
            on=TODAY,
            failed_journeys=(failure,),
        )[0]

        dismissed = card.dismiss("already handled by the operator")

        self.assertIs(InterventionState.OPEN, card.state)
        self.assertIs(InterventionState.DISMISSED, dismissed.state)
        self.assertEqual("already handled by the operator", dismissed.resolution_note)

    def test_a_dismissal_without_a_rationale_is_refused(self):
        card = Intervention(
            client=ENGAGEMENT,
            reason=InterventionReason.NEARING_COMMITMENT,
            severity=InterventionSeverity.MEDIUM,
            subject="live-date",
            explanation="due soon",
            evidence=frozenset({"due 2026-10-05"}),
            owner="production-manager",
            next_action="confirm",
        )

        with self.assertRaises(InterventionDismissalError):
            card.dismiss("  ")

    def test_an_already_dismissed_card_cannot_be_dismissed_again(self):
        card = Intervention(
            client=ENGAGEMENT,
            reason=InterventionReason.NEARING_COMMITMENT,
            severity=InterventionSeverity.MEDIUM,
            subject="live-date",
            explanation="due soon",
            evidence=frozenset({"due 2026-10-05"}),
            owner="production-manager",
            next_action="confirm",
        )
        dismissed = card.dismiss("handled")

        with self.assertRaises(InterventionDismissalError):
            dismissed.dismiss("again")


class InterventionInvariantTests(unittest.TestCase):
    def test_a_card_requires_client_owner_evidence_and_explanation(self):
        base = {
            "client": ENGAGEMENT,
            "reason": InterventionReason.NEARING_COMMITMENT,
            "severity": InterventionSeverity.MEDIUM,
            "subject": "live-date",
            "explanation": "due soon",
            "evidence": frozenset({"due 2026-10-05"}),
            "owner": "production-manager",
            "next_action": "confirm",
        }
        for field in ("client", "owner", "explanation", "subject"):
            broken = dict(base)
            broken[field] = " "
            with self.subTest(field=field):
                with self.assertRaises(InvalidInterventionError):
                    Intervention(**broken)

        no_evidence = dict(base)
        no_evidence["evidence"] = frozenset()
        with self.assertRaises(InvalidInterventionError):
            Intervention(**no_evidence)

    def test_a_card_is_immutable(self):
        card = Intervention(
            client=ENGAGEMENT,
            reason=InterventionReason.NEARING_COMMITMENT,
            severity=InterventionSeverity.MEDIUM,
            subject="live-date",
            explanation="due soon",
            evidence=frozenset({"due 2026-10-05"}),
            owner="production-manager",
            next_action="confirm",
        )

        with self.assertRaises(FrozenInstanceError):
            card.owner = "other"

    def test_a_card_key_deduplicates_on_client_reason_and_subject(self):
        card = Intervention(
            client=ENGAGEMENT,
            reason=InterventionReason.NEARING_COMMITMENT,
            severity=InterventionSeverity.MEDIUM,
            subject="live-date",
            explanation="due soon",
            evidence=frozenset({"due 2026-10-05"}),
            owner="production-manager",
            next_action="confirm",
        )

        self.assertEqual(
            (ENGAGEMENT, "nearing_commitment", "live-date"), card.key
        )


if __name__ == "__main__":
    unittest.main()
