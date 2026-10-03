"""Behavioral tests for the ``GateLedgerRepository`` port and its adapter.

SPEC.md section 6 says infrastructure adapters implement ports and the API and
workers call use cases rather than mutating persistence directly. ADR 0003 makes
RED's gate ledger durable in PostgreSQL behind a repository port. SPEC.md
section 4 makes a stage complete only when its required assets exist, pass the
checkpoint, and receive approval for downstream use, and a passing gate pins the
exact evidence and intended downstream use; history is append-only (section 3).

These tests pin the port contract using the in-memory reference adapter: the
ledger is reconstructed per template version, a passing decision survives a
reload with its exact pinned versions, history is retained in order, decisions
for another template version are never replayed, and a stored decision that the
domain would reject cannot be read back as approved. They use the shared
application seam the API and workers will call: record through the stage 0 use
case, persist through the port, then reload and assert the durable result.
"""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import date

from redops.contexts.engagement.application.commands import (
    RecordStageZeroGateCommand,
)
from redops.contexts.engagement.application.handlers import (
    RecordStageZeroGateHandler,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.value_objects import (
    CANONICAL_INTAKE_KINDS,
    ClientAuthority,
    IntakeAsset,
    IntakePackage,
)
from redops.contexts.governance.application.ports import GateLedgerRepository
from redops.contexts.governance.domain.entities import StageRun
from redops.contexts.governance.domain.errors import AssetPackageMismatchError
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    GateDisposition,
    StageTemplate,
)
from redops.contexts.governance.infrastructure.repositories import (
    InMemoryGateLedgerRepository,
)
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
CORRELATION = "corr-stage-0"


def workspace() -> ClientWorkspace:
    return ClientWorkspace(
        workspace_id="ws-3f",
        tenant_id=TENANT,
        authorities=(
            ClientAuthority(actor=OWNER, authority="production-owner"),
            ClientAuthority(actor=APPROVER, authority="client-designated-authority"),
        ),
    )


def working_stage_run(template: StageTemplate) -> StageRun:
    run = StageRun(
        engagement="ws-3f",
        stage_number=0,
        template_version=template.version,
        assigned_owner=OWNER,
    )
    run.start(
        actor=OWNER,
        reason="intake work began",
        on=ON,
        correlation_id=CORRELATION,
    )
    return run


def sourced_claim() -> Claim:
    return Claim(
        claim_id="claim-intake-1",
        tenant_id=TENANT,
        statement="Intake fact recorded with the client",
        provenance=ProvenanceClass.KNOWN,
        citations=(
            frozenset({SourceCitation("source-intake", "sha256:abc", "p.1")}),
        ),
        confidence_note="captured during intake",
    )


def intake_package() -> IntakePackage:
    assets = tuple(
        IntakeAsset(
            asset_id=f"{kind.value}-3f@1",
            tenant_id=TENANT,
            kind=kind,
            version=1,
            owner=OWNER,
            summary=f"Recorded {kind.value}",
            evidence_claim_ids=("claim-intake-1",),
        )
        for kind in CANONICAL_INTAKE_KINDS
    )
    return IntakePackage(
        package_id="intake-3f", tenant_id=TENANT, assets=assets
    )


class GateLedgerRepositoryContractTests(unittest.TestCase):
    """The port contract, exercised through the in-memory reference adapter."""

    def setUp(self) -> None:
        self.template = stage_zero_to_ten_template()
        self.repository: GateLedgerRepository = InMemoryGateLedgerRepository()
        self.handler = RecordStageZeroGateHandler()

    def record_stage_zero(self):
        command = RecordStageZeroGateCommand(
            template=self.template,
            workspace=workspace(),
            package=intake_package(),
            claims=(sourced_claim(),),
            stage_run=working_stage_run(self.template),
            approver=APPROVER,
            proposed_by=OWNER,
            scope=SCOPE,
            checkpoint_evidence="all twelve stage 0 assets reviewed",
            rationale="intake complete and owned",
            assigned_owner=OWNER,
            due_on=DUE,
            on=ON,
            correlation_id=CORRELATION,
        )
        decision = self.handler.handle(command, ledger=self.repository.load(self.template))
        self.repository.append(decision)
        return decision

    def test_a_fresh_repository_loads_an_empty_ledger(self) -> None:
        ledger = self.repository.load(self.template)

        self.assertIsNone(ledger.decision_for(0))
        self.assertEqual((), ledger.decisions_for(0))

    def test_a_recorded_passing_gate_survives_a_reload_with_exact_versions(self) -> None:
        decision = self.record_stage_zero()

        reloaded = self.repository.load(self.template)

        self.assertIs(decision, reloaded.decision_for(0))
        self.assertEqual(decision.required_assets, reloaded.decision_for(0).required_assets)
        self.assertTrue(reloaded.has_passing_decision(0, on=ON))

    def test_history_is_append_only_and_ordered(self) -> None:
        first = self.record_stage_zero()
        second = replace(
            first,
            disposition=GateDisposition.CHANGES_REQUIRED,
            rationale="reopened for a scope correction",
            asset_approvals=(),
        )
        self.repository.append(second)

        reloaded = self.repository.load(self.template)

        self.assertEqual((first, second), reloaded.decisions_for(0))
        self.assertIs(second, reloaded.decision_for(0))
        self.assertFalse(reloaded.has_passing_decision(0, on=ON))

    def test_decisions_for_another_template_version_are_not_replayed(self) -> None:
        self.record_stage_zero()
        other = StageTemplate(version="tampered", stages=self.template.stages)

        ledger = self.repository.load(other)

        self.assertIsNone(ledger.decision_for(0))

    def test_reload_refuses_a_stored_decision_the_domain_would_reject(self) -> None:
        decision = self.record_stage_zero()
        self.repository.append(replace(decision, stage_number=1))

        with self.assertRaises(AssetPackageMismatchError):
            self.repository.load(self.template)


if __name__ == "__main__":
    unittest.main()
