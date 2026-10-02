"""Behavioral tests for the stage gate assigned-owner authority rule.

Rules under test come from SPEC.md sections 1, 3, 4 and 11: every output has an
owner, a stage completion records an assigned work owner and a due date, and the
production view must answer "who is accountable" for a stage. The
``ClientWorkspace`` is the client-owned named-authority registry (cycle 56), and
the stage 0 intake-asset owners and the gate approver are already bound to it.
But the durable ``GateDecision.assigned_owner`` was still a free caller-supplied
string, so a passing stage 0 decision could name an owner who holds no authority
on the client and is therefore unaccountable. These tests bind that owner to the
same registry without inventing a concrete human identity (SPEC.md section 11).
"""

import unittest
from datetime import date

from redops.contexts.engagement.domain.assemblies import (
    StageZeroGateAssembler,
    StageZeroGateRecorder,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    StageOwnerNotAuthorizedError,
)
from redops.contexts.engagement.domain.policies import GateOwnerAuthorityPolicy
from redops.contexts.engagement.domain.value_objects import (
    CANONICAL_INTAKE_KINDS,
    ClientAuthority,
    IntakeAsset,
    IntakeAssetKind,
    IntakePackage,
)
from redops.contexts.governance.domain.entities import GateLedger
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.value_objects import (
    ProvenanceClass,
    SourceCitation,
)

ON = date(2026, 10, 2)
DUE = date(2026, 10, 16)
TENANT = "client-3f"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE = "stage-1-diagnosis"


def workspace(**overrides) -> ClientWorkspace:
    values = {
        "workspace_id": "ws-3f",
        "tenant_id": TENANT,
        "authorities": (
            ClientAuthority(actor=OWNER, authority="production-owner"),
            ClientAuthority(actor=APPROVER, authority="client-designated-authority"),
        ),
    }
    values.update(overrides)
    return ClientWorkspace(**values)


class GateOwnerAuthorityPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = GateOwnerAuthorityPolicy()

    def test_an_assigned_owner_who_is_a_named_authority_is_accepted(self):
        self.policy.require(OWNER, workspace())

    def test_an_assigned_owner_who_holds_no_authority_is_refused(self):
        with self.assertRaises(StageOwnerNotAuthorizedError) as caught:
            self.policy.require("stranger", workspace())
        self.assertIn("stranger", str(caught.exception))
        self.assertIn("ws-3f", str(caught.exception))

    def test_a_blank_assigned_owner_is_refused(self):
        with self.assertRaises(StageOwnerNotAuthorizedError):
            self.policy.require("   ", workspace())

    def test_owner_authority_is_checked_against_the_workspace_tenant(self):
        other = workspace(
            workspace_id="ws-other",
            tenant_id="client-other",
            authorities=(
                ClientAuthority(actor="other-owner", authority="production-owner"),
            ),
        )

        with self.assertRaises(StageOwnerNotAuthorizedError):
            self.policy.require("other-owner", workspace())
        self.policy.require("other-owner", other)

    def test_the_policy_does_not_mutate_the_workspace(self):
        root = workspace()

        self.policy.require(OWNER, root)

        self.assertEqual(2, len(root.authorities))


def asset(kind: IntakeAssetKind, version: int = 1, **overrides) -> IntakeAsset:
    values = {
        "asset_id": f"{kind.value}-3f@{version}",
        "tenant_id": TENANT,
        "kind": kind,
        "version": version,
        "owner": OWNER,
        "summary": f"Recorded {kind.value}",
        "evidence_claim_ids": ("claim-intake-1",),
    }
    values.update(overrides)
    return IntakeAsset(**values)


def package(version: int = 1) -> IntakePackage:
    return IntakePackage(
        package_id="intake-3f",
        tenant_id=TENANT,
        assets=tuple(asset(kind, version) for kind in CANONICAL_INTAKE_KINDS),
    )


def sourced_claim(claim_id: str = "claim-intake-1") -> Claim:
    return Claim(
        claim_id=claim_id,
        tenant_id=TENANT,
        statement="Intake fact recorded with the client",
        provenance=ProvenanceClass.KNOWN,
        citations=frozenset(
            {SourceCitation("source-intake", "sha256:abc", "p.1")}
        ),
        confidence_note="captured during intake",
    )


class StageZeroGateRecorderOwnerTests(unittest.TestCase):
    """The recording path must refuse an unaccountable assigned work owner.

    The recorder is the only place that writes ``GateDecision.assigned_owner``, so
    the authority binding belongs there; a caller cannot pass a non-authority
    owner and leave the production view showing an owner who does not exist on the
    client (SPEC.md sections 4 and 6).
    """

    def setUp(self):
        self.recorder = StageZeroGateRecorder()
        self.template = stage_zero_to_ten_template()

    def test_the_recorder_refuses_a_decision_owner_without_workspace_authority(self):
        gate = StageZeroGateAssembler().assemble(
            template=self.template,
            workspace=workspace(),
            package=package(),
            approver=APPROVER,
            claims=(sourced_claim(),),
            proposed_by=OWNER,
        )
        ledger = GateLedger(self.template)

        with self.assertRaises(StageOwnerNotAuthorizedError):
            self.recorder.record(
                gate=gate,
                workspace=workspace(),
                ledger=ledger,
                scope=SCOPE,
                checkpoint_evidence="all twelve stage 0 assets reviewed",
                rationale="intake complete and owned",
                assigned_owner="stranger",
                due_on=DUE,
                on=ON,
            )

        self.assertIsNone(ledger.decision_for(0))


if __name__ == "__main__":
    unittest.main()
