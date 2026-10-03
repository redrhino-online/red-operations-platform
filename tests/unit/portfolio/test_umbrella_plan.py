"""Behavioral tests for the canon umbrella plan (Portfolio domain).

Rules under test come from SPEC.md section 12.5 (umbrella planning -- the Online
Business Launch Map and the one-page Bulletproof Business Plan with a 90-day
revisit, canon files 00 and 01 -- is a canon gap over stages 0 to 10) and section
12.3 (canon files 00 and 01 inform portfolio and engagement planning), shaped by
the canon:

- Canon file 00 puts the whole strategy into one page with four parts: the
  foundation, the signature solution, the funnel and the floodgates.
- Canon file 01 requires the one-page business plan's goals and metrics to be
  specific and the plan to be redone every 90 days, not put on the shelf.

The plan maps the canon's four parts onto the versioned stage 0 to 10 template
(SPEC.md section 4). It is a planning decision, not a new required gate kind (a
methodology-owner decision, SPEC.md section 12.5), it does not authorize
production, spend or traffic (SPEC.md sections 4 and 9) and it is never an
observation (SPEC.md section 3).
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date, timedelta

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.value_objects import ClientAuthority
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.portfolio.domain.errors import (
    InvalidUmbrellaPlanError,
    UmbrellaPlanDependencyError,
    UmbrellaPlanFormatError,
    UmbrellaPlanObservationError,
    UmbrellaPlanOverdueError,
    UmbrellaPlanTenantBoundaryError,
    UmbrellaReviewCadenceError,
    UmbrellaReviewOrderError,
)
from redops.contexts.portfolio.domain.policies import UmbrellaReviewPolicy
from redops.contexts.portfolio.domain.value_objects import (
    LAUNCH_MAP_SECTIONS,
    LAUNCH_MAP_SECTION_STAGES,
    QUARTERLY_REVIEW_DAYS,
    BusinessTarget,
    LaunchMapSection,
    QuarterlyReview,
    UmbrellaPlan,
    UmbrellaSection,
)

TENANT = "client-3f"
CREATED = date(2026, 10, 2)


def workspace(**overrides) -> ClientWorkspace:
    values = {
        "workspace_id": "ws-3f",
        "tenant_id": TENANT,
        "authorities": (
            ClientAuthority(actor="red-owner", authority="production-owner"),
        ),
    }
    values.update(overrides)
    return ClientWorkspace(**values)


def section(
    kind: LaunchMapSection = LaunchMapSection.FOUNDATION,
    stages: tuple[int, ...] = None,
    objective: str = "establish the avatar, currency and message",
) -> UmbrellaSection:
    default_stages = (
        LAUNCH_MAP_SECTION_STAGES[kind]
        if kind in LAUNCH_MAP_SECTION_STAGES
        else (0,)
    )
    return UmbrellaSection(
        section=kind,
        stages=default_stages if stages is None else stages,
        objective=objective,
    )


def sections() -> tuple[UmbrellaSection, ...]:
    return tuple(section(kind) for kind in LAUNCH_MAP_SECTIONS)


def target(**overrides) -> BusinessTarget:
    values = {
        "target_id": "target-leads",
        "name": "qualified strategy calls",
        "metric": "booked strategy calls per week",
        "goal": "20 per week",
        "due_on": date(2026, 12, 31),
    }
    values.update(overrides)
    return BusinessTarget(**values)


def review(**overrides) -> QuarterlyReview:
    values = {
        "reviewed_on": CREATED,
        "next_review_on": CREATED + timedelta(days=QUARTERLY_REVIEW_DAYS),
        "actor": "red-principal",
    }
    values.update(overrides)
    return QuarterlyReview(**values)


def umbrella_plan(**overrides) -> UmbrellaPlan:
    values = {
        "plan_id": "umbrella-3f",
        "tenant_id": TENANT,
        "owner": "red-principal",
        "workspace": workspace(),
        "template": stage_zero_to_ten_template(),
        "sections": sections(),
        "targets": (target(),),
        "reviews": (review(),),
        "created_on": CREATED,
    }
    values.update(overrides)
    return UmbrellaPlan(**values)


class LaunchMapSectionTests(unittest.TestCase):
    def test_the_canon_launch_map_has_four_parts_in_order(self):
        self.assertEqual(
            (
                LaunchMapSection.FOUNDATION,
                LaunchMapSection.SIGNATURE_SOLUTION,
                LaunchMapSection.FUNNEL,
                LaunchMapSection.FLOODGATES,
            ),
            LAUNCH_MAP_SECTIONS,
        )

    def test_the_canon_section_stages_cover_the_pipeline_exactly(self):
        covered = [
            stage
            for kind in LAUNCH_MAP_SECTIONS
            for stage in LAUNCH_MAP_SECTION_STAGES[kind]
        ]

        self.assertEqual(list(range(11)), covered)


class UmbrellaSectionTests(unittest.TestCase):
    def test_a_section_requires_a_typed_kind_an_objective_and_stages(self):
        self.assertEqual(LaunchMapSection.FOUNDATION, section().section)
        with self.assertRaises(InvalidUmbrellaPlanError):
            section(kind="foundation")
        with self.assertRaises(InvalidUmbrellaPlanError):
            section(objective="  ")
        with self.assertRaises(InvalidUmbrellaPlanError):
            section(stages=())

    def test_a_section_refuses_a_non_negative_stage(self):
        with self.assertRaises(InvalidUmbrellaPlanError):
            section(stages=(-1,))

    def test_a_section_refuses_duplicate_stages(self):
        with self.assertRaises(UmbrellaPlanFormatError):
            section(stages=(0, 0))

    def test_a_section_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            section().objective = "another objective"


class BusinessTargetTests(unittest.TestCase):
    def test_a_target_requires_its_specific_fields_and_a_due_date(self):
        self.assertEqual("20 per week", target().goal)
        for override in (
            {"target_id": ""},
            {"name": "  "},
            {"metric": ""},
            {"goal": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidUmbrellaPlanError):
                    target(**override)

    def test_a_target_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            target().goal = "200 per week"


class QuarterlyReviewTests(unittest.TestCase):
    def test_a_review_requires_an_actor_and_dates(self):
        self.assertEqual("red-principal", review().actor)
        with self.assertRaises(InvalidUmbrellaPlanError):
            review(actor="")
        with self.assertRaises(InvalidUmbrellaPlanError):
            review(reviewed_on=None)

    def test_a_review_schedules_its_next_revisit_exactly_one_quarter_later(self):
        self.assertEqual(
            CREATED + timedelta(days=QUARTERLY_REVIEW_DAYS), review().next_review_on
        )

    def test_a_review_refuses_a_shorter_or_longer_revisit(self):
        for days in (89, 91):
            with self.subTest(days=days):
                with self.assertRaises(UmbrellaReviewCadenceError):
                    review(next_review_on=CREATED + timedelta(days=days))

    def test_a_review_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            review().actor = "someone-else"


class UmbrellaPlanTests(unittest.TestCase):
    def test_a_plan_requires_its_identity_owner_and_creation_date(self):
        for override in (
            {"plan_id": ""},
            {"tenant_id": "  "},
            {"owner": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidUmbrellaPlanError):
                    umbrella_plan(**override)

    def test_a_plan_requires_a_typed_workspace_and_template(self):
        with self.assertRaises(UmbrellaPlanDependencyError):
            umbrella_plan(workspace="ws-3f")
        with self.assertRaises(UmbrellaPlanDependencyError):
            umbrella_plan(template="0 to 10")

    def test_a_plan_refuses_a_cross_tenant_workspace(self):
        with self.assertRaises(UmbrellaPlanTenantBoundaryError):
            umbrella_plan(workspace=workspace(tenant_id="client-other"))

    def test_a_plan_requires_every_canon_section_exactly_once(self):
        for override in (
            {"sections": sections()[:-1]},
            {"sections": sections() + (section(LaunchMapSection.FOUNDATION),)},
        ):
            with self.subTest(override=override):
                with self.assertRaises(UmbrellaPlanFormatError):
                    umbrella_plan(**override)

    def test_a_plan_refuses_a_section_stage_the_template_does_not_name(self):
        with self.assertRaises(UmbrellaPlanDependencyError):
            umbrella_plan(
                sections=(
                    section(LaunchMapSection.FOUNDATION),
                    section(LaunchMapSection.SIGNATURE_SOLUTION),
                    section(LaunchMapSection.FUNNEL),
                    section(
                        LaunchMapSection.FLOODGATES,
                        stages=(10, 11),
                    ),
                )
            )

    def test_a_plan_refuses_a_stage_gap_or_overlap(self):
        with self.assertRaises(UmbrellaPlanFormatError):
            umbrella_plan(
                sections=(
                    section(LaunchMapSection.FOUNDATION),
                    section(LaunchMapSection.SIGNATURE_SOLUTION),
                    section(LaunchMapSection.FUNNEL, stages=(6, 7, 8)),
                    section(LaunchMapSection.FLOODGATES, stages=(10,)),
                )
            )
        with self.assertRaises(UmbrellaPlanFormatError):
            umbrella_plan(
                sections=(
                    section(LaunchMapSection.FOUNDATION),
                    section(LaunchMapSection.SIGNATURE_SOLUTION),
                    section(LaunchMapSection.FUNNEL, stages=(6, 7, 8, 9)),
                    section(LaunchMapSection.FLOODGATES, stages=(9, 10)),
                )
            )

    def test_a_plan_requires_at_least_one_specific_target(self):
        with self.assertRaises(InvalidUmbrellaPlanError):
            umbrella_plan(targets=())
        with self.assertRaises(UmbrellaPlanFormatError):
            umbrella_plan(targets=(target(), target()))
        with self.assertRaises(InvalidUmbrellaPlanError):
            umbrella_plan(targets=("20 calls",))

    def test_a_plan_refuses_a_target_due_before_it_was_created(self):
        with self.assertRaises(UmbrellaPlanFormatError):
            umbrella_plan(
                targets=(target(due_on=CREATED - timedelta(days=1)),)
            )

    def test_a_plan_requires_an_ordered_review_history(self):
        with self.assertRaises(InvalidUmbrellaPlanError):
            umbrella_plan(reviews=())
        with self.assertRaises(UmbrellaReviewOrderError):
            umbrella_plan(
                reviews=(
                    review(
                        reviewed_on=CREATED - timedelta(days=1),
                        next_review_on=CREATED - timedelta(days=1)
                        + timedelta(days=QUARTERLY_REVIEW_DAYS),
                    ),
                )
            )
        with self.assertRaises(UmbrellaReviewOrderError):
            umbrella_plan(
                reviews=(
                    review(),
                    review(
                        reviewed_on=CREATED + timedelta(days=30),
                        next_review_on=CREATED + timedelta(days=120),
                    ),
                )
            )

    def test_a_plan_reports_the_stages_it_covers_and_the_next_revisit(self):
        plan = umbrella_plan()

        self.assertEqual(tuple(range(11)), plan.covered_stages)
        self.assertEqual((), plan.missing_stages())
        self.assertEqual(
            CREATED + timedelta(days=QUARTERLY_REVIEW_DAYS), plan.next_review_due
        )

    def test_a_plan_is_a_plan_not_an_observation(self):
        self.assertTrue(umbrella_plan().is_plan)
        with self.assertRaises(UmbrellaPlanObservationError):
            umbrella_plan().as_observation(claim_id="claim-1")

    def test_a_plan_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            umbrella_plan().owner = "someone-else"


class UmbrellaReviewPolicyTests(unittest.TestCase):
    def test_a_plan_within_its_cadence_is_current(self):
        UmbrellaReviewPolicy().require_current(umbrella_plan(), on=CREATED)

    def test_a_plan_is_current_on_its_exact_revisit_due_date(self):
        UmbrellaReviewPolicy().require_current(
            umbrella_plan(), on=CREATED + timedelta(days=QUARTERLY_REVIEW_DAYS)
        )

    def test_a_plan_past_its_revisit_due_date_is_refused(self):
        with self.assertRaises(UmbrellaPlanOverdueError):
            UmbrellaReviewPolicy().require_current(
                umbrella_plan(),
                on=CREATED + timedelta(days=QUARTERLY_REVIEW_DAYS + 1),
            )


if __name__ == "__main__":
    unittest.main()
