"""Behavioral tests for the ``StageRunRepository`` port and its reference adapter.

SPEC.md section 3 makes ``StageRun`` a core aggregate carrying the engagement,
stage number, template version, assigned owner and status; section 4 requires a
stage to complete only through an accepted gate rather than activity, recording
actor, reason, timestamp, old and new status, and correlation ID. SPEC.md
section 6 says infrastructure adapters implement ports. These tests pin the
port contract with the in-memory reference adapter: a run is stored per client,
engagement, template version and stage; a completed run survives a reload with
its assigned owner, entered/exited timestamps, pinned accepted decision and
full transition log; a run stored for one client is never read back for
another; and an unscoped read or write is refused.
"""

from __future__ import annotations

import unittest
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
from redops.contexts.governance.application.ports import StageRunRepository
from redops.contexts.governance.domain.entities import StageRun
from redops.contexts.governance.domain.errors import CrossTenantStageRunError
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    StageStatus,
    StageTemplate,
)
from redops.contexts.governance.infrastructure.repositories import (
    InMemoryGateLedgerRepository,
    InMemoryStageRunRepository,
)
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.value_objects import (
    ProvenanceClass,
    SourceCitation,
)

ON = "2026-10-02"
DUE_DATE = date(2026, 10, 16)
TENANT = "client-3f"
OTHER_TENANT = "client-other"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE = "stage-1-diagnosis"
CORRELATION = "corr-stage-0"
ENGAGEMENT = "ws-3f"

# The stage 0 use case needs a client workspace, a sourced claim and the twelve
# canonical intake assets; a working run is the input whose progress this port
# is meant to persist.
ON_DATE = date(2026, 10, 2)


def workspace() -> ClientWorkspace:
    return ClientWorkspace(
        workspace_id=ENGAGEMENT,
        tenant_id=TENANT,
        authorities=(
            ClientAuthority(actor=OWNER, authority="production-owner"),
            ClientAuthority(actor=APPROVER, authority="client-designated-authority"),
        ),
    )


def sourced_claim() -> Claim:
    return Claim(
        claim_id="claim-intake-1",
        tenant_id=TENANT,
        statement="Intake fact recorded with the client",
        provenance=ProvenanceClass.KNOWN,
        citations=frozenset({SourceCitation("source-intake", "sha256:abc", "p.1")}),
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
    return IntakePackage(package_id="intake-3f", tenant_id=TENANT, assets=assets)


def working_stage_run(template: StageTemplate) -> StageRun:
    run = StageRun(
        engagement=ENGAGEMENT,
        stage_number=0,
        template_version=template.version,
        assigned_owner=OWNER,
        tenant_id=TENANT,
    )
    run.start(
        actor=OWNER,
        reason="intake work began",
        on=ON_DATE,
        correlation_id=CORRELATION,
    )
    return run


class StageRunRepositoryContractTests(unittest.TestCase):
    """The port contract, exercised through the in-memory reference adapter."""

    def setUp(self) -> None:
        self.template = stage_zero_to_ten_template()
        self.runs: StageRunRepository = InMemoryStageRunRepository()
        self.ledger = InMemoryGateLedgerRepository()
        self.handler = RecordStageZeroGateHandler()

    def complete_stage_zero(self, run: StageRun):
        command = RecordStageZeroGateCommand(
            template=self.template,
            workspace=workspace(),
            package=intake_package(),
            claims=(sourced_claim(),),
            stage_run=run,
            approver=APPROVER,
            proposed_by=OWNER,
            scope=SCOPE,
            checkpoint_evidence="all twelve stage 0 assets reviewed",
            rationale="intake complete and owned",
            assigned_owner=OWNER,
            due_on=DUE_DATE,
            on=date(2026, 10, 2),
            correlation_id=CORRELATION,
        )
        decision = self.handler.handle(
            command, ledger=self.ledger.load(self.template, TENANT)
        )
        self.ledger.append(decision)
        return decision

    def test_a_fresh_repository_loads_no_run(self) -> None:
        self.assertIsNone(
            self.runs.load(self.template.version, ENGAGEMENT, 0, TENANT)
        )

    def test_a_working_run_survives_a_reload(self) -> None:
        run = working_stage_run(self.template)

        self.runs.save(run)
        reloaded = self.runs.load(self.template.version, ENGAGEMENT, 0, TENANT)

        self.assertIsNotNone(reloaded)
        self.assertEqual(StageStatus.WORKING, reloaded.status)
        self.assertEqual(OWNER, reloaded.assigned_owner)
        self.assertEqual(TENANT, reloaded.tenant_id)
        self.assertEqual(ON_DATE, reloaded.entered_at)
        self.assertEqual(1, len(reloaded.transitions))
        self.assertEqual(StageStatus.WORKING, reloaded.transitions[0].new_status)
        self.assertEqual(CORRELATION, reloaded.transitions[0].correlation_id)

    def test_a_completed_run_survives_a_reload_with_its_decision(self) -> None:
        run = working_stage_run(self.template)
        decision = self.complete_stage_zero(run)
        self.runs.save(run)

        reloaded = self.runs.load(self.template.version, ENGAGEMENT, 0, TENANT)

        self.assertEqual(StageStatus.COMPLETE, reloaded.status)
        self.assertTrue(reloaded.is_complete)
        self.assertEqual(ON_DATE, reloaded.exited_at)
        self.assertIsNotNone(reloaded.accepted_decision)
        self.assertEqual(decision.required_assets, reloaded.accepted_decision.required_assets)
        self.assertEqual(TENANT, reloaded.accepted_decision.tenant_id)
        self.assertEqual(StageStatus.COMPLETE, reloaded.transitions[-1].new_status)

    def test_a_resave_moves_one_run_forward_rather_than_adding_one(self) -> None:
        run = working_stage_run(self.template)
        self.runs.save(run)
        self.complete_stage_zero(run)
        self.runs.save(run)

        reloaded = self.runs.load(self.template.version, ENGAGEMENT, 0, TENANT)
        self.assertEqual(StageStatus.COMPLETE, reloaded.status)
        self.assertEqual(2, len(reloaded.transitions))

    def test_a_run_is_not_read_back_for_another_client(self) -> None:
        self.runs.save(working_stage_run(self.template))

        self.assertIsNone(
            self.runs.load(self.template.version, ENGAGEMENT, 0, OTHER_TENANT)
        )

    def test_save_refuses_a_run_that_carries_no_tenant(self) -> None:
        run = working_stage_run(self.template)
        run.tenant_id = ""

        with self.assertRaises(CrossTenantStageRunError):
            self.runs.save(run)

    def test_load_requires_a_tenant(self) -> None:
        with self.assertRaises(CrossTenantStageRunError):
            self.runs.load(self.template.version, ENGAGEMENT, 0, "")

    def test_round_trip_preserves_a_run_without_a_decision(self) -> None:
        from redops.contexts.governance.infrastructure.mappers import (
            stage_run_from_payload,
            stage_run_to_payload,
        )

        run = working_stage_run(self.template)
        reloaded = stage_run_from_payload(stage_run_to_payload(run))

        self.assertEqual(run.status, reloaded.status)
        self.assertEqual(run.tenant_id, reloaded.tenant_id)
        self.assertEqual(run.entered_at, reloaded.entered_at)
        self.assertEqual(run.transitions, reloaded.transitions)
        self.assertIsNone(reloaded.accepted_decision)


if __name__ == "__main__":
    unittest.main()
