"""Behavioral tests for the umbrella-plan projection of the production view.

SPEC.md section 4 requires the production-manager view to answer, for each
client, what should exist, what is present and approved, what is missing, who is
accountable, which dependency blocks work, what approval is next and when it is
due, and to separate its eight reporting dimensions. SPEC.md section 12.5 and
canon files 00 and 01 describe the umbrella plan: the engagement's single-page
plan over the whole stage 0-10 pipeline, revisited every 90 days. It is a
planning decision, not a new required gate kind, so it is wired into the
production view as a caller-supplied, tenant-scoped read-model projection.

The projection is a pure read model: it never invents a plan, owner or review
date, and it refuses a row from another client or one that does not cover exactly
the view's stages.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date, timedelta

from redops.contexts.governance.domain.entities import GateLedger
from redops.contexts.governance.domain.errors import (
    UmbrellaPlanCoverageError,
    UmbrellaPlanReportingError,
    UmbrellaPlanReportingTenantBoundaryError,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    UmbrellaPlanReportingView,
)
from tests.unit.governance.test_production_view import (
    VERSION,
    ledger_through,
    view,
)

ALL_STAGES = frozenset(range(11))
REVIEWED_ON = date(2026, 9, 1)
NEXT_REVIEW_DUE = date(2026, 11, 30)


def umbrella_plan(**overrides) -> UmbrellaPlanReportingView:
    values = {
        "plan_id": "umbrella-3f",
        "tenant_id": "tenant-3f",
        "owner": "production-manager",
        "covered_stages": ALL_STAGES,
        "reviewed_on": REVIEWED_ON,
        "next_review_due": NEXT_REVIEW_DUE,
    }
    values.update(overrides)
    return UmbrellaPlanReportingView(**values)


class UmbrellaPlanProjectionTests(unittest.TestCase):
    def test_a_same_tenant_plan_covering_the_view_stages_is_exposed(self):
        plan = umbrella_plan()
        result = view(ledger_through(11), umbrella_plan=plan)

        self.assertIs(plan, result.umbrella_plan)

    def test_the_default_umbrella_plan_is_none(self):
        result = view(GateLedger(stage_zero_to_ten_template(VERSION)))

        self.assertIsNone(result.umbrella_plan)

    def test_the_90_day_revisit_is_current_before_and_overdue_at_the_due_date(self):
        plan = umbrella_plan()

        self.assertTrue(plan.is_current(NEXT_REVIEW_DUE - timedelta(days=1)))
        self.assertFalse(plan.is_overdue(NEXT_REVIEW_DUE - timedelta(days=1)))
        self.assertFalse(plan.is_current(NEXT_REVIEW_DUE))
        self.assertTrue(plan.is_overdue(NEXT_REVIEW_DUE))
        self.assertTrue(plan.is_overdue(NEXT_REVIEW_DUE + timedelta(days=1)))

    def test_a_cross_tenant_plan_is_refused(self):
        with self.assertRaises(UmbrellaPlanReportingTenantBoundaryError):
            view(
                ledger_through(11),
                umbrella_plan=umbrella_plan(tenant_id="other-client"),
            )

    def test_a_plan_missing_a_view_stage_is_refused(self):
        with self.assertRaises(UmbrellaPlanCoverageError):
            view(
                ledger_through(11),
                umbrella_plan=umbrella_plan(covered_stages=frozenset(range(10))),
            )

    def test_a_plan_with_an_extra_stage_is_refused(self):
        with self.assertRaises(UmbrellaPlanCoverageError):
            view(
                ledger_through(11),
                umbrella_plan=umbrella_plan(covered_stages=frozenset(range(12))),
            )

    def test_a_malformed_row_is_refused(self):
        for override in (
            {"plan_id": " "},
            {"tenant_id": " "},
            {"owner": ""},
            {"covered_stages": frozenset()},
            {"covered_stages": frozenset({-1})},
            {"covered_stages": frozenset({"0"})},
            {"covered_stages": frozenset({True})},
            {"next_review_due": REVIEWED_ON},
            {"next_review_due": REVIEWED_ON - timedelta(days=1)},
        ):
            with self.subTest(override=override):
                with self.assertRaises(UmbrellaPlanReportingError):
                    umbrella_plan(**override)

    def test_the_view_is_still_immutable(self):
        result = view(ledger_through(11), umbrella_plan=umbrella_plan())

        with self.assertRaises(FrozenInstanceError):
            result.umbrella_plan = None


if __name__ == "__main__":
    unittest.main()
