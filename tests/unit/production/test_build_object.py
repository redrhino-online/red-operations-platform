"""Behavioral tests for the BuildObject aggregate (pure domain, Production).

Rules under test come from SPEC.md sections 3 and 4:
- BuildObject records type, purpose, audience, state, owner, next action,
  blockers and refs (SPEC.md section 3 aggregate table).
- An active build always has an owner and a next action.
- Record transition actor, reason, timestamp, old and new state, correlation ID.
- Reject illegal transitions rather than silently coercing state.
"""

import unittest
from datetime import date

from redops.contexts.production.domain.entities import BuildObject
from redops.contexts.production.domain.errors import (
    IllegalBuildTransitionError,
    InvalidBuildError,
)
from redops.contexts.production.domain.value_objects import BuildState

TODAY = date(2026, 10, 2)
CORRELATION = "corr-build-1"
SCRIPT_V1 = "authority-amplifier-script@1"


def build_object(**overrides) -> BuildObject:
    values = {
        "build_id": "build-1",
        "tenant_id": "3fmindset",
        "build_type": "authority-amplifier-video",
        "purpose": "stage 7 creative",
        "audience": "3f prospects",
        "owner": "production-manager",
        "next_action": "record the video",
        "refs": frozenset({SCRIPT_V1}),
    }
    values.update(overrides)
    return BuildObject(**values)


class BuildInvariantTests(unittest.TestCase):
    def test_new_build_is_identified_with_owner_and_next_action(self):
        build = build_object()

        self.assertIs(BuildState.IDENTIFIED, build.state)
        self.assertTrue(build.is_active)
        self.assertEqual("production-manager", build.owner)
        self.assertEqual("record the video", build.next_action)

    def test_active_build_without_an_owner_is_rejected(self):
        with self.assertRaises(InvalidBuildError):
            build_object(owner="")

    def test_build_without_a_tenant_is_rejected(self):
        with self.assertRaises(InvalidBuildError):
            build_object(tenant_id="   ")

    def test_active_build_without_a_next_action_is_rejected(self):
        with self.assertRaises(InvalidBuildError):
            build_object(next_action="   ")

    def test_an_archived_build_may_have_no_next_action(self):
        build = build_object(state=BuildState.ARCHIVED, next_action="")

        self.assertFalse(build.is_active)

    def test_blocked_build_is_still_active_and_exposes_its_blockers(self):
        build = build_object()

        build.add_blocker("waiting on client footage")

        self.assertTrue(build.is_blocked)
        self.assertIn("waiting on client footage", build.blockers)
        self.assertTrue(build.is_active)

    def test_blank_blocker_is_rejected(self):
        with self.assertRaises(InvalidBuildError):
            build_object().add_blocker(" ")

    def test_reassigning_owner_rejects_a_blank_owner(self):
        with self.assertRaises(InvalidBuildError):
            build_object().reassign_owner("")


class BuildTransitionTests(unittest.TestCase):
    def test_build_progresses_from_identified_to_optimizing(self):
        build = build_object()

        build.require_source(actor="specialist-1", reason="need footage", on=TODAY, correlation_id=CORRELATION)
        build.mark_ready(actor="specialist-1", reason="footage arrived", on=TODAY, correlation_id=CORRELATION)
        build.start_development(actor="specialist-1", reason="editing", on=TODAY, correlation_id=CORRELATION)
        build.submit_for_internal_review(actor="specialist-1", reason="first cut", on=TODAY, correlation_id=CORRELATION)
        build.submit_for_client_review(actor="production-manager", reason="internal ok", on=TODAY, correlation_id=CORRELATION)
        build.approve(actor="client-approver-1", reason="accepted", on=TODAY, correlation_id=CORRELATION)
        build.mark_production_ready(actor="production-manager", reason="ready", on=TODAY, correlation_id=CORRELATION)
        build.deploy(actor="operator-1", reason="published", on=TODAY, correlation_id=CORRELATION)
        build.start_measuring(actor="analyst-1", reason="live", on=TODAY, correlation_id=CORRELATION)

        self.assertIs(BuildState.MEASURING, build.state)

        build.start_optimizing(actor="analyst-1", reason="improve", on=TODAY, correlation_id=CORRELATION)

        self.assertIs(BuildState.OPTIMIZING, build.state)
        self.assertTrue(build.is_active)

    def test_illegal_transition_is_rejected(self):
        build = build_object()

        with self.assertRaises(IllegalBuildTransitionError):
            build.approve(actor="client-approver-1", reason="jump the gate", on=TODAY, correlation_id=CORRELATION)

        self.assertIs(BuildState.IDENTIFIED, build.state)

    def test_superseded_build_cannot_transition_again(self):
        build = build_object()
        build.require_source(actor="specialist-1", reason="start", on=TODAY, correlation_id=CORRELATION)
        build.mark_ready(actor="specialist-1", reason="ready", on=TODAY, correlation_id=CORRELATION)
        build.supersede(actor="governance-manager", reason="method changed", on=TODAY, correlation_id=CORRELATION)

        with self.assertRaises(IllegalBuildTransitionError):
            build.mark_ready(actor="specialist-1", reason="restart", on=TODAY, correlation_id=CORRELATION)

    def test_archived_build_is_terminal(self):
        build = build_object()
        build.archive(actor="production-manager", reason="cancelled", on=TODAY, correlation_id=CORRELATION)

        self.assertFalse(build.is_active)
        with self.assertRaises(IllegalBuildTransitionError):
            build.start_development(actor="specialist-1", reason="restart", on=TODAY, correlation_id=CORRELATION)

    def test_transition_records_actor_reason_time_state_and_correlation(self):
        build = build_object()
        build.mark_ready(actor="specialist-1", reason="cleared", on=TODAY, correlation_id=CORRELATION)
        build.start_development(actor="specialist-1", reason="editing", on=TODAY, correlation_id=CORRELATION)

        self.assertEqual(2, len(build.transitions))
        transition = build.transitions[-1]
        self.assertEqual("specialist-1", transition.actor)
        self.assertEqual("editing", transition.reason)
        self.assertEqual(TODAY, transition.occurred_at)
        self.assertEqual(CORRELATION, transition.correlation_id)
        self.assertIs(BuildState.READY, transition.old_state)
        self.assertIs(BuildState.IN_DEVELOPMENT, transition.new_state)

    def test_transition_history_is_immutable(self):
        build = build_object()
        build.mark_ready(actor="specialist-1", reason="cleared", on=TODAY, correlation_id=CORRELATION)
        build.start_development(actor="specialist-1", reason="editing", on=TODAY, correlation_id=CORRELATION)

        self.assertIsInstance(build.transitions, tuple)


if __name__ == "__main__":
    unittest.main()
