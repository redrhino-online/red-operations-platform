"""Behavioral tests for the canon Swimlanes channel model (Execution domain).

Rules under test come from SPEC.md section 12.5 (the Swimlanes channel model --
messages, ads, human outreach, offline and direct mail, content -- is a canon gap
"cross-cutting over stages 8 to 10" used to "recover stalled prospects across all
channels, not only digital ads") and section 12.3 (canon files 13, 14, 33 and 34
inform stages 8 and 10), shaped by the canon:

- Canon files 13 and 14, the swimlanes "five swim lanes sales funnel system",
  names five modalities or vehicles that "drive prospects through your funnel"
  when they do not move forward, so a move "gently move[s] them to the next step".
- Canon file 34 warns you "can't just rely on email" and "you can't be single
  source dependent", so the plan must use all five canon channels to some degree.

The plan is a cross-cutting planning asset over the stage 8 `FunnelIntegration`.
The methodology owner ruled it a canon-informed required asset kind of the stage 8
"Funnel Complete" gate (owner decision 2026-10-04; SPEC.md sections 4 and 12.5), so
`SwimlanesPlan.as_stage_asset` projects it onto exact `swimlanes-plan` evidence. It
does not authorize sending, publishing, spend or traffic (SPEC.md sections 4 and 9)
and it is never an observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.execution.domain.errors import (
    InvalidSwimlanesError,
    SwimlaneCoverageError,
    SwimlanesDependencyError,
    SwimlanesObservationError,
    SwimlanesTenantBoundaryError,
)
from redops.contexts.execution.domain.policies import SwimlaneCoveragePolicy
from redops.contexts.execution.domain.swimlanes import (
    SWIMLANE_CHANNELS,
    SWIMLANES_PLAN_KIND,
    SwimlaneChannel,
    SwimlaneMove,
    SwimlanesPlan,
)

from .fixtures import TENANT, funnel_integration

STEPS = (
    ("traffic", "opt_in"),
    ("opt_in", "watch_amplifier"),
    ("watch_amplifier", "book_call"),
    ("book_call", "show"),
    ("show", "enroll"),
)


def move(
    channel: SwimlaneChannel = SwimlaneChannel.MESSAGES,
    *,
    stalled_step: str = "traffic",
    next_step: str = "opt_in",
    **overrides,
) -> SwimlaneMove:
    values = {
        "move_id": f"move-{getattr(channel, 'value', channel)}",
        "tenant_id": TENANT,
        "channel": channel,
        "stalled_step": stalled_step,
        "next_step": next_step,
        "vehicle": "email",
        "next_action": "send the reason to take the next step",
    }
    values.update(overrides)
    return SwimlaneMove(**values)


def all_channel_moves() -> tuple[SwimlaneMove, ...]:
    return tuple(
        move(channel, stalled_step=stalled, next_step=next_step)
        for channel, (stalled, next_step) in zip(SWIMLANE_CHANNELS, STEPS)
    )


def swimlanes_plan(**overrides) -> SwimlanesPlan:
    values = {
        "plan_id": "swimlanes-3f",
        "tenant_id": TENANT,
        "owner": "journey-owner",
        "funnel": funnel_integration(),
        "moves": all_channel_moves(),
    }
    values.update(overrides)
    return SwimlanesPlan(**values)


class SwimlaneChannelTests(unittest.TestCase):
    def test_the_canon_swimlanes_have_five_channels_in_order(self):
        self.assertEqual(
            (
                SwimlaneChannel.MESSAGES,
                SwimlaneChannel.ADS,
                SwimlaneChannel.HUMAN_OUTREACH,
                SwimlaneChannel.OFFLINE_DIRECT_MAIL,
                SwimlaneChannel.CONTENT,
            ),
            SWIMLANE_CHANNELS,
        )


class SwimlaneMoveTests(unittest.TestCase):
    def test_a_move_requires_its_identity_channel_steps_vehicle_and_action(self):
        self.assertEqual(SwimlaneChannel.MESSAGES, move().channel)
        for override in (
            {"move_id": ""},
            {"tenant_id": "  "},
            {"stalled_step": ""},
            {"next_step": ""},
            {"vehicle": ""},
            {"next_action": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidSwimlanesError):
                    move(**override)

    def test_a_move_refuses_an_untyped_channel(self):
        with self.assertRaises(InvalidSwimlanesError):
            move(channel="messages")

    def test_a_move_must_move_a_prospect_to_a_different_step(self):
        with self.assertRaises(InvalidSwimlanesError):
            move(stalled_step="opt_in", next_step="opt_in")

    def test_a_move_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            move().next_step = "book_call"


class SwimlanesPlanTests(unittest.TestCase):
    def test_a_plan_requires_its_identity_and_owner(self):
        for override in (
            {"plan_id": ""},
            {"tenant_id": "  "},
            {"owner": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidSwimlanesError):
                    swimlanes_plan(**override)

    def test_a_plan_requires_a_typed_same_tenant_funnel(self):
        with self.assertRaises(SwimlanesDependencyError):
            swimlanes_plan(funnel="funnel-3f")
        with self.assertRaises(SwimlanesTenantBoundaryError):
            swimlanes_plan(tenant_id="client-other")

    def test_a_plan_requires_at_least_one_move(self):
        with self.assertRaises(InvalidSwimlanesError):
            swimlanes_plan(moves=())
        with self.assertRaises(InvalidSwimlanesError):
            swimlanes_plan(moves=("send an email",))

    def test_a_plan_refuses_a_cross_tenant_move_and_a_duplicate_move(self):
        with self.assertRaises(SwimlanesTenantBoundaryError):
            swimlanes_plan(moves=(move(tenant_id="client-other"),))
        with self.assertRaises(InvalidSwimlanesError):
            swimlanes_plan(moves=(move(), move()))

    def test_a_plan_reports_the_channels_it_covers_and_misses(self):
        moves = all_channel_moves()
        plan = swimlanes_plan(moves=moves)

        self.assertEqual(SWIMLANE_CHANNELS, plan.covered_channels)
        self.assertEqual((), plan.missing_channels())
        self.assertTrue(plan.is_complete)
        self.assertEqual(
            (moves[1],), plan.moves_for(SwimlaneChannel.ADS)
        )

    def test_a_plan_missing_a_channel_reports_it_and_is_incomplete(self):
        plan = swimlanes_plan(moves=all_channel_moves()[:-1])

        self.assertEqual(SWIMLANE_CHANNELS[:-1], plan.covered_channels)
        self.assertEqual(
            (SwimlaneChannel.CONTENT,), plan.missing_channels()
        )
        self.assertFalse(plan.is_complete)

    def test_a_plan_is_a_plan_not_an_observation(self):
        self.assertTrue(swimlanes_plan().is_plan)
        with self.assertRaises(SwimlanesObservationError):
            swimlanes_plan().as_observation(claim_id="claim-1")

    def test_as_stage_asset_projects_the_plan_identity_at_an_exact_version(self):
        asset = swimlanes_plan().as_stage_asset(version=2)

        self.assertEqual(SWIMLANES_PLAN_KIND, asset.kind)
        self.assertEqual("swimlanes-plan", asset.kind)
        self.assertEqual("swimlanes-3f", asset.asset_id)
        self.assertEqual(TENANT, asset.tenant_id)
        self.assertEqual(2, asset.version)

    def test_as_stage_asset_refuses_a_versionless_projection(self):
        for version in (0, -1):
            with self.subTest(version=version):
                with self.assertRaises(InvalidSwimlanesError):
                    swimlanes_plan().as_stage_asset(version=version)

    def test_a_plan_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            swimlanes_plan().owner = "someone-else"


class SwimlaneCoveragePolicyTests(unittest.TestCase):
    def test_a_plan_using_all_five_channels_is_single_source_independent(self):
        SwimlaneCoveragePolicy().require_all_channels(swimlanes_plan())

    def test_a_plan_relying_on_too_few_channels_is_refused(self):
        plan = swimlanes_plan(moves=all_channel_moves()[:2])

        with self.assertRaises(SwimlaneCoverageError):
            SwimlaneCoveragePolicy().require_all_channels(plan)


if __name__ == "__main__":
    unittest.main()
