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
    GateLedger,
    StageRun,
)
from redops.contexts.governance.domain.errors import (
    IllegalStageTransitionError,
    StageGateNotAcceptedError,
)
from redops.contexts.governance.domain.templates import (
    stage_zero_to_ten_template,
)
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateDisposition,
    StageStatus,
    StageTransition,
    Waiver,
)

SCRIPT_V1 = AssetVersionRef("authority-amplifier-script", 1)
TODAY = date(2026, 10, 2)
DATE_DUE = date(2026, 10, 16)
CORRELATION = "corr-123"
SCOPE = "stage-8-funnel-integration"
TEMPLATE = stage_zero_to_ten_template("2026.1")


def canonical_decision(
    stage_number: int,
    *,
    decided_on: date = TODAY,
    expires_on: date | None = None,
) -> GateDecision:
    definition = TEMPLATE.definition_for(stage_number)
    assets = frozenset(
        AssetVersionRef(kind, 1)
        for kind in TEMPLATE.required_asset_kinds(stage_number)
    )
    scope = f"stage-{stage_number + 1}-downstream"
    approvals = []
    for asset in assets:
        request = ApprovalRequest(
            asset=asset,
            scope=scope,
            requested_by="specialist-1",
            approver="client-approver-1",
            expires_on=expires_on,
        )
        request.approve(actor="client-approver-1", on=decided_on)
        approvals.append(request)
    return GateDecision(
        stage_number=stage_number,
        template_version="2026.1",
        required_assets=assets,
        checkpoint=definition.checkpoint,
        checkpoint_evidence=f"stage {stage_number} rubric passed",
        reviewer="client-approver-1",
        scope=scope,
        disposition=GateDisposition.APPROVED,
        rationale="reviewed against the canonical checkpoint",
        decided_on=decided_on,
        assigned_owner="production-manager",
        due_on=DATE_DUE,
        dependencies=TEMPLATE.dependencies_of(stage_number),
        asset_approvals=tuple(approvals),
    )


def prerequisite_ledger(expiries) -> GateLedger:
    ledger = GateLedger(TEMPLATE)
    for stage_number, expires_on in enumerate(expiries):
        ledger.record(
            canonical_decision(stage_number, expires_on=expires_on)
        )
    return ledger


def authorizing_ledger(decision: GateDecision | None = None) -> GateLedger:
    ledger = prerequisite_ledger([date(2026, 12, 31)] * 7)
    if decision is not None:
        ledger.record(decision)
    return ledger


def script_approval(expires_on=None, asset=SCRIPT_V1, scope=SCOPE):
    request = ApprovalRequest(
        asset=asset,
        scope=scope,
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
    definition = TEMPLATE.definition_for(stage_number)
    assets = frozenset(
        AssetVersionRef(kind, 1)
        for kind in TEMPLATE.required_asset_kinds(stage_number)
    )
    return GateDecision(
        stage_number=stage_number,
        template_version=template_version,
        required_assets=assets,
        checkpoint=definition.checkpoint,
        checkpoint_evidence="authority-amplifier-approved-rubric passed",
        reviewer="client-approver-1",
        scope=SCOPE,
        disposition=GateDisposition.APPROVED,
        rationale="script and supported claims reviewed with the client",
        decided_on=TODAY,
        assigned_owner="production-manager",
        due_on=DATE_DUE,
        dependencies=TEMPLATE.dependencies_of(stage_number),
        asset_approvals=tuple(
            script_approval(expires_on, asset=asset) for asset in assets
        ),
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
            dependencies=TEMPLATE.dependencies_of(7),
        )

        with self.assertRaises(StageGateNotAcceptedError):
            run.complete(
                decision=blocked,
                ledger=authorizing_ledger(),
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
            dependencies=TEMPLATE.dependencies_of(7),
            waiver=Waiver(
                reason="video delayed by vendor",
                risk_owner="production-manager",
                review_trigger="vendor delivery",
                downstream_effects=frozenset({"stage-8-funnel-integration"}),
            ),
        )

        with self.assertRaises(StageGateNotAcceptedError):
            run.complete(
                decision=waived,
                ledger=authorizing_ledger(),
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
                ledger=authorizing_ledger(),
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
                ledger=authorizing_ledger(),
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
            ledger=authorizing_ledger(decision),
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
                ledger=authorizing_ledger(),
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
            ledger=authorizing_ledger(decision),
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
        decision = accepted_decision(stage_number=7)
        with self.assertRaises(IllegalStageTransitionError):
            stage_run().complete(
                decision=decision,
                ledger=authorizing_ledger(decision),
                actor="client-approver-1",
                reason="nothing was produced",
                on=TODAY,
                correlation_id=CORRELATION,
            )

    def test_superseded_stage_cannot_transition_again(self):
        run = stage_run()
        run.start(actor="specialist-1", reason="begin", on=TODAY, correlation_id=CORRELATION)
        decision = accepted_decision(stage_number=7)
        run.complete(
            decision=decision,
            ledger=authorizing_ledger(decision),
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


class StageCompletionPrerequisiteTests(unittest.TestCase):
    """Stage completion consults the durable prerequisite chain.

    SPEC.md section 4 makes the 0-10 pipeline a dependency graph and says "a
    failed or expired prerequisite blocks dependent authorization until
    resolved". Completing a stage is the downstream authorization its accepted
    decision grants, so it must be refused while any transitive prerequisite
    stage is lapsed at the transition instant, even when the accepted decision's
    own pinned approvals are still current. Before this change StageRun.complete
    read only the accepted decision, which carries no upstream state, so a stage
    could complete on top of an expired prerequisite.
    """

    AFTER_UPSTREAM_EXPIRY = date(2026, 10, 20)

    def test_a_stage_cannot_complete_when_a_transitive_prerequisite_has_lapsed(self):
        decision = accepted_decision(stage_number=7)
        ledger = prerequisite_ledger(
            [date(2026, 10, 15)] + [date(2026, 12, 31)] * 6
        )
        ledger.record(decision)
        run = stage_run(stage_number=7)
        run.start(
            actor="specialist-1",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        with self.assertRaises(StageGateNotAcceptedError):
            run.complete(
                decision=decision,
                ledger=ledger,
                actor="client-approver-1",
                reason="accepting on top of an expired upstream stage",
                on=self.AFTER_UPSTREAM_EXPIRY,
                correlation_id=CORRELATION,
            )

        self.assertIs(StageStatus.WORKING, run.status)
        self.assertFalse(run.is_complete)
        self.assertIsNone(run.exited_at)
        self.assertIsNone(run.accepted_decision)

    def test_a_stage_cannot_complete_when_a_direct_prerequisite_has_lapsed(self):
        decision = accepted_decision(stage_number=7)
        ledger = prerequisite_ledger(
            [date(2026, 12, 31)] * 6 + [date(2026, 10, 15)]
        )
        ledger.record(decision)
        run = stage_run(stage_number=7)
        run.start(
            actor="specialist-1",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        with self.assertRaises(StageGateNotAcceptedError):
            run.complete(
                decision=decision,
                ledger=ledger,
                actor="client-approver-1",
                reason="immediate prerequisite lapsed",
                on=self.AFTER_UPSTREAM_EXPIRY,
                correlation_id=CORRELATION,
            )

        self.assertFalse(run.is_complete)

    def test_a_stage_completes_when_its_prerequisite_chain_authorizes(self):
        decision = accepted_decision(stage_number=7)
        ledger = prerequisite_ledger([date(2026, 12, 31)] * 7)
        ledger.record(decision)
        run = stage_run(stage_number=7)
        run.start(
            actor="specialist-1",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        run.complete(
            decision=decision,
            ledger=ledger,
            actor="client-approver-1",
            reason="gate approved with current prerequisites",
            on=self.AFTER_UPSTREAM_EXPIRY,
            correlation_id=CORRELATION,
        )

        self.assertIs(StageStatus.COMPLETE, run.status)
        self.assertTrue(run.is_complete)
        self.assertIs(decision, run.accepted_decision)


class StageCompletionDurabilityTests(unittest.TestCase):
    """Stage completion is authorized by the stage's durable ledger entry.

    SPEC.md section 3 makes a passing gate decision the durable, append-only
    record that pins the exact evidence and intended downstream use, and section
    4 says stage completion requires gate acceptance. A caller-supplied passing
    ``GateDecision`` the ledger never recorded is a transient object, not durable
    evidence, so it must not complete a stage. Likewise, when a later durable
    decision for the same stage supersedes the passing one, the stage's current
    ledger entry no longer authorizes completion even though the earlier passing
    decision once did.
    """

    def test_a_decision_not_recorded_in_the_ledger_cannot_complete_a_stage(self):
        run = stage_run(stage_number=7)
        run.start(
            actor="specialist-1",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )
        transient = accepted_decision(stage_number=7)
        ledger = prerequisite_ledger([date(2026, 12, 31)] * 7)

        with self.assertRaises(StageGateNotAcceptedError):
            run.complete(
                decision=transient,
                ledger=ledger,
                actor="client-approver-1",
                reason="accepting on a decision the ledger never recorded",
                on=TODAY,
                correlation_id=CORRELATION,
            )

        self.assertIs(StageStatus.WORKING, run.status)
        self.assertFalse(run.is_complete)
        self.assertIsNone(run.exited_at)
        self.assertIsNone(run.accepted_decision)

    def test_a_later_ledger_decision_supersedes_the_accepted_pass(self):
        decision = accepted_decision(stage_number=7)
        ledger = authorizing_ledger(decision)
        ledger.record(
            GateDecision(
                stage_number=7,
                template_version="2026.1",
                required_assets=frozenset(
                    AssetVersionRef(kind, 1)
                    for kind in TEMPLATE.required_asset_kinds(7)
                ),
                checkpoint=TEMPLATE.definition_for(7).checkpoint,
                checkpoint_evidence="",
                reviewer="client-approver-1",
                scope="",
                disposition=GateDisposition.CHANGES_REQUIRED,
                rationale="client requested changes after reviewing the cut",
                decided_on=TODAY,
                assigned_owner="production-manager",
                due_on=DATE_DUE,
                dependencies=TEMPLATE.dependencies_of(7),
            )
        )
        run = stage_run(stage_number=7)
        run.start(
            actor="specialist-1",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        with self.assertRaises(StageGateNotAcceptedError):
            run.complete(
                decision=decision,
                ledger=ledger,
                actor="client-approver-1",
                reason="completing on an entry the ledger has since superseded",
                on=TODAY,
                correlation_id=CORRELATION,
            )

        self.assertFalse(run.is_complete)

    def test_the_current_recorded_passing_decision_completes_the_stage(self):
        decision = accepted_decision(stage_number=7)
        ledger = authorizing_ledger(decision)
        run = stage_run(stage_number=7)
        run.start(
            actor="specialist-1",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        run.complete(
            decision=decision,
            ledger=ledger,
            actor="client-approver-1",
            reason="the recorded decision authorizes downstream use",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        self.assertIs(StageStatus.COMPLETE, run.status)
        self.assertIs(decision, run.accepted_decision)


class StageWaiverTests(unittest.TestCase):
    """A stage-level mirror of a scoped gate waiver.

    SPEC.md section 4 lists ``Waived`` among the stage states and requires a
    waiver to be a scoped human decision with a reason, risk owner, expiry or
    review trigger, and downstream effects; a waiver never makes an absent asset
    appear present. ``StageTransitionPolicy`` already permits
    ``WORKING -> WAIVED`` and ``WAIVED -> SUPERSEDED``, but ``StageRun`` exposed
    no ``waive()`` transition, so the stage state machine could not mirror a gate
    waiver and the production view could not show a waived stage.
    """

    SCOPE = "stage-8-funnel-integration"

    def waiver(self, **overrides) -> Waiver:
        values = {
            "reason": "video delayed by vendor",
            "risk_owner": "production-manager",
            "review_trigger": "vendor delivery",
            "downstream_effects": frozenset({self.SCOPE}),
        }
        values.update(overrides)
        return Waiver(**values)

    def working_run(self) -> StageRun:
        run = stage_run()
        run.start(
            actor="specialist-1",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )
        return run

    def waived_decision(
        self,
        *,
        stage_number: int = 7,
        template_version: str = "2026.1",
        waiver: Waiver | None = None,
        decided_on: date = TODAY,
    ) -> GateDecision:
        waiver = waiver if waiver is not None else self.waiver()
        definition = TEMPLATE.definition_for(stage_number)
        assets = frozenset(
            AssetVersionRef(kind, 1)
            for kind in TEMPLATE.required_asset_kinds(stage_number)
        )
        return GateDecision(
            stage_number=stage_number,
            template_version=template_version,
            required_assets=assets,
            checkpoint=definition.checkpoint,
            checkpoint_evidence="vendor delay recorded as a scoped waiver",
            reviewer="client-approver-1",
            scope=self.SCOPE,
            disposition=GateDisposition.WAIVED,
            rationale="risk accepted against the stage checkpoint",
            decided_on=decided_on,
            assigned_owner="production-manager",
            due_on=DATE_DUE,
            dependencies=TEMPLATE.dependencies_of(stage_number),
            waiver=waiver,
        )

    def waive(
        self, run: StageRun, *, decision=None, ledger=None, **overrides
    ) -> StageTransition:
        decision = decision if decision is not None else self.waived_decision()
        if ledger is None:
            ledger = authorizing_ledger(decision)
        values = {
            "waiver": decision.waiver,
            "decision": decision,
            "ledger": ledger,
            "actor": "client-approver-1",
            "on": TODAY,
            "correlation_id": CORRELATION,
        }
        values.update(overrides)
        return run.waive(**values)

    def test_waive_moves_a_working_stage_to_waived(self):
        run = self.working_run()

        self.waive(run)

        self.assertIs(StageStatus.WAIVED, run.status)
        self.assertFalse(run.is_complete)

    def test_waive_records_the_transition_with_the_waiver_reason(self):
        run = self.working_run()

        transition = self.waive(run)

        self.assertEqual("client-approver-1", transition.actor)
        self.assertEqual("video delayed by vendor", transition.reason)
        self.assertEqual(TODAY, transition.occurred_at)
        self.assertEqual(CORRELATION, transition.correlation_id)
        self.assertIs(StageStatus.WORKING, transition.old_status)
        self.assertIs(StageStatus.WAIVED, transition.new_status)

    def test_waive_never_completes_the_stage_or_pins_evidence(self):
        run = self.working_run()

        self.waive(run)

        self.assertIsNone(run.accepted_decision)
        self.assertIsNone(run.exited_at)

    def test_waive_requires_a_scoped_waiver(self):
        run = self.working_run()

        with self.assertRaises(ValueError):
            self.waive(run, waiver=None)

        self.assertIs(StageStatus.WORKING, run.status)

    def test_a_not_started_stage_cannot_be_waived(self):
        run = stage_run()

        with self.assertRaises(IllegalStageTransitionError):
            self.waive(run)

        self.assertIs(StageStatus.NOT_STARTED, run.status)

    def test_a_completed_stage_cannot_be_waived(self):
        decision = accepted_decision(stage_number=7)
        run = stage_run()
        run.start(
            actor="specialist-1",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )
        run.complete(
            decision=decision,
            ledger=authorizing_ledger(decision),
            actor="client-approver-1",
            reason="gate approved",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        with self.assertRaises(IllegalStageTransitionError):
            self.waive(run)

        self.assertIs(StageStatus.COMPLETE, run.status)

    def test_a_waived_stage_cannot_start_again(self):
        run = self.working_run()
        self.waive(run)

        with self.assertRaises(IllegalStageTransitionError):
            run.start(
                actor="specialist-1",
                reason="restart after waiver",
                on=TODAY,
                correlation_id=CORRELATION,
            )

        self.assertIs(StageStatus.WAIVED, run.status)

    def test_a_waived_stage_can_be_superseded(self):
        run = self.working_run()
        self.waive(run)

        run.supersede(
            actor="governance-manager",
            reason="method changed",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        self.assertIs(StageStatus.SUPERSEDED, run.status)

    def test_waive_requires_the_durable_ledger_decision(self):
        run = self.working_run()
        decision = self.waived_decision()

        with self.assertRaises(StageGateNotAcceptedError):
            self.waive(run, decision=decision, ledger=authorizing_ledger())

        self.assertIs(StageStatus.WORKING, run.status)

    def test_waive_rejects_a_ledger_for_another_template_version(self):
        run = self.working_run()

        with self.assertRaises(StageGateNotAcceptedError):
            self.waive(
                run,
                ledger=GateLedger(stage_zero_to_ten_template("2025.9")),
            )

        self.assertIs(StageStatus.WORKING, run.status)

    def test_waive_rejects_a_decision_for_another_stage(self):
        run = self.working_run()
        decision = self.waived_decision(stage_number=6)

        with self.assertRaises(StageGateNotAcceptedError):
            self.waive(run, decision=decision)

        self.assertIs(StageStatus.WORKING, run.status)

    def test_waive_rejects_a_decision_for_another_template_version(self):
        run = self.working_run()
        decision = self.waived_decision(template_version="2025.9")

        with self.assertRaises(StageGateNotAcceptedError):
            self.waive(run, decision=decision, ledger=authorizing_ledger())

        self.assertIs(StageStatus.WORKING, run.status)

    def test_waive_rejects_a_decision_that_is_not_a_waiver(self):
        run = self.working_run()
        decision = accepted_decision(stage_number=7)

        with self.assertRaises(StageGateNotAcceptedError):
            self.waive(run, decision=decision, waiver=self.waiver())

        self.assertIs(StageStatus.WORKING, run.status)

    def test_waive_rejects_a_decision_recorded_for_another_waiver(self):
        run = self.working_run()
        decision = self.waived_decision(waiver=self.waiver(reason="first"))

        with self.assertRaises(StageGateNotAcceptedError):
            self.waive(
                run,
                decision=decision,
                waiver=self.waiver(reason="second"),
            )

        self.assertIs(StageStatus.WORKING, run.status)

    def test_waive_requires_the_stages_current_recorded_decision(self):
        run = self.working_run()
        first = self.waived_decision(waiver=self.waiver(reason="first"))
        second = self.waived_decision(waiver=self.waiver(reason="second"))
        ledger = authorizing_ledger(first)
        ledger.record(second)

        with self.assertRaises(StageGateNotAcceptedError):
            self.waive(run, decision=first, ledger=ledger)

        self.assertIs(StageStatus.WORKING, run.status)

    def test_waive_refuses_a_waiver_that_has_expired(self):
        run = self.working_run()
        waiver = self.waiver(
            review_trigger="",
            expires_on=date(2026, 9, 30),
        )
        decision = self.waived_decision(
            waiver=waiver,
            decided_on=date(2026, 9, 30),
        )

        with self.assertRaises(StageGateNotAcceptedError):
            self.waive(run, decision=decision, waiver=waiver)

        self.assertIs(StageStatus.WORKING, run.status)

    def test_waive_accepts_a_waiver_expiring_on_the_transition_date(self):
        run = self.working_run()
        waiver = self.waiver(review_trigger="", expires_on=TODAY)
        decision = self.waived_decision(waiver=waiver)

        self.waive(run, decision=decision, waiver=waiver)

        self.assertIs(StageStatus.WAIVED, run.status)


class StageWaiverDecisionRetentionTests(unittest.TestCase):
    """The stage mirror keeps the durable waiver decision that produced it.

    SPEC.md section 4 makes the production view answer, for each client, "which
    dependency blocks work, what approval is next, and when it is due" and names
    ``Waived`` among the stage states; a waiver is a scoped human decision with a
    reason, risk owner, expiry or review trigger, and downstream effects. A
    completed stage retains its accepted ``GateDecision`` so the exact evidence is
    pinned     on the stage mirror. A waived stage is the symmetric case: without the
    waiver decision the stage cannot show who accepted the risk, when the waiver
    must be reviewed, or which effects it covers, and the stage state and the
    durable decision can drift.
    """

    SCOPE = "stage-8-funnel-integration"

    def waiver(self, **overrides) -> Waiver:
        values = {
            "reason": "video delayed by vendor",
            "risk_owner": "production-manager",
            "review_trigger": "vendor delivery",
            "downstream_effects": frozenset({self.SCOPE}),
        }
        values.update(overrides)
        return Waiver(**values)

    def working_run(self) -> StageRun:
        run = stage_run()
        run.start(
            actor="specialist-1",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )
        return run

    def waived_decision(self, *, waiver: Waiver | None = None) -> GateDecision:
        waiver = waiver if waiver is not None else self.waiver()
        definition = TEMPLATE.definition_for(7)
        assets = frozenset(
            AssetVersionRef(kind, 1)
            for kind in TEMPLATE.required_asset_kinds(7)
        )
        return GateDecision(
            stage_number=7,
            template_version="2026.1",
            required_assets=assets,
            checkpoint=definition.checkpoint,
            checkpoint_evidence="vendor delay recorded as a scoped waiver",
            reviewer="client-approver-1",
            scope=self.SCOPE,
            disposition=GateDisposition.WAIVED,
            rationale="risk accepted against the stage checkpoint",
            decided_on=TODAY,
            assigned_owner="production-manager",
            due_on=DATE_DUE,
            dependencies=TEMPLATE.dependencies_of(7),
            waiver=waiver,
        )

    def test_a_fresh_stage_run_retains_no_waiver_decision(self):
        self.assertIsNone(stage_run().waiver_decision)

    def test_waive_retains_the_durable_waiver_decision_on_the_stage(self):
        run = self.working_run()
        decision = self.waived_decision()

        run.waive(
            waiver=decision.waiver,
            decision=decision,
            ledger=authorizing_ledger(decision),
            actor="client-approver-1",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        self.assertIs(decision, run.waiver_decision)
        self.assertIsNone(run.accepted_decision)

    def test_the_retained_decision_carries_the_scoped_waiver_details(self):
        run = self.working_run()
        decision = self.waived_decision()

        run.waive(
            waiver=decision.waiver,
            decision=decision,
            ledger=authorizing_ledger(decision),
            actor="client-approver-1",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        retained = run.waiver_decision
        self.assertIsNotNone(retained)
        self.assertEqual("production-manager", retained.waiver.risk_owner)
        self.assertEqual("vendor delivery", retained.waiver.review_trigger)
        self.assertEqual(
            frozenset({self.SCOPE}), retained.waiver.downstream_effects
        )
        self.assertEqual("client-approver-1", retained.reviewer)

    def test_a_refused_waiver_retains_no_decision(self):
        run = self.working_run()

        with self.assertRaises(StageGateNotAcceptedError):
            run.waive(
                waiver=self.waiver(),
                decision=self.waived_decision(),
                ledger=authorizing_ledger(),
                actor="client-approver-1",
                on=TODAY,
                correlation_id=CORRELATION,
            )

        self.assertIsNone(run.waiver_decision)
        self.assertIs(StageStatus.WORKING, run.status)

    def test_completion_retains_the_accepted_decision_not_a_waiver_decision(self):
        decision = accepted_decision(stage_number=7)
        run = stage_run()
        run.start(
            actor="specialist-1",
            reason="begin",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        run.complete(
            decision=decision,
            ledger=authorizing_ledger(decision),
            actor="client-approver-1",
            reason="gate approved",
            on=TODAY,
            correlation_id=CORRELATION,
        )

        self.assertIs(decision, run.accepted_decision)
        self.assertIsNone(run.waiver_decision)


if __name__ == "__main__":
    unittest.main()
