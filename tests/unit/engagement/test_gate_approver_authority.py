"""Behavioral tests for the stage gate approver authority rule (pure domain).

Rules under test come from SPEC.md sections 4 and 5: a stage completion requires
gate acceptance by the client-designated authority, and "an agent cannot confer
human approval upon itself". The stage 0-10 template names the approver role
``client-designated-authority``, but a gate's ``approver`` was a free
caller-supplied string with no link to the workspace's named-authority registry,
so a gate could designate an approver who holds no authority on the client. These
tests bind the governance gate's designated approver to the Engagement
ClientWorkspace authority registry (cycle 56) without inventing a concrete human
identity or authority name (SPEC.md section 11).
"""

import unittest
from datetime import date

from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    GateApproverNotAuthorizedError,
)
from redops.contexts.engagement.domain.policies import (
    GateApproverAuthorityPolicy,
)
from redops.contexts.engagement.domain.value_objects import ClientAuthority
from redops.contexts.governance.domain.entities import StageGate
from redops.contexts.governance.domain.value_objects import AssetVersionRef

ON = date(2026, 10, 2)
TENANT = "client-3f"
APPROVER = "client-approver-1"


def workspace(**overrides) -> ClientWorkspace:
    values = {
        "workspace_id": "ws-3f",
        "tenant_id": TENANT,
        "authorities": (
            ClientAuthority(actor=APPROVER, authority="client-designated-authority"),
        ),
    }
    values.update(overrides)
    return ClientWorkspace(**values)


def gate(approver=APPROVER, **overrides) -> StageGate:
    values = {
        "stage_number": 0,
        "template_version": "2026.1",
        "required_assets": frozenset({AssetVersionRef("client-record", 1)}),
        "checkpoint": "Production Ready",
        "proposed_by": "red-specialist",
        "approver": approver,
    }
    values.update(overrides)
    return StageGate(**values)


class GateApproverAuthorityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = GateApproverAuthorityPolicy()

    def test_a_gate_approver_who_is_a_named_authority_is_accepted(self):
        self.policy.require(gate(), workspace())

    def test_a_gate_approver_who_holds_no_authority_is_refused(self):
        with self.assertRaises(GateApproverNotAuthorizedError) as caught:
            self.policy.require(gate(approver="stranger"), workspace())
        self.assertIn("stranger", str(caught.exception))
        self.assertIn("ws-3f", str(caught.exception))

    def test_a_gate_without_a_designated_approver_is_refused(self):
        with self.assertRaises(GateApproverNotAuthorizedError):
            self.policy.require(gate(approver=None), workspace())

    def test_authority_is_checked_against_the_workspace_tenant(self):
        other = workspace(
            workspace_id="ws-other",
            tenant_id="client-other",
            authorities=(ClientAuthority(actor="other-approver", authority="client-designated-authority"),),
        )

        with self.assertRaises(GateApproverNotAuthorizedError):
            self.policy.require(gate(approver="other-approver"), workspace())
        self.policy.require(gate(approver="other-approver"), other)

    def test_the_policy_does_not_mutate_gate_or_workspace(self):
        entry = gate()
        root = workspace()

        self.policy.require(entry, root)

        self.assertEqual(APPROVER, entry.approver)
        self.assertTrue(root.has_authority(APPROVER))


if __name__ == "__main__":
    unittest.main()
