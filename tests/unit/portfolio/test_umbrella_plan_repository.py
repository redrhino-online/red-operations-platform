"""Adapter contract tests for the portfolio umbrella plan store (SPEC.md section 6).

SPEC.md section 12.5 records the canon umbrella plan (the Online Business Launch
Map and the one-page Bulletproof Business Plan, canon files 00 and 01) as a
planning decision over the whole stage 0-10 pipeline, revisited every 90 days, and
SPEC.md section 4 requires the production view to carry it as a tenant-scoped
projection. These tests exercise the port contract on the process-local reference
adapter: a plan is append-only, scoped to one tenant, idempotent on an exact
replay and a named conflict on a different same-id re-statement. They also prove
the aggregate projects into the governance ``UmbrellaPlanReportingView`` with the
plan identity, owner, covered stages and latest review dates.
"""

from __future__ import annotations

import unittest
from datetime import date, timedelta

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.value_objects import ClientAuthority
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import UmbrellaPlanReportingView
from redops.contexts.portfolio.domain.errors import (
    UmbrellaPlanConflictError,
    UmbrellaPlanTenantBoundaryError,
)
from redops.contexts.portfolio.domain.value_objects import (
    LAUNCH_MAP_SECTIONS,
    LAUNCH_MAP_SECTION_STAGES,
    QUARTERLY_REVIEW_DAYS,
    BusinessTarget,
    QuarterlyReview,
    UmbrellaPlan,
    UmbrellaSection,
)
from redops.contexts.portfolio.infrastructure.repositories import (
    InMemoryUmbrellaPlanRepository,
    umbrella_plan_repository_from_env,
)

TENANT = "tenant-3f"
OTHER_TENANT = "tenant-other"
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


def umbrella_plan(**overrides) -> UmbrellaPlan:
    values = {
        "plan_id": "umbrella-3f",
        "tenant_id": TENANT,
        "owner": "red-principal",
        "workspace": workspace(),
        "template": stage_zero_to_ten_template(),
        "sections": tuple(
            UmbrellaSection(
                section=kind,
                stages=LAUNCH_MAP_SECTION_STAGES[kind],
                objective=f"{kind.value} objective",
            )
            for kind in LAUNCH_MAP_SECTIONS
        ),
        "targets": (
            BusinessTarget(
                target_id="target-leads",
                name="qualified strategy calls",
                metric="booked strategy calls per week",
                goal="20 per week",
                due_on=date(2026, 12, 31),
            ),
        ),
        "reviews": (
            QuarterlyReview(
                reviewed_on=CREATED,
                next_review_on=CREATED + timedelta(days=QUARTERLY_REVIEW_DAYS),
                actor="red-principal",
            ),
        ),
        "created_on": CREATED,
    }
    values.update(overrides)
    return UmbrellaPlan(**values)


class InMemoryUmbrellaPlanRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryUmbrellaPlanRepository()

    def test_a_saved_plan_is_listed_and_resolved(self) -> None:
        self.repository.save(umbrella_plan())

        self.assertEqual((umbrella_plan(),), self.repository.list(TENANT))
        self.assertEqual(
            umbrella_plan(), self.repository.get(TENANT, "umbrella-3f")
        )

    def test_an_unknown_plan_is_none(self) -> None:
        self.assertIsNone(self.repository.get(TENANT, "umbrella-missing"))

    def test_reads_are_scoped_by_tenant(self) -> None:
        self.repository.save(umbrella_plan())

        self.assertEqual((), self.repository.list(OTHER_TENANT))
        self.assertIsNone(self.repository.get(OTHER_TENANT, "umbrella-3f"))

    def test_an_exact_replay_is_idempotent(self) -> None:
        self.repository.save(umbrella_plan())
        self.repository.save(umbrella_plan())

        self.assertEqual(1, len(self.repository.list(TENANT)))

    def test_a_same_id_different_body_is_refused(self) -> None:
        self.repository.save(umbrella_plan())

        with self.assertRaises(UmbrellaPlanConflictError):
            self.repository.save(umbrella_plan(owner="someone-else"))

    def test_an_unscoped_read_or_write_is_refused(self) -> None:
        with self.assertRaises(UmbrellaPlanTenantBoundaryError):
            self.repository.list("   ")

    def test_the_factory_uses_the_process_local_store_without_a_url(self) -> None:
        self.assertIsInstance(
            umbrella_plan_repository_from_env(None),
            InMemoryUmbrellaPlanRepository,
        )


class UmbrellaPlanReportingProjectionTests(unittest.TestCase):
    def test_the_plan_projects_its_identity_owner_coverage_and_review(self) -> None:
        row = umbrella_plan().as_reporting_view()

        self.assertIsInstance(row, UmbrellaPlanReportingView)
        self.assertEqual("umbrella-3f", row.plan_id)
        self.assertEqual(TENANT, row.tenant_id)
        self.assertEqual("red-principal", row.owner)
        self.assertEqual(frozenset(range(11)), row.covered_stages)
        self.assertEqual(CREATED, row.reviewed_on)
        self.assertEqual(
            CREATED + timedelta(days=QUARTERLY_REVIEW_DAYS), row.next_review_due
        )

    def test_the_projection_reports_current_and_overdue_against_the_review(self) -> None:
        row = umbrella_plan().as_reporting_view()

        self.assertTrue(row.is_current(CREATED))
        self.assertFalse(row.is_overdue(CREATED))
        self.assertTrue(
            row.is_overdue(CREATED + timedelta(days=QUARTERLY_REVIEW_DAYS + 1))
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
