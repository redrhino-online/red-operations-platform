"""Application commands for the Engagement bounded context.

SPEC.md section 6: application use cases depend on domain types and ports; entry
points call use cases rather than reaching into persistence. A command is the
typed, immutable request that carries every input a use case needs, so an entry
point cannot smuggle a hand-built governance gate past the stage 0 checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from redops.contexts.commercial.domain.value_objects import (
    CampaignMessagePackage,
    CurrencyPackage,
    DiagnosisPackage,
    DiagnosticPackage,
    OfferPackage,
    SignaturePackage,
)
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.value_objects import IntakePackage
from redops.contexts.execution.domain.value_objects import (
    FunnelIntegrationPackage,
    LaunchQAPackage,
)
from redops.contexts.governance.domain.entities import StageRun
from redops.contexts.governance.domain.value_objects import StageTemplate
from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.production.domain.value_objects import (
    AuthorityAmplifierPackage,
)


@dataclass(frozen=True)
class RecordStageZeroGateCommand:
    """Request to assemble and record the stage 0 "Production Ready" gate.

    The command carries the real ``IntakePackage``, the workspace authority
    registry, the supporting ``Claim`` set and the exact decision metadata; it
    deliberately carries no ``StageGate``. The use case builds the canonical gate
    itself from the package, so a caller cannot substitute a hand-built gate and
    skip the owner-authority and sourced-evidence checks (SPEC.md sections 3, 4
    and 6).

    It also carries the stage 0 ``StageRun`` to close. Recording a passing gate
    and completing the stage are one application operation, so the durable
    ``GateDecision`` and the stage status cannot drift apart, and SPEC.md section
    4's "stage completion requires gate acceptance, not merely activity" holds at
    the application boundary.
    """

    template: StageTemplate
    workspace: ClientWorkspace
    package: IntakePackage
    claims: tuple[Claim, ...]
    stage_run: StageRun
    approver: str
    scope: str
    checkpoint_evidence: str
    rationale: str
    assigned_owner: str
    due_on: date
    on: date
    correlation_id: str
    proposed_by: str | None = None
    next_action: str = ""


@dataclass(frozen=True)
class RecordStageOneGateCommand:
    """Request to assemble and record the stage 1 "Avatar Locked" gate.

    The command carries the reviewed ``DiagnosisPackage`` (the bridge that
    projects the three stage 1 values onto the nine canonical kinds), the
    workspace authority registry, the supporting ``Claim`` set and the exact
    decision metadata; it deliberately carries no ``StageGate``. The use case
    builds the canonical gate itself from the package, so a caller cannot
    substitute a hand-built gate and skip the sourced-evidence, approver-authority
    and owner-authority checks (SPEC.md sections 3, 4 and 6).

    It also carries the stage 1 ``StageRun`` to close. Recording a passing gate
    and completing the stage are one application operation, so the durable
    ``GateDecision`` and the stage status cannot drift apart. Stage 1 depends on
    stage 0, so the passing stage 0 decision must already be present in the
    ``GateLedger`` the use case is given (SPEC.md section 4).
    """

    template: StageTemplate
    workspace: ClientWorkspace
    package: DiagnosisPackage
    claims: tuple[Claim, ...]
    stage_run: StageRun
    approver: str
    scope: str
    checkpoint_evidence: str
    rationale: str
    assigned_owner: str
    due_on: date
    on: date
    correlation_id: str
    proposed_by: str | None = None
    next_action: str = ""


@dataclass(frozen=True)
class RecordStageTwoGateCommand:
    """Request to assemble and record the stage 2 "Currency Locked" gate.

    The command carries the reviewed ``CurrencyPackage`` (the bridge that
    projects the four stage 2 values onto the ten canonical kinds), the workspace
    authority registry and the exact decision metadata; it deliberately carries
    no ``StageGate``. The use case builds the canonical gate itself from the
    package, so a caller cannot substitute a hand-built gate and skip the
    tenant-boundary, approver-authority and owner-authority checks (SPEC.md
    sections 3, 4 and 6). Unlike the stage 1 command it carries no claims,
    because the "Currency Locked" checkpoint turns on the primary currency's
    internal specificity, which ``PrimaryCurrency`` already enforces, rather than
    on external customer evidence.

    It also carries the stage 2 ``StageRun`` to close. Recording a passing gate
    and completing the stage are one application operation, so the durable
    ``GateDecision`` and the stage status cannot drift apart. Stage 2 depends on
    stage 1, so the passing stage 1 decision must already be present in the
    ``GateLedger`` the use case is given (SPEC.md section 4).
    """

    template: StageTemplate
    workspace: ClientWorkspace
    package: CurrencyPackage
    stage_run: StageRun
    approver: str
    scope: str
    checkpoint_evidence: str
    rationale: str
    assigned_owner: str
    due_on: date
    on: date
    correlation_id: str
    proposed_by: str | None = None
    next_action: str = ""


@dataclass(frozen=True)
class RecordStageThreeGateCommand:
    """Request to assemble and record the stage 3 "Diagnostic Model Approved" gate.

    The command carries the reviewed ``DiagnosticPackage`` (the bridge that
    projects the single stage 3 ``DiagnosticModel`` onto the ten canonical kinds),
    the workspace authority registry and the exact decision metadata; it
    deliberately carries no ``StageGate``. The use case builds the canonical gate
    itself from the package, so a caller cannot substitute a hand-built gate and
    skip the tenant-boundary, approver-authority and owner-authority checks
    (SPEC.md sections 3, 4 and 6). Unlike the stage 1 command it carries no
    claims, because the "Diagnostic Model Approved" checkpoint turns on
    adjacent-level observable distinguishability, which ``DiagnosticModel``
    already enforces, rather than on external customer evidence.

    It also carries the stage 3 ``StageRun`` to close. Recording a passing gate
    and completing the stage are one application operation, so the durable
    ``GateDecision`` and the stage status cannot drift apart. Stage 3 depends on
    stage 2, so the passing stage 2 decision must already be present in the
    ``GateLedger`` the use case is given (SPEC.md section 4).
    """

    template: StageTemplate
    workspace: ClientWorkspace
    package: DiagnosticPackage
    stage_run: StageRun
    approver: str
    scope: str
    checkpoint_evidence: str
    rationale: str
    assigned_owner: str
    due_on: date
    on: date
    correlation_id: str
    proposed_by: str | None = None
    next_action: str = ""


@dataclass(frozen=True)
class RecordStageFiveGateCommand:
    """Request to assemble and record the stage 5 "Offer Locked" gate.

    The command carries the reviewed ``OfferPackage`` (the bridge that projects
    the single stage 5 ``DeliverySpecification`` onto the twelve canonical kinds),
    the workspace authority registry and the exact decision metadata; it
    deliberately carries no ``StageGate``. The use case builds the canonical gate
    itself from the package, so a caller cannot substitute a hand-built gate and
    skip the tenant-boundary, approver-authority and owner-authority checks
    (SPEC.md sections 3, 4 and 6). Unlike the stage 1 command it carries no
    claims, because the "Offer Locked" checkpoint turns on every delivered method
    step carrying an action, actor, deliverable, timing and measure, which
    ``DeliverySpecification`` already enforces at construction, rather than on
    external customer evidence.

    It also carries the stage 5 ``StageRun`` to close. Recording a passing gate
    and completing the stage are one application operation, so the durable
    ``GateDecision`` and the stage status cannot drift apart. Stage 5 depends on
    stage 4, so the passing stage 4 decision must already be present in the
    ``GateLedger`` the use case is given (SPEC.md section 4).
    """

    template: StageTemplate
    workspace: ClientWorkspace
    package: OfferPackage
    stage_run: StageRun
    approver: str
    scope: str
    checkpoint_evidence: str
    rationale: str
    assigned_owner: str
    due_on: date
    on: date
    correlation_id: str
    proposed_by: str | None = None
    next_action: str = ""


@dataclass(frozen=True)
class RecordStageFourGateCommand:
    """Request to assemble and record the stage 4 "IP Architecture Locked" gate.

    The command carries the reviewed ``SignaturePackage`` (the bridge that
    projects the single stage 4 ``SignatureSolution`` onto the twelve canonical
    kinds), the workspace authority registry and the exact decision metadata; it
    deliberately carries no ``StageGate``. The use case builds the canonical gate
    itself from the package, so a caller cannot substitute a hand-built gate and
    skip the tenant-boundary, approver-authority and owner-authority checks
    (SPEC.md sections 3, 4 and 6). Unlike the stage 1 command it carries no
    claims, because the "IP Architecture Locked" checkpoint turns on the coherence
    and continuity of the reviewed transformation, which ``SignatureSolution``
    already enforces at construction, rather than on external customer evidence.

    It also carries the stage 4 ``StageRun`` to close. Recording a passing gate
    and completing the stage are one application operation, so the durable
    ``GateDecision`` and the stage status cannot drift apart. Stage 4 depends on
    stage 3, so the passing stage 3 decision must already be present in the
    ``GateLedger`` the use case is given (SPEC.md section 4).
    """

    template: StageTemplate
    workspace: ClientWorkspace
    package: SignaturePackage
    stage_run: StageRun
    approver: str
    scope: str
    checkpoint_evidence: str
    rationale: str
    assigned_owner: str
    due_on: date
    on: date
    correlation_id: str
    proposed_by: str | None = None
    next_action: str = ""


@dataclass(frozen=True)
class RecordStageSixGateCommand:
    """Request to assemble and record the stage 6 "Campaign Message Approved" gate.

    The command carries the reviewed ``CampaignMessagePackage`` (the bridge that
    projects the single approved stage 6 ``CampaignMessage`` onto the twelve
    canonical kinds), the workspace authority registry and the exact decision
    metadata; it deliberately carries no ``StageGate``. The use case builds the
    canonical gate itself from the package, so a caller cannot substitute a
    hand-built gate and skip the tenant-boundary, approval, approver-authority and
    owner-authority checks (SPEC.md sections 3, 4 and 6). Unlike the stage 2
    through 5 commands it carries no claims, because the "Campaign Message
    Approved" checkpoint turns on the message's congruence with the approved stage
    5 offer and the approved method, which ``CampaignMessage.approve`` already
    enforces, rather than on external customer evidence.

    It also carries the stage 6 ``StageRun`` to close. Recording a passing gate
    and completing the stage are one application operation, so the durable
    ``GateDecision`` and the stage status cannot drift apart. Stage 6 depends on
    stage 5, so the passing stage 5 decision must already be present in the
    ``GateLedger`` the use case is given (SPEC.md section 4).
    """

    template: StageTemplate
    workspace: ClientWorkspace
    package: CampaignMessagePackage
    stage_run: StageRun
    approver: str
    scope: str
    checkpoint_evidence: str
    rationale: str
    assigned_owner: str
    due_on: date
    on: date
    correlation_id: str
    proposed_by: str | None = None
    next_action: str = ""


@dataclass(frozen=True)
class RecordStageSevenGateCommand:
    """Request to assemble and record the stage 7 "Authority Amplifier Approved" gate.

    The command carries the reviewed ``AuthorityAmplifierPackage`` (the bridge
    that projects the single stage 7 ``AuthorityAmplifier`` onto the nine
    canonical kinds), the workspace authority registry and the exact decision
    metadata; it deliberately carries no ``StageGate``. The use case builds the
    canonical gate itself from the package, so a caller cannot substitute a
    hand-built gate and skip the tenant-boundary, creative-acceptance,
    approver-authority and owner-authority checks (SPEC.md sections 3, 4 and 6).
    Unlike the stage 2 through 5 commands it carries no claims, because the
    "Authority Amplifier Approved" checkpoint turns on the amplifier's own
    two-stage approval -- script and supported proof before visual production,
    then final creative acceptance -- which ``AuthorityAmplifier`` already
    enforces, rather than on external customer evidence.

    It also carries the stage 7 ``StageRun`` to close. Recording a passing gate
    and completing the stage are one application operation, so the durable
    ``GateDecision`` and the stage status cannot drift apart. Stage 7 depends on
    stage 6, so the passing stage 6 decision must already be present in the
    ``GateLedger`` the use case is given (SPEC.md section 4).
    """

    template: StageTemplate
    workspace: ClientWorkspace
    package: AuthorityAmplifierPackage
    stage_run: StageRun
    approver: str
    scope: str
    checkpoint_evidence: str
    rationale: str
    assigned_owner: str
    due_on: date
    on: date
    correlation_id: str
    proposed_by: str | None = None
    next_action: str = ""


@dataclass(frozen=True)
class RecordStageEightGateCommand:
    """Request to assemble and record the stage 8 "Funnel Complete" gate.

    The command carries the reviewed ``FunnelIntegrationPackage`` (the bridge that
    projects the single completed stage 8 ``FunnelIntegration`` onto the thirteen
    canonical kinds), the workspace authority registry and the exact decision
    metadata; it deliberately carries no ``StageGate``. The use case builds the
    canonical gate itself from the package, so a caller cannot substitute a
    hand-built gate and skip the tenant-boundary, approver-authority and
    owner-authority checks (SPEC.md sections 3, 4 and 6). Unlike the stage 1
    command it carries no claims, because the "Funnel Complete" checkpoint turns
    on the funnel's own completion -- a same-tenant prospect path dry run whose
    capture, engagement and conversion handoffs all routed with reliable records
    and ownership -- which ``FunnelIntegrationPackage`` already enforces, rather
    than on external customer evidence.

    It also carries the stage 8 ``StageRun`` to close. Recording a passing gate
    and completing the stage are one application operation, so the durable
    ``GateDecision`` and the stage status cannot drift apart. Stage 8 depends on
    stage 7, so the passing stage 7 decision must already be present in the
    ``GateLedger`` the use case is given (SPEC.md section 4).
    """

    template: StageTemplate
    workspace: ClientWorkspace
    package: FunnelIntegrationPackage
    stage_run: StageRun
    approver: str
    scope: str
    checkpoint_evidence: str
    rationale: str
    assigned_owner: str
    due_on: date
    on: date
    correlation_id: str
    proposed_by: str | None = None
    next_action: str = ""


@dataclass(frozen=True)
class RecordStageNineGateCommand:
    """Request to assemble and record the stage 9 "Launch Approved" gate.

    The command carries the reviewed ``LaunchQAPackage`` (the bridge that projects
    the single ready-for-traffic stage 9 ``LaunchQA`` onto the sixteen canonical
    kinds), the workspace authority registry and the exact decision metadata; it
    deliberately carries no ``StageGate``. The use case builds the canonical gate
    itself from the package, so a caller cannot substitute a hand-built gate and
    skip the tenant-boundary, approver-authority and owner-authority checks
    (SPEC.md sections 3, 4 and 6). Unlike the stage 1 command it carries no claims,
    because the "Launch Approved" checkpoint turns on the QA's own completion --
    the complete same-tenant check set, the critical-path outcomes and the
    designated human traffic authorization -- which ``LaunchQAPackage`` already
    enforces, rather than on external customer evidence.

    It also carries the stage 9 ``StageRun`` to close. Recording a passing gate
    and completing the stage are one application operation, so the durable
    ``GateDecision`` and the stage status cannot drift apart. Stage 9 depends on
    stage 8, so the passing stage 8 decision must already be present in the
    ``GateLedger`` the use case is given (SPEC.md section 4).
    """

    template: StageTemplate
    workspace: ClientWorkspace
    package: LaunchQAPackage
    stage_run: StageRun
    approver: str
    scope: str
    checkpoint_evidence: str
    rationale: str
    assigned_owner: str
    due_on: date
    on: date
    correlation_id: str
    proposed_by: str | None = None
    next_action: str = ""
