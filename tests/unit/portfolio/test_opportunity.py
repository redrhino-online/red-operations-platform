"""Behavioral tests for the portfolio opportunity proposal (Portfolio domain).

SPEC.md section 7 lists ``/opportunities`` and SPEC.md section 1 puts portfolio
expansion in the product contract; the canon's Grow motion splits the foundation
offer into smaller offers that are new entry points and raise customer lifetime
value (canon files 11 and 12; SPEC.md section 12.3). These tests pin the
opportunity's fields, its exact same-tenant source asset version, and the rule
that it stays a proposal until a human investment authority acts (SPEC.md
sections 1 and 5).
"""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.governance.domain.value_objects import StageAssetVersion
from redops.contexts.portfolio.domain.errors import (
    InvalidOpportunityError,
    OpportunityAuthorityError,
    OpportunityTenantBoundaryError,
)
from redops.contexts.portfolio.domain.value_objects import (
    Opportunity,
    OpportunityKind,
    OpportunityState,
)

TENANT = "tenant-3f"
OTHER_TENANT = "tenant-other"
CAPTURED_ON = date(2026, 10, 3)


def source(**overrides) -> StageAssetVersion:
    values = {
        "asset_id": "offer-3f",
        "tenant_id": TENANT,
        "kind": "offer-version",
        "version": 3,
    }
    values.update(overrides)
    return StageAssetVersion(**values)


def opportunity(**overrides) -> Opportunity:
    values = {
        "opportunity_id": "opp-1",
        "tenant_id": TENANT,
        "title": "a smaller entry point offer",
        "kind": OpportunityKind.ENTRY_POINT,
        "source": source(),
        "investment_case": "the warmed audience already converts on the core offer",
        "expected_outcome": "a lower priced entry point that raises qualified leads",
        "owner": "portfolio-lead",
        "next_action": "size the offer and price it against the primary currency",
        "captured_on": CAPTURED_ON,
    }
    values.update(overrides)
    return Opportunity(**values)


class OpportunityTests(unittest.TestCase):
    def test_an_opportunity_pins_its_exact_source_asset_version(self):
        record = opportunity()

        self.assertEqual(("offer-version", 3), record.source_key)

    def test_an_opportunity_is_a_proposal(self):
        record = opportunity()

        self.assertIs(OpportunityState.PROPOSED, record.state)
        self.assertTrue(record.is_proposal)

    def test_every_required_field_is_enforced(self):
        for field in (
            "opportunity_id",
            "tenant_id",
            "title",
            "investment_case",
            "expected_outcome",
            "owner",
            "next_action",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidOpportunityError):
                    opportunity(**{field: "   "})

    def test_the_kind_must_be_typed(self):
        with self.assertRaises(InvalidOpportunityError):
            opportunity(kind="entry_point")

    def test_the_source_must_be_an_exact_stage_asset_version(self):
        with self.assertRaises(InvalidOpportunityError):
            opportunity(source="offer-3f@3")

    def test_a_cross_tenant_source_is_refused(self):
        with self.assertRaises(OpportunityTenantBoundaryError):
            opportunity(source=source(tenant_id=OTHER_TENANT))

    def test_the_capture_date_must_be_a_date(self):
        with self.assertRaises(InvalidOpportunityError):
            opportunity(captured_on="2026-10-03")

    def test_an_approved_state_cannot_be_recorded(self):
        with self.assertRaises(OpportunityAuthorityError):
            opportunity(state=OpportunityState.APPROVED)

    def test_an_untyped_state_is_refused(self):
        with self.assertRaises(InvalidOpportunityError):
            opportunity(state="approved")

    def test_an_opportunity_is_immutable(self):
        record = opportunity()

        with self.assertRaises(FrozenInstanceError):
            record.title = "changed"  # type: ignore[misc]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
