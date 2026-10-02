"""Behavioral tests for the Engagement tenant root (pure domain).

Rules under test come from SPEC.md section 3: the ClientWorkspace aggregate
carries an id, a tenant, authorities and a lifecycle, and its invariant is that
"every child resource belongs to exactly one client". SPEC.md section 4 names the
engagement lifecycle states and requires illegal transitions to be rejected
rather than silently coerced, recording the actor, reason, timestamp, old and new
state and correlation ID. These tests exercise the tenant boundary the whole
stage 0-10 pipeline attaches to; they never claim a named human approver because
that identity is an open decision (SPEC.md section 11).
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    ChildAlreadyAttachedError,
    IllegalLifecycleTransitionError,
    InvalidAuthorityError,
    InvalidClientWorkspaceError,
    TenantBoundaryError,
)
from redops.contexts.engagement.domain.value_objects import (
    ClientAuthority,
    EngagementLifecycle,
    LifecycleTransition,
)

ON = date(2026, 10, 2)

PROGRESSION_AFTER_INTAKE = (
    EngagementLifecycle.DIAGNOSIS,
    EngagementLifecycle.POSITIONING,
    EngagementLifecycle.DIAGNOSTIC_MODELING,
    EngagementLifecycle.IP_PACKAGING,
    EngagementLifecycle.PRODUCTIZATION,
    EngagementLifecycle.CAMPAIGN_MESSAGING,
    EngagementLifecycle.AUTHORITY_AMPLIFIER_PRODUCTION,
    EngagementLifecycle.FUNNEL_INTEGRATION,
    EngagementLifecycle.LAUNCH_QA,
    EngagementLifecycle.FIRST_CAMPAIGN_LAUNCH,
    EngagementLifecycle.OPTIMIZATION,
    EngagementLifecycle.EXPANSION,
)


def authority(
    actor: str = "red-owner", authority_name: str = "production-owner"
) -> ClientAuthority:
    return ClientAuthority(actor=actor, authority=authority_name)


def workspace(**overrides) -> ClientWorkspace:
    values = {
        "workspace_id": "ws-3f",
        "tenant_id": "client-3f",
        "authorities": (authority(),),
    }
    values.update(overrides)
    return ClientWorkspace(**values)


class ClientAuthorityTests(unittest.TestCase):
    def test_an_authority_names_an_actor_and_its_authority(self):
        entry = authority(actor="alice", authority_name="client-approver")

        self.assertEqual("alice", entry.actor)
        self.assertEqual("client-approver", entry.authority)

    def test_an_authority_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            authority().actor = "mallory"

    def test_an_authority_without_an_actor_or_authority_is_rejected(self):
        for override in ({"actor": ""}, {"actor": "  "}, {"authority_name": ""}):
            with self.subTest(override=override):
                with self.assertRaises(InvalidAuthorityError):
                    authority(**override)


class ClientWorkspaceTenantBoundaryTests(unittest.TestCase):
    def test_a_workspace_records_its_identity_tenant_authorities_and_lifecycle(self):
        root = workspace()

        self.assertEqual("ws-3f", root.workspace_id)
        self.assertEqual("client-3f", root.tenant_id)
        self.assertEqual((authority(),), root.authorities)
        self.assertEqual(EngagementLifecycle.INTAKE, root.lifecycle)

    def test_a_workspace_without_identity_or_authority_is_rejected(self):
        for override in (
            {"workspace_id": ""},
            {"workspace_id": "   "},
            {"tenant_id": ""},
            {"authorities": ()},
        ):
            with self.subTest(override=override):
                with self.assertRaises(InvalidClientWorkspaceError):
                    workspace(**override)

    def test_a_workspace_rejects_a_duplicate_authority(self):
        with self.assertRaises(InvalidClientWorkspaceError):
            workspace(authorities=(authority(), authority()))

    def test_a_workspace_owns_only_its_own_tenant(self):
        root = workspace()

        self.assertTrue(root.owns("client-3f"))
        self.assertFalse(root.owns("client-other"))
        self.assertFalse(root.owns(""))

    def test_a_same_tenant_child_attaches_once_and_is_retrievable(self):
        root = workspace()

        root.attach("avatar-3f@1", "client-3f")

        self.assertTrue(root.is_attached("avatar-3f@1"))
        self.assertEqual("client-3f", root.child_tenant("avatar-3f@1"))
        self.assertEqual(("avatar-3f@1",), root.children)

    def test_a_foreign_tenant_child_is_refused_and_never_attaches(self):
        root = workspace()

        with self.assertRaises(TenantBoundaryError):
            root.attach("avatar-other@1", "client-other")

        self.assertFalse(root.is_attached("avatar-other@1"))
        self.assertEqual((), root.children)

    def test_attaching_the_same_child_twice_is_refused(self):
        root = workspace()
        root.attach("avatar-3f@1", "client-3f")

        with self.assertRaises(ChildAlreadyAttachedError):
            root.attach("avatar-3f@1", "client-3f")

    def test_attaching_a_blank_child_is_rejected(self):
        with self.assertRaises(InvalidClientWorkspaceError):
            workspace().attach("", "client-3f")

    def test_an_unattached_child_has_no_tenant(self):
        self.assertIsNone(workspace().child_tenant("missing"))

    def test_a_workspace_can_designate_and_check_authorities(self):
        root = workspace()
        root.designate(authority(actor="alice", authority_name="client-approver"))

        self.assertTrue(root.has_authority("alice", "client-approver"))
        self.assertTrue(root.has_authority("alice"))
        self.assertFalse(root.has_authority("alice", "production-owner"))
        self.assertFalse(root.has_authority("bob"))

    def test_designating_a_duplicate_authority_is_refused(self):
        root = workspace()

        with self.assertRaises(InvalidClientWorkspaceError):
            root.designate(authority())


class EngagementLifecycleTests(unittest.TestCase):
    def test_a_workspace_advances_one_step_and_records_the_transition(self):
        root = workspace()

        transition = root.advance_to(
            EngagementLifecycle.DIAGNOSIS,
            actor="red-owner",
            reason="stage 0 accepted",
            on=ON,
            correlation_id="corr-1",
        )

        self.assertEqual(EngagementLifecycle.DIAGNOSIS, root.lifecycle)
        self.assertEqual(EngagementLifecycle.INTAKE, transition.old_lifecycle)
        self.assertEqual(EngagementLifecycle.DIAGNOSIS, transition.new_lifecycle)
        self.assertEqual("red-owner", transition.actor)
        self.assertEqual("stage 0 accepted", transition.reason)
        self.assertEqual(ON, transition.occurred_at)
        self.assertEqual("corr-1", transition.correlation_id)
        self.assertEqual((transition,), root.transitions)

    def test_a_workspace_cannot_skip_or_reverse_a_lifecycle_state(self):
        root = workspace()
        root.advance_to(
            EngagementLifecycle.DIAGNOSIS,
            actor="red-owner",
            reason="stage 0 accepted",
            on=ON,
            correlation_id="corr-1",
        )

        with self.assertRaises(IllegalLifecycleTransitionError):
            root.advance_to(
                EngagementLifecycle.IP_PACKAGING,
                actor="red-owner",
                reason="skip",
                on=ON,
                correlation_id="corr-2",
            )
        with self.assertRaises(IllegalLifecycleTransitionError):
            root.advance_to(
                EngagementLifecycle.INTAKE,
                actor="red-owner",
                reason="reverse",
                on=ON,
                correlation_id="corr-3",
            )
        self.assertEqual(EngagementLifecycle.DIAGNOSIS, root.lifecycle)

    def test_a_paused_workspace_resumes_to_the_state_it_paused_from(self):
        root = workspace()
        root.advance_to(
            EngagementLifecycle.DIAGNOSIS,
            actor="red-owner",
            reason="stage 0 accepted",
            on=ON,
            correlation_id="corr-1",
        )

        root.pause(
            actor="red-owner",
            reason="client away",
            on=ON,
            correlation_id="corr-2",
        )
        self.assertEqual(EngagementLifecycle.PAUSED, root.lifecycle)

        root.resume(
            actor="red-owner",
            reason="client back",
            on=ON,
            correlation_id="corr-3",
        )
        self.assertEqual(EngagementLifecycle.DIAGNOSIS, root.lifecycle)

    def test_pausing_a_paused_workspace_is_refused(self):
        root = workspace()
        root.pause(
            actor="red-owner",
            reason="client away",
            on=ON,
            correlation_id="corr-1",
        )

        with self.assertRaises(IllegalLifecycleTransitionError):
            root.pause(
                actor="red-owner",
                reason="again",
                on=ON,
                correlation_id="corr-2",
            )

    def test_a_completed_workspace_is_terminal(self):
        root = workspace()
        for step, target in enumerate(PROGRESSION_AFTER_INTAKE, start=1):
            root.advance_to(
                target,
                actor="red-owner",
                reason=f"step {step}",
                on=ON,
                correlation_id=f"corr-{step}",
            )
        root.advance_to(
            EngagementLifecycle.COMPLETED,
            actor="red-owner",
            reason="engagement complete",
            on=ON,
            correlation_id="corr-complete",
        )

        self.assertTrue(root.lifecycle.is_terminal)
        with self.assertRaises(IllegalLifecycleTransitionError):
            root.advance_to(
                EngagementLifecycle.EXPANSION,
                actor="red-owner",
                reason="reopen",
                on=ON,
                correlation_id="corr-reopen",
            )

    def test_a_lifecycle_transition_requires_an_actor_reason_and_correlation(self):
        for override in (
            {"actor": ""},
            {"reason": "  "},
            {"correlation_id": ""},
        ):
            with self.subTest(override=override):
                values = {
                    "actor": "red-owner",
                    "reason": "stage accepted",
                    "occurred_at": ON,
                    "old_lifecycle": EngagementLifecycle.INTAKE,
                    "new_lifecycle": EngagementLifecycle.DIAGNOSIS,
                    "correlation_id": "corr-1",
                }
                values.update(override)
                with self.assertRaises(ValueError):
                    LifecycleTransition(**values)


if __name__ == "__main__":
    unittest.main()
