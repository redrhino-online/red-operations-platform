"""Behavioral tests for the stage 1 "Avatar Locked" gate path.

Rules under test come from SPEC.md sections 3, 4, 5 and 11 and the reference
model canon (SPEC.md section 12.3 maps stage 1 "Diagnose" to canon files 02, 03
and 04). A stage is complete only when its required assets exist, pass a defined
checkpoint, and receive approval for downstream use; a passing gate "pins the
exact evidence and intended downstream use"; a failed or expired prerequisite
blocks dependent authorization until resolved; a stage gate is approved by the
client-designated authority and an agent cannot confer human approval upon
itself; every output has an owner and a source.

Cycle 69 added the Commercial ``DiagnosisPackage`` bridge that projects the three
reviewed stage 1 values onto the nine canonical stage 1 asset kinds as exact
``StageAssetVersion`` evidence, so a canonical stage 1 gate can now be assembled.
This cycle wires the stage 1 "Avatar Locked" gate end to end, mirroring the stage
0 path: a pure Engagement assembler validates the reviewed values with
``AvatarLockedPolicy`` and ``DiagnosisEvidencePolicy``, pins the canonical stage 1
gate via ``StageGate.from_assets`` and binds the client-designated approver; a
recorder issues one exact-version approval per kind and writes the durable
``GateDecision``; an application use case chains them and closes the stage 1
``StageRun``. Stage 1 depends on stage 0, so the ledger must already hold a
passing stage 0 decision. These tests never invent a named client approver or a
concrete authority role.
"""

import unittest
from datetime import date

from redops.contexts.commercial.domain.errors import (
    AvatarLockedError,
    MarketAwarenessTargetingError,
    UnsourcedDiagnosisEvidenceError,
)
from redops.contexts.commercial.domain.value_objects import (
    AudienceDefinition,
    AudienceReachEstimate,
    AvatarProfile,
    BusinessSnapshot,
    DiagnosisPackage,
    InterestKind,
    InterestSignal,
    MarketAwarenessLevel,
    MarketAwarenessMap,
    OfferFunnelAudit,
    ResearchPlatform,
)
from redops.contexts.engagement.application.commands import (
    RecordStageOneGateCommand,
)
from redops.contexts.engagement.application.handlers import (
    RecordStageOneGateHandler,
)
from redops.contexts.engagement.domain.assemblies import (
    StageOneGateAssembler,
    StageOneGateRecorder,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    GateApproverNotAuthorizedError,
    GateAuthorRequiredError,
    NotStageOneGateError,
    StageOwnerNotAuthorizedError,
    StageRunNotCompletableError,
    StageRunNotStageOneError,
    TenantBoundaryError,
)
from redops.contexts.engagement.domain.value_objects import ClientAuthority
from redops.contexts.governance.domain.entities import (
    ApprovalRequest,
    GateDecision,
    GateLedger,
    StageGate,
    StageRun,
)
from redops.contexts.governance.domain.errors import (
    GateDecisionError,
    SelfApprovalError,
)
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    GateDisposition,
    GateState,
    PipelineProgress,
)
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.value_objects import (
    ProvenanceClass,
    SourceCitation,
)

ON = date(2026, 10, 3)
DUE = date(2026, 10, 17)
TENANT = "client-3f"
OTHER_TENANT = "client-other"
OWNER = "red-owner"
APPROVER = "client-approver-1"
SCOPE_ZERO = "stage-1-diagnosis"
SCOPE_ONE = "stage-2-position"
CORRELATION = "corr-stage-1"
AVATAR_CLAIM = "claim-voice-1"
SNAPSHOT_CLAIM = "claim-offer-1"
AUDIT_CLAIM = "claim-offer-2"


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


def sourced_claim(
    claim_id: str,
    *,
    tenant_id: str = TENANT,
    provenance: ProvenanceClass = ProvenanceClass.KNOWN,
) -> Claim:
    return Claim(
        claim_id=claim_id,
        tenant_id=tenant_id,
        statement="Stage 1 diagnosis fact recorded with the client",
        provenance=provenance,
        citations=(
            frozenset({SourceCitation("source-diagnosis", "sha256:def", "p.2")})
            if provenance is ProvenanceClass.KNOWN
            else frozenset()
        ),
        confidence_note="captured during diagnosis",
    )


def claims() -> tuple[Claim, ...]:
    return (
        sourced_claim(AVATAR_CLAIM),
        sourced_claim(SNAPSHOT_CLAIM),
        sourced_claim(AUDIT_CLAIM),
    )


def avatar(*, tenant_id: str = TENANT, evidence=("claim-voice-1",)) -> AvatarProfile:
    return AvatarProfile(
        avatar_id="avatar-3f",
        tenant_id=tenant_id,
        name="Owner-operator of a small service firm",
        demographics="35-50, runs a two to five person local service firm",
        psychographics="proud of craft, skeptical of marketing, time poor",
        pains=("feast and famine pipeline",),
        goals=("predictable qualified demand",),
        consequences_of_inaction=("hires then lays off as work dries up",),
        awareness="problem aware, not solution aware",
        customer_evidence_claim_ids=evidence,
        voice_notes=("I cannot plan payroll when the phone is quiet",),
    )


def snapshot(*, tenant_id: str = TENANT, evidence=("claim-offer-1",)) -> BusinessSnapshot:
    return BusinessSnapshot(
        snapshot_id="snapshot-3f",
        tenant_id=tenant_id,
        business_model="project based service work billed hourly",
        current_offers=("hourly support retainer",),
        lead_sources=("referrals",),
        constraints=("two delivery people, no marketing owner",),
        narrative="Steady referrals but no predictable pipeline between projects",
        evidence_claim_ids=evidence,
    )


def audit(*, tenant_id: str = TENANT, evidence=("claim-offer-2",)) -> OfferFunnelAudit:
    return OfferFunnelAudit(
        audit_id="audit-3f",
        tenant_id=tenant_id,
        offer_findings=("the retainer has no stated outcome",),
        funnel_steps=("referral", "call", "quote", "project"),
        conversion_evidence=("quotes are tracked in a spreadsheet",),
        gaps=("no qualification step before the call",),
        narrative="The funnel has no owner between referral and quote",
        evidence_claim_ids=evidence,
    )


def awareness_map(*, tenant_id: str = TENANT) -> MarketAwarenessMap:
    return MarketAwarenessMap(
        map_id="awareness-3f",
        tenant_id=tenant_id,
        primary_level=MarketAwarenessLevel.PROBLEM_AWARE,
        research_evidence=("reviews name the unpredictable pipeline",),
        message_requirements=("lead with the predictable pipeline outcome",),
        retarget_level=MarketAwarenessLevel.SOLUTION_AWARE,
    )


def reach(*, tenant_id: str = TENANT) -> AudienceReachEstimate:
    return AudienceReachEstimate(
        estimate_id="reach-3f",
        tenant_id=tenant_id,
        owner=OWNER,
        platform=ResearchPlatform.FACEBOOK_AUDIENCE_INSIGHTS,
        audience=AudienceDefinition(
            location="United States",
            age="35-50",
            gender="all",
            interests=(
                InterestSignal(
                    kind=InterestKind.EXPERT,
                    value="small service firm coach",
                ),
            ),
        ),
        estimated_reach=180000,
        source_note="Facebook Audience Insights sizing",
        captured_on=ON,
    )


def package(**overrides) -> DiagnosisPackage:
    values = {
        "package_id": "diagnosis-3f",
        "tenant_id": TENANT,
        "avatar": avatar(),
        "avatar_version": 1,
        "business_snapshot": snapshot(),
        "business_snapshot_version": 1,
        "offer_funnel_audit": audit(),
        "offer_funnel_audit_version": 1,
        "awareness_map": awareness_map(),
        "awareness_map_version": 1,
        "audience_reach_estimate": reach(),
        "audience_reach_estimate_version": 1,
    }
    values.update(overrides)
    return DiagnosisPackage(**values)


def working_stage_run(stage_number: int = 1, **overrides) -> StageRun:
    values = {
        "engagement": "ws-3f",
        "stage_number": stage_number,
        "template_version": stage_zero_to_ten_template().version,
        "assigned_owner": OWNER,
    }
    values.update(overrides)
    run = StageRun(**values)
    run.start(
        actor=OWNER,
        reason="stage work began",
        on=ON,
        correlation_id=CORRELATION,
    )
    return run


def seed_stage_zero(ledger: GateLedger, template, *, on: date = ON) -> None:
    """Record a passing stage 0 decision so the stage 1 prerequisite is met."""

    kinds = template.required_asset_kinds(0)
    gate = StageGate.from_template(template, 0, {kind: 1 for kind in kinds})
    gate.approver = APPROVER
    gate.proposed_by = OWNER
    for asset in sorted(gate.required_assets, key=str):
        request = ApprovalRequest(
            asset=asset,
            scope=SCOPE_ZERO,
            requested_by=OWNER,
            approver=APPROVER,
        )
        request.approve(actor=APPROVER, on=on, rationale="stage 0 evidenced")
        gate.record_asset_approval(request)
    gate.state = GateState.APPROVED
    decision = GateDecision.from_gate(
        gate,
        ledger=ledger,
        reviewer=APPROVER,
        scope=SCOPE_ZERO,
        checkpoint_evidence="all twelve stage 0 assets reviewed",
        disposition=GateDisposition.APPROVED,
        rationale="intake complete and owned",
        on=on,
        assigned_owner=OWNER,
        due_on=DUE,
    )
    ledger.record(decision)


class StageOneGateAssemblerTests(unittest.TestCase):
    def setUp(self):
        self.assembler = StageOneGateAssembler()
        self.template = stage_zero_to_ten_template()

    def assemble(self, *, workspace_=None, package_=None, approver=APPROVER, claims_=None, **overrides):
        return self.assembler.assemble(
            template=overrides.pop("template", self.template),
            workspace=workspace_ or workspace(),
            package=package_ or package(),
            approver=approver,
            claims=claims_ if claims_ is not None else claims(),
            **overrides,
        )

    def test_a_reviewed_diagnosis_package_assembles_the_canonical_stage_one_gate(self):
        gate = self.assemble()

        self.assertEqual(1, gate.stage_number)
        self.assertEqual(self.template.version, gate.template_version)
        self.assertEqual("Avatar Locked", gate.checkpoint)
        self.assertEqual(frozenset({0}), gate.dependencies)
        self.assertEqual(APPROVER, gate.approver)
        self.assertEqual(
            self.template.required_asset_kinds(1),
            {ref.asset_id for ref in gate.required_assets},
        )
        self.assertEqual(10, len(gate.required_assets))

    def test_the_gate_pins_the_exact_version_each_reviewed_asset_carries(self):
        gate = self.assemble(
            package_=package(
                avatar_version=2,
                business_snapshot_version=3,
                offer_funnel_audit_version=4,
            )
        )

        versions = {ref.asset_id: ref.version for ref in gate.required_assets}
        self.assertEqual(2, versions["avatar-profile"])
        self.assertEqual(2, versions["voice-notes"])
        self.assertEqual(3, versions["business-snapshot"])
        self.assertEqual(4, versions["offer-funnel-audit"])

    def test_the_assembler_records_the_author_distinct_from_the_approver(self):
        gate = self.assemble(proposed_by=OWNER)

        self.assertEqual(OWNER, gate.proposed_by)
        self.assertNotEqual(gate.approver, gate.proposed_by)

    def test_a_cross_tenant_package_cannot_assemble_a_gate(self):
        foreign = DiagnosisPackage(
            package_id="diagnosis-other",
            tenant_id=OTHER_TENANT,
            avatar=avatar(tenant_id=OTHER_TENANT),
            avatar_version=1,
            business_snapshot=snapshot(tenant_id=OTHER_TENANT),
            business_snapshot_version=1,
            offer_funnel_audit=audit(tenant_id=OTHER_TENANT),
            offer_funnel_audit_version=1,
            awareness_map=awareness_map(tenant_id=OTHER_TENANT),
            awareness_map_version=1,
            audience_reach_estimate=reach(tenant_id=OTHER_TENANT),
            audience_reach_estimate_version=1,
        )

        with self.assertRaises(TenantBoundaryError):
            self.assemble(package_=foreign)

    def test_unsourced_avatar_evidence_cannot_assemble_a_gate(self):
        with self.assertRaises(AvatarLockedError):
            self.assemble(
                claims_=(
                    sourced_claim(AVATAR_CLAIM, provenance=ProvenanceClass.DERIVED),
                    sourced_claim(SNAPSHOT_CLAIM),
                    sourced_claim(AUDIT_CLAIM),
                )
            )

    def test_unsourced_snapshot_evidence_cannot_assemble_a_gate(self):
        with self.assertRaises(UnsourcedDiagnosisEvidenceError):
            self.assemble(
                claims_=(
                    sourced_claim(AVATAR_CLAIM),
                    sourced_claim(SNAPSHOT_CLAIM, provenance=ProvenanceClass.PROPOSED),
                    sourced_claim(AUDIT_CLAIM),
                )
            )

    def test_an_untargetable_awareness_map_cannot_assemble_a_gate(self):
        unaware = MarketAwarenessMap(
            map_id="awareness-3f",
            tenant_id=TENANT,
            primary_level=MarketAwarenessLevel.COMPLETELY_UNAWARE,
            research_evidence=("no active search for the problem",),
            message_requirements=("educate the market before any offer",),
        )

        with self.assertRaises(MarketAwarenessTargetingError):
            self.assemble(package_=package(awareness_map=unaware))

    def test_unsourced_audit_evidence_cannot_assemble_a_gate(self):
        with self.assertRaises(UnsourcedDiagnosisEvidenceError):
            self.assemble(
                claims_=(
                    sourced_claim(AVATAR_CLAIM),
                    sourced_claim(SNAPSHOT_CLAIM),
                    sourced_claim(AUDIT_CLAIM, provenance=ProvenanceClass.UNKNOWN),
                )
            )

    def test_an_approver_without_workspace_authority_cannot_assemble_a_gate(self):
        with self.assertRaises(GateApproverNotAuthorizedError) as caught:
            self.assemble(approver="stranger")
        self.assertIn("stranger", str(caught.exception))

    def test_an_absent_approver_cannot_assemble_a_gate(self):
        with self.assertRaises(GateApproverNotAuthorizedError):
            self.assemble(approver="")

    def test_the_assembler_does_not_mutate_the_workspace_or_package(self):
        root = workspace()
        box = package()

        self.assemble(workspace_=root, package_=box)

        self.assertEqual(2, len(root.authorities))
        self.assertEqual(1, len(box.avatar.pains))


class StageOneGateRecorderTests(unittest.TestCase):
    def setUp(self):
        self.recorder = StageOneGateRecorder()
        self.assembler = StageOneGateAssembler()
        self.template = stage_zero_to_ten_template()

    def seeded_ledger(self) -> GateLedger:
        ledger = GateLedger(self.template)
        seed_stage_zero(ledger, self.template)
        return ledger

    def assembled_gate(self, approver=APPROVER, proposed_by=OWNER):
        return self.assembler.assemble(
            template=self.template,
            workspace=workspace(),
            package=package(),
            approver=approver,
            claims=claims(),
            proposed_by=proposed_by,
        )

    def record(self, gate, ledger, **overrides):
        return self.recorder.record(
            gate=gate,
            workspace=overrides.pop("workspace_", workspace()),
            ledger=ledger,
            scope=overrides.pop("scope", SCOPE_ONE),
            checkpoint_evidence=overrides.pop(
                "checkpoint_evidence", "all nine stage 1 assets reviewed"
            ),
            rationale=overrides.pop("rationale", "diagnosis complete and sourced"),
            assigned_owner=overrides.pop("assigned_owner", OWNER),
            due_on=overrides.pop("due_on", DUE),
            on=overrides.pop("on", ON),
            **overrides,
        )

    def test_records_a_passing_stage_one_decision_from_the_assembled_gate(self):
        ledger = self.seeded_ledger()

        decision = self.record(self.assembled_gate(), ledger)

        self.assertEqual(1, decision.stage_number)
        self.assertIs(GateDisposition.APPROVED, decision.disposition)
        self.assertEqual("Avatar Locked", decision.checkpoint)
        self.assertEqual(frozenset({0}), decision.dependencies)
        self.assertEqual(APPROVER, decision.reviewer)
        self.assertIs(decision, ledger.decision_for(1))
        self.assertTrue(ledger.has_passing_decision(1, on=ON))

    def test_one_approved_exact_version_request_per_required_asset(self):
        ledger = self.seeded_ledger()

        decision = self.record(self.assembled_gate(), ledger)

        self.assertEqual(10, len(decision.asset_approvals))
        for request in decision.asset_approvals:
            self.assertEqual(SCOPE_ONE, request.scope)
            self.assertEqual(APPROVER, request.approver)
            self.assertIn(request.asset, decision.required_assets)
        self.assertEqual(frozenset(), decision.unapproved_assets())

    def test_a_non_stage_one_gate_cannot_be_recorded(self):
        kinds = self.template.required_asset_kinds(0)
        gate = StageGate.from_template(self.template, 0, {kind: 1 for kind in kinds})
        gate.proposed_by = OWNER
        gate.approver = APPROVER
        ledger = self.seeded_ledger()

        with self.assertRaises(NotStageOneGateError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(1))

    def test_an_approver_without_workspace_authority_cannot_record(self):
        gate = self.assembled_gate()
        gate.approver = "stranger"
        ledger = self.seeded_ledger()

        with self.assertRaises(GateApproverNotAuthorizedError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(1))

    def test_a_gate_without_an_author_cannot_record(self):
        gate = self.assembled_gate(proposed_by=None)
        ledger = self.seeded_ledger()

        with self.assertRaises(GateAuthorRequiredError):
            self.record(gate, ledger)

        self.assertIsNone(ledger.decision_for(1))

    def test_the_author_cannot_approve_their_own_gate(self):
        gate = self.assembled_gate(approver=OWNER, proposed_by=OWNER)
        ledger = self.seeded_ledger()

        with self.assertRaises(SelfApprovalError):
            self.record(gate, ledger)

    def test_the_assigned_owner_must_hold_workspace_authority(self):
        gate = self.assembled_gate()
        ledger = self.seeded_ledger()

        with self.assertRaises(StageOwnerNotAuthorizedError):
            self.record(gate, ledger, assigned_owner="stranger")

    def test_recording_does_not_mutate_the_workspace(self):
        root = workspace()
        ledger = self.seeded_ledger()

        self.record(self.assembled_gate(), ledger, workspace_=root)

        self.assertEqual(2, len(root.authorities))


class RecordStageOneGateHandlerTests(unittest.TestCase):
    def setUp(self):
        self.handler = RecordStageOneGateHandler()
        self.template = stage_zero_to_ten_template()

    def ledger(self) -> GateLedger:
        ledger = GateLedger(self.template)
        seed_stage_zero(ledger, self.template)
        return ledger

    def command(self, *, workspace_=None, package_=None, claims_=None, stage_run_=None, **overrides):
        values = {
            "template": self.template,
            "workspace": workspace_ or workspace(),
            "package": package_ or package(),
            "claims": claims_ if claims_ is not None else claims(),
            "stage_run": stage_run_ if stage_run_ is not None else working_stage_run(),
            "approver": APPROVER,
            "proposed_by": OWNER,
            "scope": SCOPE_ONE,
            "checkpoint_evidence": "all nine stage 1 assets reviewed",
            "rationale": "diagnosis complete and sourced",
            "assigned_owner": OWNER,
            "due_on": DUE,
            "on": ON,
            "correlation_id": CORRELATION,
        }
        values.update(overrides)
        return RecordStageOneGateCommand(**values)

    def test_records_a_passing_stage_one_decision_and_closes_the_run(self):
        ledger = self.ledger()
        run = working_stage_run()

        decision = self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        self.assertEqual(1, decision.stage_number)
        self.assertIs(decision, ledger.decision_for(1))
        self.assertTrue(run.is_complete)
        self.assertIs(decision, run.accepted_decision)
        self.assertEqual(ON, run.exited_at)

    def test_verified_progress_counts_stage_zero_and_stage_one(self):
        ledger = self.ledger()
        run = working_stage_run()

        self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        progress = PipelineProgress.from_ledger(ledger, on=ON)
        self.assertEqual(2, progress.approved_gates)
        self.assertTrue(run.is_complete)

    def test_a_run_for_another_stage_cannot_be_closed(self):
        ledger = self.ledger()

        with self.assertRaises(StageRunNotStageOneError):
            self.handler.handle(
                self.command(stage_run_=working_stage_run(stage_number=2)),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(1))

    def test_a_run_for_another_template_version_cannot_be_closed(self):
        ledger = self.ledger()

        with self.assertRaises(StageRunNotStageOneError):
            self.handler.handle(
                self.command(
                    stage_run_=working_stage_run(template_version="2025.9")
                ),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(1))

    def test_a_not_completable_run_does_not_record_a_decision(self):
        ledger = self.ledger()
        run = StageRun(
            engagement="ws-3f",
            stage_number=1,
            template_version=self.template.version,
            assigned_owner=OWNER,
        )

        with self.assertRaises(StageRunNotCompletableError):
            self.handler.handle(self.command(stage_run_=run), ledger=ledger)

        self.assertIsNone(ledger.decision_for(1))
        self.assertFalse(run.is_complete)

    def test_stage_one_cannot_pass_while_stage_zero_is_unapproved(self):
        empty = GateLedger(self.template)

        with self.assertRaises(GateDecisionError):
            self.handler.handle(self.command(), ledger=empty)

        self.assertIsNone(empty.decision_for(1))

    def test_the_use_case_owns_assembly_so_unsourced_evidence_cannot_be_bypassed(self):
        ledger = self.ledger()

        with self.assertRaises(AvatarLockedError):
            self.handler.handle(
                self.command(
                    claims_=(
                        sourced_claim(
                            AVATAR_CLAIM, provenance=ProvenanceClass.DERIVED
                        ),
                        sourced_claim(SNAPSHOT_CLAIM),
                        sourced_claim(AUDIT_CLAIM),
                    )
                ),
                ledger=ledger,
            )

        self.assertIsNone(ledger.decision_for(1))

    def test_the_use_case_does_not_mutate_the_workspace_or_package(self):
        root = workspace()
        box = package()
        ledger = self.ledger()

        self.handler.handle(
            self.command(workspace_=root, package_=box), ledger=ledger
        )

        self.assertEqual(2, len(root.authorities))
        self.assertEqual(1, len(box.avatar.pains))


if __name__ == "__main__":
    unittest.main()
