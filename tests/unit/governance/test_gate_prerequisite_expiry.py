"""Behavioral tests for time-aware prerequisite authorization (Governance).

Rules under test come from SPEC.md section 4: the 0-10 pipeline is a gated
dependency graph and "a failed or expired prerequisite blocks dependent
authorization until resolved". A prerequisite stage that passed earlier only
authorizes a dependent stage while the exact asset approvals it pinned are
still unexpired at the instant the dependent gate is evaluated. Before this
change the ledger read only the prerequisite's latest disposition, so a
prerequisite whose approval had lapsed still appeared approved and could
authorize a dependent gate.

``GateDecision`` already refuses an expired approval through
``ApprovalRequest.authorizes`` at the instant it records a prerequisite, but the
same rule must hold when the dependency graph is traversed later. The ledger and
the decision therefore share one time-parameterized effectiveness check.
"""

import unittest
from datetime import date

from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
    StageGate,
)
from redops.contexts.governance.domain.errors import (
    GateDecisionError,
    UnsatisfiedPrerequisiteError,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    AssetVersionRef,
    GateDisposition,
    GateState,
    PipelineProgress,
)

VERSION = "2026.1"
DECIDED = date(2026, 10, 2)
LATER = date(2026, 10, 20)
DUE = date(2026, 11, 2)
TEMPLATE = stage_zero_to_ten_template(VERSION)


def canonical_assets(stage_number: int) -> frozenset[AssetVersionRef]:
    return frozenset(
        AssetVersionRef(kind, 1)
        for kind in TEMPLATE.required_asset_kinds(stage_number)
    )


def approvals(assets, scope, *, approved_on, expires_on):
    for asset in assets:
        request = ApprovalRequest(
            asset=asset,
            scope=scope,
            requested_by="specialist-1",
            approver="client-approver-1",
            expires_on=expires_on,
        )
        request.approve(actor="client-approver-1", on=approved_on)
        yield request


def passing(
    stage_number: int,
    *,
    decided_on: date = DECIDED,
    expires_on: date | None = None,
) -> GateDecision:
    definition = TEMPLATE.definition_for(stage_number)
    assets = canonical_assets(stage_number)
    scope = f"stage-{stage_number + 1}-downstream"
    return GateDecision(
        stage_number=stage_number,
        template_version=VERSION,
        required_assets=assets,
        checkpoint=definition.checkpoint,
        checkpoint_evidence=f"stage {stage_number} rubric passed",
        reviewer="client-approver-1",
        scope=scope,
        disposition=GateDisposition.APPROVED,
        rationale="reviewed against the checkpoint",
        decided_on=decided_on,
        assigned_owner="production-manager",
        due_on=DUE,
        dependencies=definition.dependencies,
        asset_approvals=tuple(
            approvals(
                assets,
                scope,
                approved_on=decided_on,
                expires_on=expires_on,
            )
        ),
    )


def approvable_gate(stage_number: int, scope: str) -> StageGate:
    versions = {kind: 1 for kind in TEMPLATE.required_asset_kinds(stage_number)}
    gate = StageGate.from_template(TEMPLATE, stage_number, versions)
    gate.state = GateState.APPROVED
    gate.proposed_by = "specialist-1"
    gate.approver = "client-approver-1"
    for asset in gate.required_assets:
        request = ApprovalRequest(
            asset=asset,
            scope=scope,
            requested_by="specialist-1",
            approver="client-approver-1",
        )
        request.approve(actor="client-approver-1", on=LATER)
        gate.record_asset_approval(request)
    return gate


class GateLedgerPrerequisiteExpiryTests(unittest.TestCase):
    def setUp(self):
        self.ledger = GateLedger(TEMPLATE)

    def test_has_passing_decision_is_false_once_the_pinned_approvals_expire(self):
        self.ledger.record(passing(0, expires_on=date(2026, 10, 15)))

        self.assertTrue(self.ledger.has_passing_decision(0, on=DECIDED))
        self.assertFalse(self.ledger.has_passing_decision(0, on=LATER))

    def test_dependency_states_mark_an_expired_prerequisite_as_blocked(self):
        self.ledger.record(passing(0, expires_on=date(2026, 10, 15)))

        self.assertIs(
            GateState.APPROVED, self.ledger.dependency_states(on=DECIDED)[0]
        )
        self.assertIs(
            GateState.BLOCKED, self.ledger.dependency_states(on=LATER)[0]
        )

    def test_refuses_a_dependent_passing_decision_when_a_prerequisite_expired(self):
        self.ledger.record(passing(0, expires_on=date(2026, 10, 15)))

        with self.assertRaises(UnsatisfiedPrerequisiteError):
            self.ledger.record(passing(1, decided_on=LATER))

        self.assertFalse(self.ledger.has_passing_decision(1, on=LATER))

    def test_accepts_a_dependent_passing_decision_while_the_prerequisite_holds(self):
        self.ledger.record(passing(0, expires_on=date(2026, 12, 31)))

        self.ledger.record(passing(1, decided_on=LATER))

        self.assertTrue(self.ledger.has_passing_decision(1, on=LATER))


class GateLedgerTransitivePrerequisiteExpiryTests(unittest.TestCase):
    """An expired upstream stage revokes every stage that depends on it.

    SPEC.md section 4 makes the 0-10 pipeline a dependency graph and says "a
    failed or expired prerequisite blocks dependent authorization until
    resolved". The revocation must be transitive: a stage whose own approvals
    are still current does not authorize downstream work while a stage further
    up the chain has lapsed. Before this change the ledger checked only the
    immediate prerequisite's own decision, so a passing decision resting on an
    expired upstream stage still reported success and could be used to record
    further dependent approvals.
    """

    def setUp(self):
        self.ledger = GateLedger(TEMPLATE)

    def _record_chain(self, expiries) -> None:
        for stage_number, expires_on in enumerate(expiries):
            self.ledger.record(
                passing(
                    stage_number,
                    decided_on=DECIDED,
                    expires_on=expires_on,
                )
            )

    def test_intact_chain_still_authorizes_transitively_later(self):
        self._record_chain([date(2026, 12, 31)] * 3)

        self.assertTrue(self.ledger.has_passing_decision(2, on=LATER))

    def test_expired_upstream_revokes_a_directly_dependent_stage(self):
        self._record_chain([date(2026, 10, 15), date(2026, 12, 31)])

        self.assertTrue(self.ledger.has_passing_decision(1, on=DECIDED))
        self.assertFalse(self.ledger.has_passing_decision(1, on=LATER))

    def test_expired_upstream_revokes_a_transitively_dependent_stage(self):
        self._record_chain(
            [date(2026, 10, 15), date(2026, 12, 31), date(2026, 12, 31)]
        )

        self.assertTrue(self.ledger.has_passing_decision(2, on=DECIDED))
        self.assertFalse(self.ledger.has_passing_decision(2, on=LATER))

    def test_dependency_states_block_every_stage_behind_the_expired_chain(self):
        self._record_chain(
            [date(2026, 10, 15), date(2026, 12, 31), date(2026, 12, 31)]
        )

        states = self.ledger.dependency_states(on=LATER)

        self.assertIs(GateState.BLOCKED, states[0])
        self.assertIs(GateState.BLOCKED, states[1])
        self.assertIs(GateState.BLOCKED, states[2])

    def test_pipeline_progress_does_not_count_gates_behind_an_expired_chain(self):
        self._record_chain(
            [date(2026, 10, 15), date(2026, 12, 31), date(2026, 12, 31)]
        )

        progress = PipelineProgress.from_ledger(self.ledger, on=LATER)

        self.assertEqual(0, progress.approved_gates)


class GateDecisionPrerequisiteExpiryTests(unittest.TestCase):
    def test_factory_refuses_a_dependent_approval_on_an_expired_prerequisite(self):
        scope = "stage-2-downstream"
        gate = approvable_gate(1, scope)
        ledger = GateLedger(TEMPLATE)
        ledger.record(passing(0, expires_on=date(2026, 10, 15)))

        with self.assertRaises(GateDecisionError):
            GateDecision.from_gate(
                gate,
                ledger=ledger,
                reviewer="client-approver-1",
                scope=scope,
                checkpoint_evidence="avatar rubric passed",
                disposition=GateDisposition.APPROVED,
                rationale="prerequisite evidence lapsed",
                on=LATER,
                assigned_owner="production-manager",
                due_on=DUE,
            )

    def test_factory_records_a_dependent_approval_while_the_prerequisite_holds(self):
        scope = "stage-2-downstream"
        gate = approvable_gate(1, scope)
        ledger = GateLedger(TEMPLATE)
        ledger.record(passing(0, expires_on=date(2026, 12, 31)))

        decision = GateDecision.from_gate(
            gate,
            ledger=ledger,
            reviewer="client-approver-1",
            scope=scope,
            checkpoint_evidence="avatar rubric passed",
            disposition=GateDisposition.APPROVED,
            rationale="prerequisite evidence current",
            on=LATER,
            assigned_owner="production-manager",
            due_on=DUE,
        )

        self.assertTrue(decision.authorizes_downstream_at(LATER))


class GateDecisionEffectivenessTests(unittest.TestCase):
    def test_authorizes_downstream_at_is_false_once_an_approval_expires(self):
        decision = passing(0, expires_on=date(2026, 10, 15))

        self.assertTrue(decision.authorizes_downstream_at(DECIDED))
        self.assertFalse(decision.authorizes_downstream_at(LATER))

    def test_no_argument_authorizes_downstream_matches_the_decision_instant(self):
        decision = passing(0, expires_on=date(2026, 10, 15))

        self.assertTrue(decision.authorizes_downstream())


if __name__ == "__main__":
    unittest.main()
