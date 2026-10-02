"""Behavioral tests for the FunnelIntegration aggregate (Execution domain).

Rules under test come from SPEC.md section 4, stage 8 "Integrate":
- The required asset package is the campaign architecture, pages, forms,
  qualification, booking, sequences, CRM, tags, automation, analytics, tracking,
  sales handoff and SOPs.
- The "Funnel Complete" checkpoint requires a test prospect to complete capture,
  engagement and conversion handoffs with reliable records and ownership.
- Phase 4 TDD example: "failed prospect routing prevents Funnel Complete".
- The stage is grounded on the approved stage 7 Authority Amplifier (SPEC.md
  section 3: production requires approved dependencies).
"""

import unittest
from dataclasses import FrozenInstanceError

from redops.contexts.execution.domain.errors import (
    FunnelDependencyError,
    FunnelIncompleteError,
    InvalidFunnelError,
)
from redops.contexts.execution.domain.value_objects import (
    HANDOFF_ORDER,
    FunnelState,
    HandoffKind,
    HandoffOutcome,
)

from .fixtures import (
    complete_funnel,
    dry_run,
    funnel_assets,
    funnel_integration,
    handoff,
)
from ..production.fixtures import script_approved_amplifier


class FunnelCompletionTests(unittest.TestCase):
    def test_a_grounded_funnel_with_a_complete_prospect_path_is_complete(self):
        integration = funnel_integration()

        completed = integration.mark_funnel_complete(dry_run())

        self.assertIs(FunnelState.COMPLETE, completed.state)
        self.assertTrue(completed.is_complete)
        self.assertIsNotNone(completed.dry_run)

    def test_failed_prospect_routing_prevents_funnel_complete(self):
        failed = dry_run(
            handoffs=tuple(
                handoff(
                    kind,
                    outcome=(
                        HandoffOutcome.FAILED
                        if kind is HandoffKind.CONVERSION
                        else HandoffOutcome.ROUTED
                    ),
                )
                for kind in HANDOFF_ORDER
            )
        )

        with self.assertRaises(FunnelIncompleteError):
            funnel_integration().mark_funnel_complete(failed)

    def test_a_missing_handoff_prevents_funnel_complete(self):
        partial = dry_run(
            handoffs=(handoff(HandoffKind.CAPTURE),)
        )

        with self.assertRaises(FunnelIncompleteError):
            funnel_integration().mark_funnel_complete(partial)

    def test_funnel_complete_requires_stage_7_creative_acceptance(self):
        script_only = script_approved_amplifier()

        with self.assertRaises(FunnelDependencyError):
            funnel_integration(amplifier=script_only).mark_funnel_complete(
                dry_run()
            )

    def test_a_terminal_funnel_cannot_complete(self):
        terminal = funnel_integration(state=FunnelState.ARCHIVED)

        with self.assertRaises(FunnelDependencyError):
            terminal.mark_funnel_complete(dry_run())

    def test_a_funnel_cannot_complete_on_another_tenants_dry_run(self):
        foreign = dry_run(tenant_id="client-other")

        with self.assertRaises(FunnelDependencyError):
            funnel_integration().mark_funnel_complete(foreign)


class FunnelInvariantTests(unittest.TestCase):
    def test_a_funnel_requires_identity_owner_and_assets(self):
        for override in (
            {"integration_id": "  "},
            {"owner": ""},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidFunnelError):
                    funnel_integration(**override)

    def test_a_funnel_cannot_be_grounded_on_another_tenants_amplifier(self):
        with self.assertRaises(FunnelDependencyError):
            funnel_integration(tenant_id="client-other")

    def test_the_asset_package_requires_every_stage_8_artifact(self):
        for field in (
            "campaign_architecture",
            "pages",
            "forms",
            "qualification",
            "booking",
            "sequences",
            "crm",
            "tags",
            "automation",
            "analytics",
            "tracking",
            "sales_handoff",
            "sops",
        ):
            with self.subTest(field=field):
                with self.assertRaises(InvalidFunnelError):
                    funnel_assets(**{field: "  "})

    def test_a_routed_handoff_requires_a_reliable_record_and_owner(self):
        for override in ({"record_id": "  "}, {"owner": ""}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidFunnelError):
                    handoff(HandoffKind.CAPTURE, **override)

    def test_duplicate_handoffs_are_rejected(self):
        with self.assertRaises(InvalidFunnelError):
            dry_run(
                handoffs=(
                    handoff(HandoffKind.CAPTURE),
                    handoff(HandoffKind.CAPTURE),
                    handoff(HandoffKind.ENGAGEMENT),
                    handoff(HandoffKind.CONVERSION),
                )
            )

    def test_a_complete_funnel_is_immutable(self):
        completed = complete_funnel()

        with self.assertRaises(FrozenInstanceError):
            completed.owner = "tampered"

    def test_a_complete_funnel_can_be_marked_review_required(self):
        completed = complete_funnel()

        marked = completed.mark_review_required(reason="amplifier changed")

        self.assertIs(FunnelState.REVIEW_REQUIRED, marked.state)
        self.assertTrue(marked.review_reason)

    def test_marking_review_required_needs_a_reason(self):
        with self.assertRaises(InvalidFunnelError):
            complete_funnel().mark_review_required(reason="  ")


if __name__ == "__main__":
    unittest.main()
