"""RED HTTP routes.

These routes are thin adapters. The stages route exposes the canonical 0-10
production template as read-only reference data from the pure Governance domain
(`stage_zero_to_ten_template`, SPEC.md section 4); it computes no domain rule,
holds no state and mutates nothing. Gate integrity, approval authority and
tenant scoping stay in the domain and application layers where they are
enforced and tested.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from redops.api.schemas import (
    ApprovalListResponse,
    ApprovalRecordResponse,
    AssetVersionResponse,
    AuthorityAmplifierInput,
    BuildListResponse,
    BuildObjectResponse,
    CampaignMessageInput,
    ClaimInput,
    ClaimListResponse,
    ClaimResponse,
    ClientWorkspaceListResponse,
    ClientWorkspaceResponse,
    CreateBuildRequest,
    CreateClaimRequest,
    CreateClientWorkspaceRequest,
    CreateSourceRecordRequest,
    DecisionListResponse,
    DecisionRecordResponse,
    EngagementProductionViewResponse,
    FunnelIntegrationInput,
    JourneyReleaseAssetResponse,
    JourneyReleaseListResponse,
    JourneyReleaseResponse,
    DismissInterventionRequest,
    InterventionDismissalResponse,
    InterventionListResponse,
    InterventionResponse,
    LaunchQAInput,
    MethodReferenceResponse,
    MethodVersionInput,
    MethodVersionListResponse,
    MetricDefinitionResponse,
    MeasurementListResponse,
    MeasurementRecordResponse,
    OfferListResponse,
    OfferVersionInput,
    OfferVersionResponse,
    RecordMeasurementRequest,
    RecordJourneyReleaseRequest,
    RecordStageEightGateRequest,
    RecordStageFiveGateRequest,
    RecordStageFourGateRequest,
    RecordStageNineGateRequest,
    RecordStageOneGateRequest,
    RecordStageSevenGateRequest,
    RecordStageSixGateRequest,
    RecordStageTenGateRequest,
    RecordStageThreeGateRequest,
    RecordStageTwoGateRequest,
    RecordStageZeroGateRequest,
    SourceRecordListResponse,
    SourceRecordResponse,
)
from redops.contexts.commercial.application.ports import (
    CampaignMessageRepository,
    OfferVersionRepository,
)
from redops.contexts.commercial.domain.entities import (
    CampaignMessage,
    OfferVersion,
)
from redops.contexts.commercial.domain.errors import (
    CampaignMessageVersionConflictError,
    CommercialError,
    OfferVersionConflictError,
)
from redops.contexts.commercial.infrastructure.repositories import (
    campaign_message_repository_from_env,
    offer_version_repository_from_env,
)
from redops.contexts.commercial.domain.value_objects import (
    AUTHORITY_AMPLIFIER_BEATS,
    AudienceDefinition,
    AudienceReachEstimate,
    AvatarProfile,
    BusinessSnapshot,
    CampaignMessagePackage,
    ContentChannel,
    ContentCrusher,
    ContentIdea,
    ContentIdeaSource,
    ContentPlan,
    ContentPlanChannel,
    ContentPromise,
    ContentRoadmap,
    ContentTheme,
    ContentTopic,
    CurrencyInventory,
    CurrencyPackage,
    DeliverySpecification,
    DiagnosisPackage,
    DiagnosticPackage,
    InterestKind,
    InterestSignal,
    MarketAwarenessLevel,
    MarketAwarenessMap,
    MethodReference,
    MillionDollarMessage,
    OfferFunnelAudit,
    OfferPackage,
    PositioningDecision,
    ProductMatrixModel,
    ProductModule,
    ProductProgram,
    ProgramCadence,
    ProgramPricingBasis,
    ResearchPlatform,
    SignaturePackage,
    StepDelivery,
    TargetMarketCandidate,
    TargetMarketMatchmaker,
)
from redops.contexts.engagement.application.commands import (
    RecordStageEightGateCommand,
    RecordStageFiveGateCommand,
    RecordStageFourGateCommand,
    RecordStageNineGateCommand,
    RecordStageOneGateCommand,
    RecordStageSevenGateCommand,
    RecordStageSixGateCommand,
    RecordStageTenGateCommand,
    RecordStageThreeGateCommand,
    RecordStageTwoGateCommand,
    RecordStageZeroGateCommand,
)
from redops.contexts.engagement.application.handlers import (
    RecordStageEightGateHandler,
    RecordStageFiveGateHandler,
    RecordStageFourGateHandler,
    RecordStageNineGateHandler,
    RecordStageOneGateHandler,
    RecordStageSevenGateHandler,
    RecordStageSixGateHandler,
    RecordStageTenGateHandler,
    RecordStageThreeGateHandler,
    RecordStageTwoGateHandler,
    RecordStageZeroGateHandler,
)
from redops.contexts.engagement.application.ports import ClientWorkspaceStore
from redops.contexts.engagement.domain.entities import ClientWorkspace
from redops.contexts.engagement.domain.errors import (
    ClientWorkspaceNotFoundError,
    EngagementError,
)
from redops.contexts.engagement.infrastructure.repositories import (
    client_workspace_store_from_env,
)
from redops.contexts.engagement.domain.value_objects import (
    ClientAuthority,
    IntakeAsset,
    IntakeAssetKind,
    IntakePackage,
)
from redops.contexts.execution.application.ports import (
    FunnelIntegrationRepository,
    JourneyReleaseRepository,
    LaunchQARepository,
)
from redops.contexts.execution.domain.entities import (
    FunnelIntegration,
    LaunchQA,
    PerformanceBaseline,
)
from redops.contexts.execution.domain.errors import (
    ExecutionError,
    FunnelVersionConflictError,
    JourneyReleaseError,
    LaunchQAVersionConflictError,
)
from redops.contexts.execution.domain.journey_release import JourneyRelease
from redops.contexts.execution.domain.value_objects import (
    ComplianceAsset,
    ComplianceAssetKind,
    CompliancePackage,
    ComplianceWaiver,
    FunnelAssetPackage,
    FunnelIntegrationPackage,
    HandoffKind,
    HandoffOutcome,
    HandoffRecord,
    LaunchAssetPackage,
    LaunchQAPackage,
    MilestoneKind,
    MilestoneObservation,
    ObservationStatus,
    PerformanceBaselinePackage,
    ProspectPathDryRun,
    QACheck,
    QACheckKind,
    QACheckOutcome,
    TrafficAuthorization,
)
from redops.contexts.execution.infrastructure.repositories import (
    funnel_integration_repository_from_env,
    journey_release_repository_from_env,
    launch_qa_repository_from_env,
)
from redops.contexts.governance.application.ports import (
    GateLedgerRepository,
    StageRunRepository,
)
from redops.contexts.governance.application.queries import (
    EngagementProductionViewQuery,
    GetEngagementProductionViewHandler,
)
from redops.contexts.governance.domain.entities import StageRun
from redops.contexts.governance.domain.errors import GovernanceError
from redops.contexts.governance.domain.templates import stage_zero_to_ten_template
from redops.contexts.governance.domain.value_objects import (
    EngagementProductionView,
    MetricReportingView,
    StageAssetVersion,
    StageProductionView,
)
from redops.contexts.governance.infrastructure.repositories import (
    gate_ledger_repository_from_env,
    stage_run_repository_from_env,
)
from redops.contexts.knowledge.application.ports import (
    ClaimStore,
    SourceRecordStore,
)
from redops.contexts.knowledge.domain.entities import Claim, SourceRecord
from redops.contexts.knowledge.domain.errors import (
    ClaimCitationError,
    KnowledgeError,
)
from redops.contexts.knowledge.infrastructure.repositories import (
    claim_store_from_env,
    source_record_store_from_env,
)
from redops.contexts.knowledge.domain.value_objects import (
    ProvenanceClass,
    SourceCitation,
)
from redops.contexts.method.application.ports import MethodVersionRepository
from redops.contexts.method.domain.entities import (
    DiagnosticModel,
    MethodVersion,
    SignatureSolution,
)
from redops.contexts.method.domain.transformations import (
    Transformation,
    TransformationScope,
    ThirteenTransformations,
)
from redops.contexts.method.domain.errors import (
    MethodError,
    MethodVersionConflictError,
)
from redops.contexts.method.domain.value_objects import (
    PrimaryCurrency,
    ProfitPyramidLevel,
    SemanticVersion,
    SignatureStep,
    TransformationPhase,
)
from redops.contexts.method.infrastructure.repositories import (
    method_version_repository_from_env,
)
from redops.contexts.measurement.application.ports import MeasurementRegistry
from redops.contexts.measurement.domain.errors import MeasurementError
from redops.contexts.measurement.domain.value_objects import (
    MeasurementBasis,
    MeasurementRecord,
    MeasurementWindow,
    MetricDefinition,
    MetricDirection,
    MetricFunnelStep,
    MetricUnit,
)
from redops.contexts.measurement.infrastructure.repositories import (
    measurement_registry_from_env,
)
from redops.contexts.operations.application.ports import (
    InterventionDismissalRepository,
)
from redops.contexts.operations.domain.errors import OperationsError
from redops.contexts.operations.domain.policies import InterventionRankingPolicy
from redops.contexts.operations.domain.value_objects import (
    Intervention,
    InterventionDismissal,
    InterventionReason,
)
from redops.contexts.operations.infrastructure.repositories import (
    intervention_dismissal_repository_from_env,
)
from redops.contexts.production.application.ports import (
    AuthorityAmplifierRepository,
    BuildObjectRepository,
)
from redops.contexts.production.domain.entities import (
    AuthorityAmplifier,
    BuildObject,
)
from redops.contexts.production.domain.errors import (
    AuthorityAmplifierVersionConflictError,
    BuildTenantBoundaryError,
    InvalidBuildError,
    ProductionError,
)
from redops.contexts.production.domain.value_objects import (
    AuthorityAmplifierPackage,
    ScriptSection,
    ScriptSectionKind,
    VisualProductionPackage,
)
from redops.contexts.production.infrastructure.repositories import (
    authority_amplifier_repository_from_env,
    build_object_repository_from_env,
)
from redops.workflows.application.ports import WorkflowRunStore
from redops.workflows.infrastructure.repositories import (
    workflow_run_store_from_env,
)

router = APIRouter(prefix="/red", tags=["red"])

# The adapter is selected from configuration through an overridable dependency
# so the API is wired to the ``GateLedgerRepository`` port, not to a concrete
# store. ADR 0003 gives RED durable gate records: when ``DATABASE_URL`` is set
# the process serving traffic records into PostgreSQL, and without it (local
# development, the domain-only test interpreter) the process-local reference
# adapter stands in.
def get_gate_ledger_repository() -> Iterator[GateLedgerRepository]:
    """Provide the configured gate ledger seam to the API (SPEC.md section 6).

    The dependency owns one adapter for the request and releases any connection
    it opened when the request ends, so a durable write is committed per gate
    (SPEC.md sections 3 and 4). The store is chosen once from ``DATABASE_URL``;
    a request cannot silently downgrade to the process-local ledger, because a
    set-but-unusable configuration raises before the route runs.
    """

    repository = gate_ledger_repository_from_env(os.environ.get("DATABASE_URL"))
    try:
        yield repository
    finally:
        repository.close()


def get_stage_run_repository() -> Iterator[StageRunRepository]:
    """Provide the configured stage run seam to the API (SPEC.md section 6).

    The dependency owns one adapter for the request and releases any connection
    it opened when the request ends. The store is chosen once from
    ``DATABASE_URL``; a set-but-unusable configuration raises before the route
    runs, so a deployment cannot mistake a process-local stage run store for a
    durable one (SPEC.md sections 3 and 4).
    """

    repository = stage_run_repository_from_env(os.environ.get("DATABASE_URL"))
    try:
        yield repository
    finally:
        repository.close()


def get_client_workspace_store() -> Iterator[ClientWorkspaceStore]:
    """Provide the configured client workspace seam to the API (SPEC.md §6).

    SPEC.md section 3 makes the ClientWorkspace the tenant root every
    client-owned resource attaches to and the persisted authority registry a
    gate approves against. The dependency owns one adapter for the request and
    releases any connection it opened when the request ends; the store is chosen
    once from ``DATABASE_URL``, and a set-but-unusable configuration raises
    before the route runs, so a deployment cannot mistake a process-local
    workspace store for a durable one.
    """

    store = client_workspace_store_from_env(os.environ.get("DATABASE_URL"))
    try:
        yield store
    finally:
        store.close()


def get_source_record_store() -> Iterator[SourceRecordStore]:
    """Provide the configured source record seam to the API (SPEC.md §6).

    SPEC.md section 3 keeps a source record as the immutable original a claim
    cites, so the ``/clients/{id}/sources`` surface must read and write the same
    durable store the API and worker processes share. The dependency owns one
    adapter for the request and releases any connection it opened when the
    request ends; the store is chosen once from ``DATABASE_URL``, and a
    set-but-unusable configuration raises before the route runs, so a deployment
    cannot mistake a process-local source store for a durable one.
    """

    store = source_record_store_from_env(os.environ.get("DATABASE_URL"))
    try:
        yield store
    finally:
        store.close()


def get_claim_store() -> Iterator[ClaimStore]:
    """Provide the configured claim seam to the API (SPEC.md §6).

    SPEC.md section 7 lists ``/claims`` and section 3 keeps a claim a client
    resource, so the surface must read and write the same durable store the
    rest of the platform shares. The dependency owns one adapter for the request
    and releases any connection it opened when the request ends; the store is
    chosen once from ``DATABASE_URL``, and a set-but-unusable configuration raises
    before the route runs, so a deployment cannot mistake a process-local claim
    store for a durable one.
    """

    store = claim_store_from_env(os.environ.get("DATABASE_URL"))
    try:
        yield store
    finally:
        store.close()


def get_method_version_repository() -> Iterator[MethodVersionRepository]:
    """Provide the approved method version seam to the API (SPEC.md section 6).

    SPEC.md section 3 pins an exact method version and intended use at approval,
    and SPEC.md section 4 keeps the approved version identifiable, so the stage
    6 to 10 gates must resolve the approved method a prior gate pinned rather
    than trust a repeated request body. The dependency owns one adapter for the
    request and releases any connection it opened when the request ends, so the
    resolved version is read from the durable store and shared across the API
    and worker processes. The store is chosen once from ``DATABASE_URL``; a
    request cannot silently downgrade to a process-local method store, because a
    set-but-unusable configuration raises before the route runs.
    """

    repository = method_version_repository_from_env(
        os.environ.get("DATABASE_URL")
    )
    try:
        yield repository
    finally:
        repository.close()


def get_offer_version_repository() -> Iterator[OfferVersionRepository]:
    """Provide the production ready offer seam to the API (SPEC.md section 6).

    SPEC.md section 3 pins exact approved asset versions and intended use at a
    passing gate, and SPEC.md section 4 keeps the approved version identifiable,
    so the stage 6 to 10 gates must resolve the production ready stage 5 offer a
    prior gate pinned rather than trust a repeated request body. The dependency
    owns one adapter for the request and releases any connection it opened when
    the request ends, so the resolved offer is read from the durable store and
    shared across the API and worker processes. The store is chosen once from
    ``DATABASE_URL``; a request cannot silently downgrade to a process-local
    offer store, because a set-but-unusable configuration raises before the route
    runs.
    """

    repository = offer_version_repository_from_env(
        os.environ.get("DATABASE_URL")
    )
    try:
        yield repository
    finally:
        repository.close()


def get_build_object_repository() -> Iterator[BuildObjectRepository]:
    """Provide the production work item seam to the API (SPEC.md section 6).

    SPEC.md section 3 makes a BuildObject the unit of production work and section
    7 lists ``/builds``, so the surface must read and write the same durable store
    the build board and worker share. The dependency owns one adapter for the
    request and releases any connection it opened when the request ends; the store
    is chosen once from ``DATABASE_URL``, and a set-but-unusable configuration
    raises before the route runs, so a deployment cannot mistake a process-local
    build store for a durable one.
    """

    repository = build_object_repository_from_env(
        os.environ.get("DATABASE_URL")
    )
    try:
        yield repository
    finally:
        repository.close()


def get_measurement_registry() -> Iterator[MeasurementRegistry]:
    """Provide the stage 10 metric registry seam to the API (SPEC.md section 6).

    SPEC.md section 7 lists ``/measurements`` and SPEC.md section 3 makes a
    Measurement aggregate "metric definition, window, baseline, observation,
    source"; the surface must read and write the same durable registry the
    production view and optimization loop read. The dependency owns one adapter
    for the request and releases any connection it opened when the request ends;
    the store is chosen once from ``DATABASE_URL``, and a set-but-unusable
    configuration raises before the route runs, so a deployment cannot mistake a
    process-local registry for a durable one.
    """

    registry = measurement_registry_from_env(os.environ.get("DATABASE_URL"))
    try:
        yield registry
    finally:
        registry.close()


def get_campaign_message_repository() -> Iterator[CampaignMessageRepository]:
    """Provide the approved message seam to the API (SPEC.md section 6).

    SPEC.md section 3 pins exact approved asset versions and intended use at a
    passing gate, and SPEC.md section 4 keeps the approved version identifiable,
    so the stage 7 to 10 gates must resolve the stage 6 message a prior gate
    approved rather than trust a repeated request body. The dependency owns one
    adapter for the request and releases any connection it opened when the request
    ends, so the resolved message is read from the durable store and shared across
    the API and worker processes. The store is chosen once from ``DATABASE_URL``; a
    request cannot silently downgrade to a process-local message store, because a
    set-but-unusable configuration raises before the route runs.
    """

    repository = campaign_message_repository_from_env(
        os.environ.get("DATABASE_URL")
    )
    try:
        yield repository
    finally:
        repository.close()


def get_authority_amplifier_repository() -> Iterator[
    AuthorityAmplifierRepository
]:
    """Provide the approved amplifier seam to the API (SPEC.md section 6).

    SPEC.md section 3 pins exact approved asset versions and intended use at a
    passing gate, and SPEC.md section 4 keeps the approved version identifiable,
    so the stage 8 to 10 gates must resolve the stage 7 amplifier a prior gate
    approved rather than trust a repeated request body. The dependency owns one
    adapter for the request and releases any connection it opened when the request
    ends, so the resolved amplifier is read from the durable store and shared
    across the API and worker processes. The store is chosen once from
    ``DATABASE_URL``; a request cannot silently downgrade to a process-local
    amplifier store, because a set-but-unusable configuration raises before the
    route runs.
    """

    repository = authority_amplifier_repository_from_env(
        os.environ.get("DATABASE_URL")
    )
    try:
        yield repository
    finally:
        repository.close()


def get_funnel_integration_repository() -> Iterator[
    FunnelIntegrationRepository
]:
    """Provide the completed funnel seam to the API (SPEC.md section 6).

    SPEC.md section 3 pins exact approved asset versions and intended use at a
    passing gate, and SPEC.md section 4 keeps the approved version identifiable,
    so the stage 9 and 10 gates must resolve the stage 8 funnel a prior gate
    completed rather than trust a repeated request body. The dependency owns one
    adapter for the request and releases any connection it opened when the request
    ends, so the resolved funnel is read from the durable store and shared across
    the API and worker processes. The store is chosen once from ``DATABASE_URL``;
    a request cannot silently downgrade to a process-local funnel store, because a
    set-but-unusable configuration raises before the route runs.
    """

    repository = funnel_integration_repository_from_env(
        os.environ.get("DATABASE_URL")
    )
    try:
        yield repository
    finally:
        repository.close()


def get_launch_qa_repository() -> Iterator[LaunchQARepository]:
    """Provide the authorized launch QA seam to the API (SPEC.md section 6).

    SPEC.md section 3 pins exact approved asset versions and intended use at a
    passing gate, and SPEC.md section 4 keeps the approved version identifiable,
    so the stage 10 gate must resolve the stage 9 launch QA a prior gate
    authorized rather than trust a repeated request body. The dependency owns one
    adapter for the request and releases any connection it opened when the request
    ends, so the resolved QA is read from the durable store and shared across the
    API and worker processes. The store is chosen once from ``DATABASE_URL``; a
    request cannot silently downgrade to a process-local QA store, because a
    set-but-unusable configuration raises before the route runs.
    """

    repository = launch_qa_repository_from_env(
        os.environ.get("DATABASE_URL")
    )
    try:
        yield repository
    finally:
        repository.close()


def get_journey_release_repository() -> Iterator[JourneyReleaseRepository]:
    """Provide the authorized journey release seam to the API (SPEC.md section 6).

    SPEC.md section 3 names ``JourneyRelease`` as a core aggregate with the
    invariant "launch needs signed readiness and authorized release", and SPEC.md
    section 7 lists ``/journeys``. The dependency owns one adapter for the request
    and releases any connection it opened when the request ends, so an authorized
    release is read from and written to the durable store and shared across the
    API and worker processes. The store is chosen once from ``DATABASE_URL``; a
    request cannot silently downgrade to a process-local release store, because a
    set-but-unusable configuration raises before the route runs.
    """

    repository = journey_release_repository_from_env(
        os.environ.get("DATABASE_URL")
    )
    try:
        yield repository
    finally:
        repository.close()


def get_intervention_dismissal_repository() -> Iterator[
    InterventionDismissalRepository
]:
    """Provide the intervention dismissal seam to the API (SPEC.md section 6).

    SPEC.md section 7 exposes the command center's cards at ``/interventions`` and
    allows dismissal with rationale, and SPEC.md section 9 keeps an operator
    decision from being lost. The derived cards are recomputed on every read, so
    only the dismissal is durable; the dependency owns one adapter for the request
    and releases any connection it opened when the request ends. The store is
    chosen once from ``DATABASE_URL``; a request cannot silently downgrade to a
    process-local dismissal store, because a set-but-unusable configuration raises
    before the route runs.
    """

    repository = intervention_dismissal_repository_from_env(
        os.environ.get("DATABASE_URL")
    )
    try:
        yield repository
    finally:
        repository.close()


def _approve_method_offer_message(
    tenant_id: str,
    *,
    method_body: MethodVersionInput,
    offer_body: OfferVersionInput,
    message_body: CampaignMessageInput,
    method_repository: MethodVersionRepository,
    offer_repository: OfferVersionRepository,
    message_repository: CampaignMessageRepository,
) -> tuple[MethodVersion, MethodReference, OfferVersion, CampaignMessage]:
    """Rebuild the approved method, production ready offer and approved message.

    SPEC.md section 3: production requires approved dependencies, and the stage 6
    and stage 7 gates both ground on the locked stage 4 Signature Solution, the
    approved method and the production ready stage 5 offer (stage 7 additionally
    grounds on the approved stage 6 message, and stages 8 to 10 ground on all of
    them). The approved method, the production ready offer and the approved message
    are resolved from their stores by their exact identity rather than trusted from
    the repeated request body: the first gate stores the approved candidate, a
    later gate reuses the stored version, and a same-identity but different body is
    refused (``MethodVersionConflictError``, ``OfferVersionConflictError`` or
    ``CampaignMessageVersionConflictError``). The caller still supplies the message
    content, whose congruence with the resolved method and offer the domain
    re-proves rather than the transport layer asserting it. Sharing this builder
    keeps the stage 6 to 10 routes from drifting in how they resolve those upstream
    dependencies.
    """

    solution = SignatureSolution(
        solution_id=offer_body.delivery.signature_solution.solution_id,
        tenant_id=tenant_id,
        transformation_map=(
            offer_body.delivery.signature_solution.transformation_map
        ),
        process_inventory=tuple(
            offer_body.delivery.signature_solution.process_inventory
        ),
        phases=tuple(
            TransformationPhase(
                phase_id=phase.phase_id,
                tenant_id=tenant_id,
                name=phase.name,
                steps=tuple(
                    SignatureStep(
                        step_id=step.step_id,
                        tenant_id=tenant_id,
                        name=step.name,
                        starting_state=step.starting_state,
                        final_state=step.final_state,
                        inputs=tuple(step.inputs),
                        actions=tuple(step.actions),
                        outputs=tuple(step.outputs),
                    )
                    for step in phase.steps
                ),
            )
            for phase in offer_body.delivery.signature_solution.phases
        ),
        starting_state=offer_body.delivery.signature_solution.starting_state,
        final_state=offer_body.delivery.signature_solution.final_state,
        narrative=offer_body.delivery.signature_solution.narrative,
        visual=offer_body.delivery.signature_solution.visual,
    )
    semantic_version = SemanticVersion(
        major=method_body.semantic_version.major,
        minor=method_body.semantic_version.minor,
        patch=method_body.semantic_version.patch,
    )
    candidate = MethodVersion(
        method_id=method_body.method_id,
        tenant_id=tenant_id,
        parent_method=method_body.parent_method,
        semantic_version=semantic_version,
        stages=tuple(method_body.stages),
        currency=method_body.currency,
        claims=frozenset(method_body.claims),
        primary_currency=PrimaryCurrency(
            tenant_id=tenant_id,
            currency=method_body.primary_currency.currency,
            audience=method_body.primary_currency.audience,
            current_measure=method_body.primary_currency.current_measure,
            desired_measure=method_body.primary_currency.desired_measure,
            mechanism=method_body.primary_currency.mechanism,
        ),
        diagnostic_model=DiagnosticModel(
            model_id=method_body.diagnostic_model.model_id,
            tenant_id=tenant_id,
            name=method_body.diagnostic_model.name,
            levels=tuple(
                ProfitPyramidLevel(
                    level_id=level.level_id,
                    tenant_id=tenant_id,
                    name=level.name,
                    observable_measures=tuple(level.observable_measures),
                    symptoms=tuple(level.symptoms),
                    behaviors=tuple(level.behaviors),
                    problems=tuple(level.problems),
                )
                for level in method_body.diagnostic_model.levels
            ),
            progression=method_body.diagnostic_model.progression,
            qualification_logic=method_body.diagnostic_model.qualification_logic,
            visual=method_body.diagnostic_model.visual,
            explanatory_copy=method_body.diagnostic_model.explanatory_copy,
        ),
        signature_solution=solution,
    ).approve(
        approved_by=method_body.approved_by,
        intended_use=method_body.intended_use,
        on=method_body.approved_on,
    )
    stored = method_repository.get(
        tenant_id, method_body.method_id, semantic_version
    )
    if stored is None:
        method_repository.save(candidate)
        method = candidate
    elif stored == candidate:
        method = stored
    else:
        raise MethodVersionConflictError(
            f"approved method {method_body.method_id!r} at version "
            f"{semantic_version} was previously pinned for tenant "
            f"{tenant_id!r} with different content; the stage gate must reuse "
            "the exact approved method, not re-state it"
        )
    method_reference = MethodReference(
        method_id=method_body.method_id,
        version=semantic_version,
        intended_use=method_body.intended_use,
    )
    delivery = DeliverySpecification(
        delivery_id=offer_body.delivery.delivery_id,
        tenant_id=tenant_id,
        signature_solution=solution,
        delivery_model=offer_body.delivery.delivery_model,
        duration=offer_body.delivery.duration,
        modules=tuple(offer_body.delivery.modules),
        responsibilities=tuple(offer_body.delivery.responsibilities),
        support_cadence=offer_body.delivery.support_cadence,
        step_deliveries=tuple(
            StepDelivery(
                step_id=row.step_id,
                tenant_id=tenant_id,
                action=row.action,
                actor=row.actor,
                deliverable=row.deliverable,
                timing=row.timing,
                measure=row.measure,
            )
            for row in offer_body.delivery.step_deliveries
        ),
        outcome_measures=tuple(offer_body.delivery.outcome_measures),
        pricing_payments=offer_body.delivery.pricing_payments,
        scope=offer_body.delivery.scope,
        guarantee_decision=offer_body.delivery.guarantee_decision,
        eligibility=offer_body.delivery.eligibility,
        offer_stack=tuple(offer_body.delivery.offer_stack),
    )
    candidate_offer = OfferVersion(
        offer_id=offer_body.offer_id,
        tenant_id=tenant_id,
        audience=offer_body.audience,
        promise=offer_body.promise,
        eligibility=offer_body.eligibility,
        price_hypothesis=offer_body.price_hypothesis,
        method_refs=(method_reference,),
        owner=offer_body.owner,
        delivery_specification=delivery,
    ).require_production_ready((method,))
    stored_offer = offer_repository.get(tenant_id, offer_body.offer_id)
    if stored_offer is None:
        offer_repository.save(candidate_offer)
        offer = candidate_offer
    elif stored_offer == candidate_offer:
        offer = stored_offer
    else:
        raise OfferVersionConflictError(
            f"production ready offer {offer_body.offer_id!r} was previously "
            f"pinned for tenant {tenant_id!r} with different content; the stage "
            "gate must reuse the exact stage 5 offer, not re-state it"
        )
    message = CampaignMessage(
        message_id=message_body.message_id,
        tenant_id=tenant_id,
        offer=offer,
        owner=message_body.owner,
        avatar=message_body.avatar,
        currency=message_body.currency,
        problem=message_body.problem,
        promise=message_body.promise,
        cta=message_body.cta,
        method_reference=method_reference,
        product_offer_id=message_body.product_offer_id,
        problem_hierarchy=tuple(message_body.problem_hierarchy),
        desired_outcome=message_body.desired_outcome,
        proof_objections=tuple(message_body.proof_objections),
        story=message_body.story,
        method_explanation=message_body.method_explanation,
        lead_magnet=message_body.lead_magnet,
        hook=message_body.hook,
        angles=tuple(message_body.angles),
        landing_message=message_body.landing_message,
        authority_amplifier_outline=message_body.authority_amplifier_outline,
    ).approve((method,))
    stored_message = message_repository.get(tenant_id, message_body.message_id)
    if stored_message is None:
        message_repository.save(message)
    elif stored_message == message:
        message = stored_message
    else:
        raise CampaignMessageVersionConflictError(
            f"approved campaign message {message_body.message_id!r} was "
            f"previously pinned for tenant {tenant_id!r} with different content; "
            "the stage gate must reuse the exact stage 6 message, not re-state it"
        )
    return method, method_reference, offer, message


def _approve_authority_amplifier(
    tenant_id: str,
    *,
    method: MethodVersion,
    message: CampaignMessage,
    amplifier_body: AuthorityAmplifierInput,
    claims_body: list[ClaimInput],
    amplifier_repository: AuthorityAmplifierRepository,
) -> AuthorityAmplifier:
    """Rebuild the approved stage 7 Authority Amplifier.

    SPEC.md section 3: production requires approved dependencies, and the stage 8
    funnel grounds on the stage 7 amplifier that received creative acceptance. The
    reviewed amplifier is resolved from its store by exact identity rather than
    trusted from the repeated request body: the stage 7 gate stores the approved
    candidate, a later gate reuses the stored amplifier, and a same-identity but
    different body is refused (``AuthorityAmplifierVersionConflictError``). The
    caller still supplies the amplifier content, whose congruence with the
    resolved stage 6 message and approved method the domain re-proves rather than
    the transport layer asserting it -- the canonical script order, the grounded
    proof (every proof claim must be a claim of the approved method backed by a
    known, directly sourced knowledge claim) and the
    script-before-visuals-before-creative sequence. Sharing this builder keeps the
    stage 7 to 10 routes from drifting in how they resolve that upstream
    dependency.
    """

    script = tuple(
        ScriptSection(
            kind=ScriptSectionKind(entry.kind),
            content=entry.content,
        )
        for entry in amplifier_body.script
    )
    visuals = VisualProductionPackage(
        storyboard=amplifier_body.visuals.storyboard,
        brand_treatment=amplifier_body.visuals.brand_treatment,
        presentation=amplifier_body.visuals.presentation,
        speaker_notes=amplifier_body.visuals.speaker_notes,
        recording=amplifier_body.visuals.recording,
        edited_video=amplifier_body.visuals.edited_video,
        hosted_video=amplifier_body.visuals.hosted_video,
        player_assets=amplifier_body.visuals.player_assets,
    )
    claims = tuple(
        Claim(
            claim_id=entry.claim_id,
            tenant_id=tenant_id,
            statement=entry.statement,
            provenance=ProvenanceClass(entry.provenance),
            citations=frozenset(
                SourceCitation(
                    citation.source_id,
                    citation.checksum,
                    citation.location,
                )
                for citation in entry.citations
            ),
            confidence_note=entry.confidence_note,
        )
        for entry in claims_body
    )
    candidate_amplifier = (
        AuthorityAmplifier(
            amplifier_id=amplifier_body.amplifier_id,
            tenant_id=tenant_id,
            message=message,
            owner=amplifier_body.owner,
            script=script,
            proof_claim_ids=frozenset(amplifier_body.proof_claim_ids),
        )
        .approve_script(
            approved_by=amplifier_body.script_approval.approved_by,
            intended_use=amplifier_body.script_approval.intended_use,
            on=amplifier_body.script_approval.approved_on,
            approved_methods=(method,),
            claims=claims,
        )
        .produce_visuals(package=visuals)
        .approve_creative(
            approved_by=amplifier_body.creative_approval.approved_by,
            intended_use=amplifier_body.creative_approval.intended_use,
            on=amplifier_body.creative_approval.approved_on,
        )
    )
    stored_amplifier = amplifier_repository.get(
        tenant_id, amplifier_body.amplifier_id
    )
    if stored_amplifier is None:
        amplifier_repository.save(candidate_amplifier)
        return candidate_amplifier
    if stored_amplifier == candidate_amplifier:
        return stored_amplifier
    raise AuthorityAmplifierVersionConflictError(
        f"approved authority amplifier {amplifier_body.amplifier_id!r} was "
        f"previously pinned for tenant {tenant_id!r} with different content; "
        "the stage gate must reuse the exact stage 7 amplifier, not re-state it"
    )


def _complete_stage_eight_funnel(
    tenant_id: str,
    funnel_body: FunnelIntegrationInput,
    amplifier: AuthorityAmplifier,
    funnel_repository: FunnelIntegrationRepository,
) -> FunnelIntegration:
    """Rebuild the stage 8 funnel and drive its "Funnel Complete" checkpoint.

    SPEC.md section 3: production requires approved dependencies, and the stage 9
    launch QA grounds on the completed stage 8 funnel (SPEC.md section 4). The
    reviewed funnel is resolved from its store by exact identity rather than
    trusted from the repeated request body: the stage 8 gate stores the completed
    candidate, a later gate reuses the stored funnel, and a same-identity but
    different body is refused (``FunnelVersionConflictError``). The caller still
    supplies the reviewed funnel assets and its prospect path dry run, and the
    domain re-proves the funnel completion -- every canonical handoff present
    exactly once and routed with a record and an owner -- rather than the transport
    layer asserting it. Sharing this builder keeps the stage 8 to 10 routes from
    drifting in how they resolve that upstream dependency.
    """

    assets = FunnelAssetPackage(
        campaign_architecture=funnel_body.assets.campaign_architecture,
        pages=funnel_body.assets.pages,
        forms=funnel_body.assets.forms,
        qualification=funnel_body.assets.qualification,
        booking=funnel_body.assets.booking,
        sequences=funnel_body.assets.sequences,
        crm=funnel_body.assets.crm,
        tags=funnel_body.assets.tags,
        automation=funnel_body.assets.automation,
        analytics=funnel_body.assets.analytics,
        tracking=funnel_body.assets.tracking,
        sales_handoff=funnel_body.assets.sales_handoff,
        sops=funnel_body.assets.sops,
    )
    dry_run = ProspectPathDryRun(
        dry_run_id=funnel_body.dry_run.dry_run_id,
        tenant_id=tenant_id,
        handoffs=tuple(
            HandoffRecord(
                kind=HandoffKind(entry.kind),
                outcome=HandoffOutcome(entry.outcome),
                tenant_id=tenant_id,
                record_id=entry.record_id,
                owner=entry.owner,
                detail=entry.detail,
            )
            for entry in funnel_body.dry_run.handoffs
        ),
    )
    candidate_funnel = FunnelIntegration(
        integration_id=funnel_body.integration_id,
        tenant_id=tenant_id,
        amplifier=amplifier,
        owner=funnel_body.owner,
        assets=assets,
    ).mark_funnel_complete(dry_run)
    stored_funnel = funnel_repository.get(
        tenant_id, funnel_body.integration_id
    )
    if stored_funnel is None:
        funnel_repository.save(candidate_funnel)
        return candidate_funnel
    if stored_funnel == candidate_funnel:
        return stored_funnel
    raise FunnelVersionConflictError(
        f"completed funnel integration {funnel_body.integration_id!r} was "
        f"previously pinned for tenant {tenant_id!r} with different content; "
        "the stage gate must reuse the exact stage 8 funnel, not re-state it"
    )


def _authorize_launch_qa(
    tenant_id: str,
    qa_body: LaunchQAInput,
    funnel: FunnelIntegration,
    qa_repository: LaunchQARepository,
) -> LaunchQA:
    """Rebuild the stage 9 launch QA and drive its traffic authorization.

    SPEC.md section 3: production requires approved dependencies, and the stage 10
    performance baseline is grounded on the stage 9 launch QA that authorized
    traffic (SPEC.md section 4). The reviewed QA is resolved from its store by
    exact identity rather than trusted from the repeated request body: the stage 9
    gate stores the authorized candidate, the stage 10 gate reuses the stored QA,
    and a same-identity but different body is refused
    (``LaunchQAVersionConflictError``). The caller still supplies the reviewed
    compliance package, the complete check set and the designated authorization,
    and the domain re-proves the critical path outcomes, the launch-blocking
    compliance assets and the traffic authorization -- rather than the transport
    layer asserting them. Sharing this builder keeps the stage 9 and stage 10
    routes from drifting in how they resolve that upstream dependency.
    """

    compliance = CompliancePackage(
        package_id=qa_body.compliance.package_id,
        tenant_id=tenant_id,
        target_markets=tuple(qa_body.compliance.target_markets),
        assets=tuple(
            ComplianceAsset(
                kind=ComplianceAssetKind(entry.kind),
                tenant_id=tenant_id,
                reference=entry.reference,
                version=entry.version,
            )
            for entry in qa_body.compliance.assets
        ),
        waivers=tuple(
            ComplianceWaiver(
                kind=ComplianceAssetKind(entry.kind),
                reason=entry.reason,
                risk_owner=entry.risk_owner,
                review_trigger=entry.review_trigger,
                expires_on=entry.expires_on,
            )
            for entry in qa_body.compliance.waivers
        ),
    )
    candidate_qa = LaunchQA(
        qa_id=qa_body.qa_id,
        tenant_id=tenant_id,
        funnel=funnel,
        owner=qa_body.owner,
        designated_authority=qa_body.designated_authority,
        checks=tuple(
            QACheck(
                kind=QACheckKind(entry.kind),
                outcome=QACheckOutcome(entry.outcome),
                evidence=entry.evidence,
                owner=entry.owner,
                detail=entry.detail,
            )
            for entry in qa_body.checks
        ),
        compliance=compliance,
    ).authorize_traffic(
        authorization=TrafficAuthorization(
            authorized_by=qa_body.authorization.authorized_by,
            intended_use=qa_body.authorization.intended_use,
            authorized_on=qa_body.authorization.authorized_on,
        )
    )
    stored_qa = qa_repository.get(tenant_id, qa_body.qa_id)
    if stored_qa is None:
        qa_repository.save(candidate_qa)
        return candidate_qa
    if stored_qa == candidate_qa:
        return stored_qa
    raise LaunchQAVersionConflictError(
        f"authorized launch QA {qa_body.qa_id!r} was previously pinned for "
        f"tenant {tenant_id!r} with different content; the stage gate must "
        "reuse the exact stage 9 launch QA, not re-state it"
    )


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe for the RED app."""

    return {"status": "ok"}


@router.get("/stages")
def stages() -> list[dict[str, Any]]:
    """Return the canonical stages 0-10 and their checkpoints.

    The template is data: it names roles, not people, and confers no authority.
    """

    template = stage_zero_to_ten_template()
    return [
        {
            "stage_number": stage.stage_number,
            "name": stage.name,
            "checkpoint": stage.checkpoint,
            "required_asset_kinds": sorted(stage.required_asset_kinds),
            "accountable_role": stage.accountable_role,
            "approver_role": stage.approver_role,
            "dependencies": sorted(stage.dependencies),
        }
        for stage in template.stages
    ]


@router.post("/clients/{tenant_id}/stages/0/gate", status_code=201)
def record_stage_zero_gate(
    tenant_id: str,
    body: RecordStageZeroGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
    workspace_store: ClientWorkspaceStore = Depends(get_client_workspace_store),
) -> dict[str, Any]:
    """Record the stage 0 "Production Ready" gate through the use case seam.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageZeroGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageZeroGateHandler`` and
    appends the resulting ``GateDecision``. The response reports the pinned
    decision (exact asset versions, reviewer, disposition) the gate authorized
    downstream use with. The stage 0 ``StageRun`` is loaded-or-created and
    upserted through the ``StageRunRepository`` port in the same operation, so
    the stage's assigned owner, status, entered/exited timestamps and transition
    log are durable alongside the decision, not synthesised per request.
    Every integrity rule -- canonical kinds, exact versions,
    owner/approver authority, sourced evidence and the tenant boundary -- is
    enforced by the domain; a rejection is a named 422 and never a partial write
    (SPEC.md sections 3, 4, 9 and 11). The path tenant, not the body, is the
    authoritative client scope for the ledger.

    SPEC.md sections 3 and 4 make the ClientWorkspace the tenant root that holds
    the authority registry a gate approves against. The workspace is resolved
    from the durable store by ``(tenant_id, workspace_id)`` rather than rebuilt
    from the request body, so the approver and owner are checked against the
    persisted registry and a caller cannot substitute its own; an unregistered
    workspace is a named 404, not a gate (SPEC.md section 11).
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = workspace_store.get(tenant_id, body.workspace_id)
        if workspace is None:
            raise ClientWorkspaceNotFoundError(
                f"workspace {body.workspace_id!r} is not registered for "
                f"{tenant_id!r}"
            )
        claims = tuple(
            Claim(
                claim_id=item.claim_id,
                tenant_id=tenant_id,
                statement=item.statement,
                provenance=ProvenanceClass(item.provenance),
                citations=frozenset(
                    SourceCitation(
                        source_id=citation.source_id,
                        checksum=citation.checksum,
                        location=citation.location,
                    )
                    for citation in item.citations
                ),
                confidence_note=item.confidence_note,
            )
            for item in body.claims
        )
        package = IntakePackage(
            package_id=body.intake_package_id,
            tenant_id=tenant_id,
            assets=tuple(
                IntakeAsset(
                    asset_id=asset.asset_id,
                    tenant_id=tenant_id,
                    kind=IntakeAssetKind(asset.kind),
                    version=asset.version,
                    owner=asset.owner,
                    summary=asset.summary,
                    evidence_claim_ids=tuple(asset.evidence_claim_ids),
                )
                for asset in body.assets
            ),
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 0, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=0,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 0 intake work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageZeroGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            claims=claims,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageZeroGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except ClientWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except (EngagementError, GovernanceError, KnowledgeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.post("/clients/{tenant_id}/stages/1/gate", status_code=201)
def record_stage_one_gate(
    tenant_id: str,
    body: RecordStageOneGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
    workspace_store: ClientWorkspaceStore = Depends(get_client_workspace_store),
) -> dict[str, Any]:
    """Record the stage 1 "Avatar Locked" gate through the use case seam.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageOneGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageOneGateHandler`` and appends
    the resulting ``GateDecision``. Stage 1 depends on stage 0, so governance
    refuses the decision unless the ledger already holds a passing stage 0
    decision (SPEC.md section 4). The stage 1 ``StageRun`` is loaded-or-created
    and upserted through the ``StageRunRepository`` port in the same operation,
    so its assigned owner, status and timestamps stay durable alongside the
    decision. Every integrity rule -- canonical kinds, exact versions,
    owner/approver authority, sourced evidence and the tenant boundary -- is
    enforced by the domain; a rejection is a named 422 and never a partial write.
    The path tenant, not the body, is the authoritative client scope.

    SPEC.md sections 3 and 4 make the ClientWorkspace the tenant root that holds
    the authority registry a gate approves against. The workspace is resolved
    from the durable store by ``(tenant_id, workspace_id)`` rather than rebuilt
    from the request body, so the approver and owner are checked against the
    persisted registry and a caller cannot substitute its own; an unregistered
    workspace is a named 404, not a gate (SPEC.md section 11).
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = workspace_store.get(tenant_id, body.workspace_id)
        if workspace is None:
            raise ClientWorkspaceNotFoundError(
                f"workspace {body.workspace_id!r} is not registered for "
                f"{tenant_id!r}"
            )
        claims = tuple(
            Claim(
                claim_id=item.claim_id,
                tenant_id=tenant_id,
                statement=item.statement,
                provenance=ProvenanceClass(item.provenance),
                citations=frozenset(
                    SourceCitation(
                        source_id=citation.source_id,
                        checksum=citation.checksum,
                        location=citation.location,
                    )
                    for citation in item.citations
                ),
                confidence_note=item.confidence_note,
            )
            for item in body.claims
        )
        awareness_map = MarketAwarenessMap(
            map_id=body.awareness_map.map_id,
            tenant_id=tenant_id,
            primary_level=MarketAwarenessLevel(body.awareness_map.primary_level),
            research_evidence=tuple(body.awareness_map.research_evidence),
            message_requirements=tuple(body.awareness_map.message_requirements),
            retarget_level=(
                MarketAwarenessLevel(body.awareness_map.retarget_level)
                if body.awareness_map.retarget_level is not None
                else None
            ),
        )
        package = DiagnosisPackage(
            package_id=body.diagnosis_package_id,
            tenant_id=tenant_id,
            avatar=AvatarProfile(
                avatar_id=body.avatar.avatar_id,
                tenant_id=tenant_id,
                name=body.avatar.name,
                demographics=body.avatar.demographics,
                psychographics=body.avatar.psychographics,
                pains=tuple(body.avatar.pains),
                goals=tuple(body.avatar.goals),
                consequences_of_inaction=tuple(
                    body.avatar.consequences_of_inaction
                ),
                awareness=body.avatar.awareness,
                customer_evidence_claim_ids=tuple(
                    body.avatar.customer_evidence_claim_ids
                ),
                voice_notes=tuple(body.avatar.voice_notes),
            ),
            avatar_version=body.avatar.version,
            business_snapshot=BusinessSnapshot(
                snapshot_id=body.business_snapshot.snapshot_id,
                tenant_id=tenant_id,
                business_model=body.business_snapshot.business_model,
                current_offers=tuple(body.business_snapshot.current_offers),
                lead_sources=tuple(body.business_snapshot.lead_sources),
                constraints=tuple(body.business_snapshot.constraints),
                narrative=body.business_snapshot.narrative,
                evidence_claim_ids=tuple(body.business_snapshot.evidence_claim_ids),
            ),
            business_snapshot_version=body.business_snapshot.version,
            offer_funnel_audit=OfferFunnelAudit(
                audit_id=body.offer_funnel_audit.audit_id,
                tenant_id=tenant_id,
                offer_findings=tuple(body.offer_funnel_audit.offer_findings),
                funnel_steps=tuple(body.offer_funnel_audit.funnel_steps),
                conversion_evidence=tuple(
                    body.offer_funnel_audit.conversion_evidence
                ),
                gaps=tuple(body.offer_funnel_audit.gaps),
                narrative=body.offer_funnel_audit.narrative,
                evidence_claim_ids=tuple(
                    body.offer_funnel_audit.evidence_claim_ids
                ),
            ),
            offer_funnel_audit_version=body.offer_funnel_audit.version,
            awareness_map=awareness_map,
            awareness_map_version=body.awareness_map.version,
            audience_reach_estimate=AudienceReachEstimate(
                estimate_id=body.audience_reach_estimate.estimate_id,
                tenant_id=tenant_id,
                owner=body.audience_reach_estimate.owner,
                platform=ResearchPlatform(body.audience_reach_estimate.platform),
                audience=AudienceDefinition(
                    location=body.audience_reach_estimate.audience.location,
                    age=body.audience_reach_estimate.audience.age,
                    gender=body.audience_reach_estimate.audience.gender,
                    interests=tuple(
                        InterestSignal(
                            kind=InterestKind(signal.kind),
                            value=signal.value,
                        )
                        for signal in body.audience_reach_estimate.audience.interests
                    ),
                ),
                estimated_reach=body.audience_reach_estimate.estimated_reach,
                source_note=body.audience_reach_estimate.source_note,
                captured_on=body.audience_reach_estimate.captured_on,
            ),
            audience_reach_estimate_version=body.audience_reach_estimate.version,
            target_market_match=TargetMarketMatchmaker(
                matchmaker_id=body.target_market_match.matchmaker_id,
                tenant_id=tenant_id,
                candidates=tuple(
                    TargetMarketCandidate(
                        market_id=candidate.market_id,
                        name=candidate.name,
                        passion=candidate.passion,
                        problem=candidate.problem,
                        profit=candidate.profit,
                        reachability=candidate.reachability,
                        pathway=candidate.pathway,
                    )
                    for candidate in body.target_market_match.candidates
                ),
                selected_market_id=body.target_market_match.selected_market_id,
                awareness_map=awareness_map,
            ),
            target_market_match_version=body.target_market_match.version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 1, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=1,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 1 diagnosis work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageOneGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            claims=claims,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageOneGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except ClientWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except (
        CommercialError,
        EngagementError,
        GovernanceError,
        KnowledgeError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


def _metric_reporting_payload(row: MetricReportingView) -> dict[str, Any]:
    movement = None
    if row.movement is not None:
        movement = {
            "improvement_id": row.movement.improvement_id,
            "before": row.movement.before,
            "after": row.movement.after,
            "measured_on": row.movement.measured_on.isoformat(),
        }
    return {
        "metric_id": row.metric_id,
        "tenant_id": row.tenant_id,
        "name": row.name,
        "funnel_step": row.funnel_step,
        "unit": row.unit,
        "direction": row.direction,
        "value": row.value,
        "window_start": row.window_start.isoformat(),
        "window_end": row.window_end.isoformat(),
        "sample_size": row.sample_size,
        "source": row.source,
        "recorded_on": row.recorded_on.isoformat(),
        "basis": row.basis.value,
        "movement": movement,
    }


def _stage_production_view_payload(stage: StageProductionView) -> dict[str, Any]:
    return {
        "stage_number": stage.stage_number,
        "name": stage.name,
        "checkpoint": stage.checkpoint,
        "status": stage.status.value,
        "required_asset_kinds": sorted(stage.required_asset_kinds),
        "approved_assets": sorted(
            (
                {"asset_id": asset.asset_id, "version": asset.version}
                for asset in stage.approved_assets
            ),
            key=lambda asset: (asset["asset_id"], asset["version"]),
        ),
        "missing_asset_kinds": sorted(stage.missing_asset_kinds),
        "accountable_role": stage.accountable_role,
        "approver_role": stage.approver_role,
        "dependencies": sorted(stage.dependencies),
        "blocking_dependencies": sorted(stage.blocking_dependencies),
        "assigned_owner": stage.assigned_owner,
        "recorded_approver": stage.recorded_approver,
        "due_on": stage.due_on.isoformat() if stage.due_on else None,
        "next_action": stage.next_action,
        "blockers": sorted(stage.blockers),
        "entered_at": stage.entered_at.isoformat() if stage.entered_at else None,
        "is_approved": stage.is_approved,
    }


def _production_view_payload(view: EngagementProductionView) -> dict[str, Any]:
    current = view.current_stage
    next_approval = view.next_approval
    return {
        "engagement": view.engagement,
        "tenant_id": view.tenant_id,
        "template_version": view.template_version,
        "current_stage_number": current.stage_number if current else None,
        "next_approval_stage_number": (
            next_approval.stage_number if next_approval else None
        ),
        "blocked_stage_numbers": [
            stage.stage_number for stage in view.blocked_stages
        ],
        "progress": {
            "approved_gates": view.progress.approved_gates,
            "total_gates": view.progress.total_gates,
            "verified_post_launch_milestones": (
                view.progress.verified_post_launch_milestones
            ),
            "activity_entries": view.progress.activity_entries,
            "verified_progress": view.progress.verified_progress,
            "gates_remaining": view.progress.gates_remaining,
        },
        "stages": [
            _stage_production_view_payload(stage) for stage in view.stages
        ],
        "metric_reporting": [
            _metric_reporting_payload(row) for row in view.metric_reporting
        ],
    }


@router.post("/clients/{tenant_id}/stages/2/gate", status_code=201)
def record_stage_two_gate(
    tenant_id: str,
    body: RecordStageTwoGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
    workspace_store: ClientWorkspaceStore = Depends(get_client_workspace_store),
) -> dict[str, Any]:
    """Record the stage 2 "Currency Locked" gate through the use case seam.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageTwoGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageTwoGateHandler`` and appends
    the resulting ``GateDecision``. Stage 2 depends on stage 1, so governance
    refuses the decision unless the ledger already holds a passing stage 1
    decision (SPEC.md section 4). The stage 2 ``StageRun`` is loaded-or-created
    and upserted through the ``StageRunRepository`` port in the same operation,
    so its assigned owner, status and timestamps stay durable alongside the
    decision. Every integrity rule -- canonical kinds, exact versions,
    owner/approver authority, the primary currency's internal specificity and
    the tenant boundary -- is enforced by the domain; a rejection is a named 422
    and never a partial write. The path tenant, not the body, is the
    authoritative client scope. Stage 2 carries no claims: the checkpoint turns
    on the locked currency, not on external customer evidence.

    SPEC.md sections 3 and 4 make the ClientWorkspace the tenant root that holds
    the authority registry a gate approves against. The workspace is resolved
    from the durable store by ``(tenant_id, workspace_id)`` rather than rebuilt
    from the request body, so the approver and owner are checked against the
    persisted registry and a caller cannot substitute its own; an unregistered
    workspace is a named 404, not a gate (SPEC.md section 11).
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = workspace_store.get(tenant_id, body.workspace_id)
        if workspace is None:
            raise ClientWorkspaceNotFoundError(
                f"workspace {body.workspace_id!r} is not registered for "
                f"{tenant_id!r}"
            )
        package = CurrencyPackage(
            package_id=body.currency_package_id,
            tenant_id=tenant_id,
            inventory=CurrencyInventory(
                inventory_id=body.inventory.inventory_id,
                tenant_id=tenant_id,
                category=body.inventory.category,
                currencies_to_increase=tuple(
                    body.inventory.currencies_to_increase
                ),
                currencies_to_decrease=tuple(
                    body.inventory.currencies_to_decrease
                ),
            ),
            inventory_version=body.inventory.version,
            positioning=PositioningDecision(
                decision_id=body.positioning.decision_id,
                tenant_id=tenant_id,
                core_problem=body.positioning.core_problem,
                transformation_statement=(
                    body.positioning.transformation_statement
                ),
                horizon=body.positioning.horizon,
                qualifications=tuple(body.positioning.qualifications),
                disqualifications=tuple(body.positioning.disqualifications),
            ),
            positioning_version=body.positioning.version,
            primary_currency=PrimaryCurrency(
                tenant_id=tenant_id,
                currency=body.primary_currency.currency,
                audience=body.primary_currency.audience,
                current_measure=body.primary_currency.current_measure,
                desired_measure=body.primary_currency.desired_measure,
                mechanism=body.primary_currency.mechanism,
            ),
            primary_currency_version=body.primary_currency.version,
            million_dollar_message=MillionDollarMessage(
                message_id=body.million_dollar_message.message_id,
                tenant_id=tenant_id,
                avatar=body.million_dollar_message.avatar,
                currency=body.million_dollar_message.currency,
                metric=body.million_dollar_message.metric,
                timeline=body.million_dollar_message.timeline,
                pain=body.million_dollar_message.pain,
                message=body.million_dollar_message.message,
            ),
            million_dollar_message_version=body.million_dollar_message.version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 2, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=2,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 2 positioning work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageTwoGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageTwoGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except ClientWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except (
        CommercialError,
        EngagementError,
        GovernanceError,
        MethodError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.post("/clients/{tenant_id}/stages/3/gate", status_code=201)
def record_stage_three_gate(
    tenant_id: str,
    body: RecordStageThreeGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
    workspace_store: ClientWorkspaceStore = Depends(get_client_workspace_store),
) -> dict[str, Any]:
    """Record the stage 3 "Diagnostic Model Approved" gate through the use case.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageThreeGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageThreeGateHandler`` and
    appends the resulting ``GateDecision``. Stage 3 depends on stage 2, so
    governance refuses the decision unless the ledger already holds a passing
    stage 2 decision (SPEC.md section 4). The stage 3 ``StageRun`` is
    loaded-or-created and upserted through the ``StageRunRepository`` port in the
    same operation, so its assigned owner, status and timestamps stay durable
    alongside the decision. Every integrity rule -- canonical kinds, exact
    versions, owner/approver authority, adjacent-level observable
    distinguishability and the tenant boundary -- is enforced by the domain; a
    rejection is a named 422 and never a partial write. The path tenant, not the
    body, is the authoritative client scope. Stage 3 carries no claims: the
    checkpoint turns on the model's own observable differences, not external
    customer evidence.

    SPEC.md sections 3 and 4 make the ClientWorkspace the tenant root that holds
    the authority registry a gate approves against. The workspace is resolved
    from the durable store by ``(tenant_id, workspace_id)`` rather than rebuilt
    from the request body, so the approver and owner are checked against the
    persisted registry and a caller cannot substitute its own; an unregistered
    workspace is a named 404, not a gate (SPEC.md section 11).
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = workspace_store.get(tenant_id, body.workspace_id)
        if workspace is None:
            raise ClientWorkspaceNotFoundError(
                f"workspace {body.workspace_id!r} is not registered for "
                f"{tenant_id!r}"
            )
        package = DiagnosticPackage(
            package_id=body.diagnostic_package_id,
            tenant_id=tenant_id,
            model=DiagnosticModel(
                model_id=body.model.model_id,
                tenant_id=tenant_id,
                name=body.model.name,
                levels=tuple(
                    ProfitPyramidLevel(
                        level_id=level.level_id,
                        tenant_id=tenant_id,
                        name=level.name,
                        observable_measures=tuple(level.observable_measures),
                        symptoms=tuple(level.symptoms),
                        behaviors=tuple(level.behaviors),
                        problems=tuple(level.problems),
                    )
                    for level in body.model.levels
                ),
                progression=body.model.progression,
                qualification_logic=body.model.qualification_logic,
                visual=body.model.visual,
                explanatory_copy=body.model.explanatory_copy,
            ),
            model_version=body.model.version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 3, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=3,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 3 diagnostic modeling work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageThreeGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageThreeGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except ClientWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except (
        CommercialError,
        EngagementError,
        GovernanceError,
        MethodError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.post("/clients/{tenant_id}/stages/4/gate", status_code=201)
def record_stage_four_gate(
    tenant_id: str,
    body: RecordStageFourGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
    workspace_store: ClientWorkspaceStore = Depends(get_client_workspace_store),
) -> dict[str, Any]:
    """Record the stage 4 "IP Architecture Locked" gate through the use case.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageFourGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageFourGateHandler`` and
    appends the resulting ``GateDecision``. Stage 4 depends on stage 3, so
    governance refuses the decision unless the ledger already holds a passing
    stage 3 decision (SPEC.md section 4). The stage 4 ``StageRun`` is
    loaded-or-created and upserted through the ``StageRunRepository`` port in the
    same operation, so its assigned owner, status and timestamps stay durable
    alongside the decision. Every integrity rule -- canonical kinds, exact
    versions, owner/approver authority, the three phase/nine step shape, the
    continuity of the named stages from the declared starting to final state and
    the tenant boundary -- is enforced by the domain; a rejection is a named 422
    and never a partial write. The path tenant, not the body, is the authoritative
    client scope. Stage 4 carries no claims: the checkpoint turns on the coherence
    and continuity of the reviewed transformation, not external customer evidence.

    SPEC.md sections 3 and 4 make the ClientWorkspace the tenant root that holds
    the authority registry a gate approves against. The workspace is resolved
    from the durable store by ``(tenant_id, workspace_id)`` rather than rebuilt
    from the request body, so the approver and owner are checked against the
    persisted registry and a caller cannot substitute its own; an unregistered
    workspace is a named 404, not a gate (SPEC.md section 11).
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = workspace_store.get(tenant_id, body.workspace_id)
        if workspace is None:
            raise ClientWorkspaceNotFoundError(
                f"workspace {body.workspace_id!r} is not registered for "
                f"{tenant_id!r}"
            )
        solution = SignatureSolution(
            solution_id=body.solution.solution_id,
            tenant_id=tenant_id,
            transformation_map=body.solution.transformation_map,
            process_inventory=tuple(body.solution.process_inventory),
            phases=tuple(
                TransformationPhase(
                    phase_id=phase.phase_id,
                    tenant_id=tenant_id,
                    name=phase.name,
                    steps=tuple(
                        SignatureStep(
                            step_id=step.step_id,
                            tenant_id=tenant_id,
                            name=step.name,
                            starting_state=step.starting_state,
                            final_state=step.final_state,
                            inputs=tuple(step.inputs),
                            actions=tuple(step.actions),
                            outputs=tuple(step.outputs),
                        )
                        for step in phase.steps
                    ),
                )
                for phase in body.solution.phases
            ),
            starting_state=body.solution.starting_state,
            final_state=body.solution.final_state,
            narrative=body.solution.narrative,
            visual=body.solution.visual,
        )
        transformations = ThirteenTransformations(
            transformations_id=body.transformations.transformations_id,
            tenant_id=tenant_id,
            million_dollar_message=body.transformations.million_dollar_message,
            solution=solution,
            overall=Transformation(
                transformation_id=(
                    f"{body.transformations.transformations_id}-overall"
                ),
                tenant_id=tenant_id,
                scope=TransformationScope.OVERALL,
                scope_id=solution.solution_id,
                title=body.transformations.million_dollar_message,
                from_state=solution.starting_state,
                to_state=solution.final_state,
            ),
            phase_transformations=tuple(
                Transformation(
                    transformation_id=(
                        f"{body.transformations.transformations_id}-"
                        f"{phase.phase_id}"
                    ),
                    tenant_id=tenant_id,
                    scope=TransformationScope.PHASE,
                    scope_id=phase.phase_id,
                    title=phase.name,
                    from_state=phase.steps[0].starting_state,
                    to_state=phase.steps[-1].final_state,
                )
                for phase in solution.phases
            ),
            step_transformations=tuple(
                Transformation(
                    transformation_id=(
                        f"{body.transformations.transformations_id}-"
                        f"{step.step_id}"
                    ),
                    tenant_id=tenant_id,
                    scope=TransformationScope.STEP,
                    scope_id=step.step_id,
                    title=step.name,
                    from_state=step.starting_state,
                    to_state=step.final_state,
                )
                for step in solution.steps
            ),
        )
        package = SignaturePackage(
            package_id=body.signature_package_id,
            tenant_id=tenant_id,
            solution=solution,
            solution_version=body.solution.version,
            transformations=transformations,
            transformations_version=body.transformations.version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 4, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=4,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 4 IP packaging work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageFourGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageFourGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except ClientWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except (
        CommercialError,
        EngagementError,
        GovernanceError,
        MethodError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.post("/clients/{tenant_id}/stages/5/gate", status_code=201)
def record_stage_five_gate(
    tenant_id: str,
    body: RecordStageFiveGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
    workspace_store: ClientWorkspaceStore = Depends(get_client_workspace_store),
) -> dict[str, Any]:
    """Record the stage 5 "Offer Locked" gate through the use case.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageFiveGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageFiveGateHandler`` and
    appends the resulting ``GateDecision``. Stage 5 depends on stage 4, so
    governance refuses the decision unless the ledger already holds a passing
    stage 4 decision (SPEC.md section 4). The stage 5 ``StageRun`` is
    loaded-or-created and upserted through the ``StageRunRepository`` port in the
    same operation, so its assigned owner, status and timestamps stay durable
    alongside the decision. Every integrity rule -- canonical kinds, exact
    versions, owner/approver authority, the delivery model grounded on the locked
    stage 4 method, one delivery per named method step with an action, actor,
    deliverable, timing and measure, the typed product program (canon files 11 and
    12) and the tenant boundary -- is enforced by the domain; a rejection is a
    named 422 and never a partial write. The path tenant, not the body, is the
    authoritative client scope. Stage 5 carries no claims:
    the checkpoint turns on the delivered offer's completeness against the locked
    method, not external customer evidence.

    SPEC.md sections 3 and 4 make the ClientWorkspace the tenant root that holds
    the authority registry a gate approves against. The workspace is resolved
    from the durable store by ``(tenant_id, workspace_id)`` rather than rebuilt
    from the request body, so the approver and owner are checked against the
    persisted registry and a caller cannot substitute its own; an unregistered
    workspace is a named 404, not a gate (SPEC.md section 11).
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = workspace_store.get(tenant_id, body.workspace_id)
        if workspace is None:
            raise ClientWorkspaceNotFoundError(
                f"workspace {body.workspace_id!r} is not registered for "
                f"{tenant_id!r}"
            )
        solution = SignatureSolution(
            solution_id=body.delivery.signature_solution.solution_id,
            tenant_id=tenant_id,
            transformation_map=(
                body.delivery.signature_solution.transformation_map
            ),
            process_inventory=tuple(
                body.delivery.signature_solution.process_inventory
            ),
            phases=tuple(
                TransformationPhase(
                    phase_id=phase.phase_id,
                    tenant_id=tenant_id,
                    name=phase.name,
                    steps=tuple(
                        SignatureStep(
                            step_id=step.step_id,
                            tenant_id=tenant_id,
                            name=step.name,
                            starting_state=step.starting_state,
                            final_state=step.final_state,
                            inputs=tuple(step.inputs),
                            actions=tuple(step.actions),
                            outputs=tuple(step.outputs),
                        )
                        for step in phase.steps
                    ),
                )
                for phase in body.delivery.signature_solution.phases
            ),
            starting_state=body.delivery.signature_solution.starting_state,
            final_state=body.delivery.signature_solution.final_state,
            narrative=body.delivery.signature_solution.narrative,
            visual=body.delivery.signature_solution.visual,
        )
        package = OfferPackage(
            package_id=body.offer_package_id,
            tenant_id=tenant_id,
            delivery=DeliverySpecification(
                delivery_id=body.delivery.delivery_id,
                tenant_id=tenant_id,
                signature_solution=solution,
                delivery_model=body.delivery.delivery_model,
                duration=body.delivery.duration,
                modules=tuple(body.delivery.modules),
                responsibilities=tuple(body.delivery.responsibilities),
                support_cadence=body.delivery.support_cadence,
                step_deliveries=tuple(
                    StepDelivery(
                        step_id=row.step_id,
                        tenant_id=tenant_id,
                        action=row.action,
                        actor=row.actor,
                        deliverable=row.deliverable,
                        timing=row.timing,
                        measure=row.measure,
                    )
                    for row in body.delivery.step_deliveries
                ),
                outcome_measures=tuple(body.delivery.outcome_measures),
                pricing_payments=body.delivery.pricing_payments,
                scope=body.delivery.scope,
                guarantee_decision=body.delivery.guarantee_decision,
                eligibility=body.delivery.eligibility,
                offer_stack=tuple(body.delivery.offer_stack),
            ),
            delivery_version=body.delivery.version,
            product_program=ProductProgram(
                program_id=body.product_program.program_id,
                tenant_id=tenant_id,
                owner=body.product_program.owner,
                method=solution,
                model=ProductMatrixModel(body.product_program.model),
                pricing_basis=ProgramPricingBasis(
                    body.product_program.pricing_basis
                ),
                duration_weeks=body.product_program.duration_weeks,
                cadence=ProgramCadence(body.product_program.cadence),
                modules=tuple(
                    ProductModule(
                        module_id=module.module_id,
                        tenant_id=tenant_id,
                        signature_step=module.signature_step,
                        position=module.position,
                        outcome=module.outcome,
                        deliverable=module.deliverable,
                    )
                    for module in body.product_program.modules
                ),
            ),
            product_program_version=body.product_program.version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 5, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=5,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 5 productization work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageFiveGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageFiveGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except ClientWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except (
        CommercialError,
        EngagementError,
        GovernanceError,
        MethodError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.post("/clients/{tenant_id}/stages/6/gate", status_code=201)
def record_stage_six_gate(
    tenant_id: str,
    body: RecordStageSixGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
    method_repository: MethodVersionRepository = Depends(
        get_method_version_repository
    ),
    offer_repository: OfferVersionRepository = Depends(
        get_offer_version_repository
    ),
    campaign_message_repository: CampaignMessageRepository = Depends(
        get_campaign_message_repository
    ),
    workspace_store: ClientWorkspaceStore = Depends(
        get_client_workspace_store
    ),
) -> dict[str, Any]:
    """Record the stage 6 "Campaign Message Approved" gate through the use case.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageSixGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageSixGateHandler`` and appends
    the resulting ``GateDecision``. Stage 6 depends on stage 5, so governance
    refuses the decision unless the ledger already holds a passing stage 5
    decision (SPEC.md section 4). The stage 6 ``StageRun`` is loaded-or-created
    and upserted through the ``StageRunRepository`` port in the same operation, so
    its assigned owner, status and timestamps stay durable alongside the decision.

    The route resolves the approved method, the production ready stage 5 offer and
    the approved stage 6 message from their stores by their exact identity instead
    of trusting the repeated request body: the first gate stores the approved
    candidate, a later gate reuses the stored version, and a same-identity but
    different body is refused. The reviewed message is approved against the
    resolved method and offer so the "Campaign Message Approved" congruence
    (avatar, currency, problem, promise, method, product and CTA agree) is proven
    by the domain, not asserted. Every
    integrity rule -- canonical kinds, exact versions, owner/approver authority,
    the message-method-offer congruence and the tenant boundary -- is enforced by
    the domain; a rejection is a named 422 and never a partial write. The path
    tenant, not the body, is the authoritative client scope. Stage 6 carries no
    claims: the checkpoint turns on the message's congruence with the approved
    method and offer, not external customer evidence.

    SPEC.md sections 3 and 4 make the ClientWorkspace the tenant root that holds
    the authority registry a gate approves against. The workspace is resolved
    from the durable store by ``(tenant_id, workspace_id)`` rather than rebuilt
    from the request body, so the approver and owner are checked against the
    persisted registry and a caller cannot substitute its own; an unregistered
    workspace is a named 404, not a gate (SPEC.md section 11).
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = workspace_store.get(tenant_id, body.workspace_id)
        if workspace is None:
            raise ClientWorkspaceNotFoundError(
                f"workspace {body.workspace_id!r} is not registered for "
                f"{tenant_id!r}"
            )
        method, method_reference, offer, message = _approve_method_offer_message(
            tenant_id,
            method_body=body.method,
            offer_body=body.offer,
            message_body=body.message,
            method_repository=method_repository,
            offer_repository=offer_repository,
            message_repository=campaign_message_repository,
        )
        roadmap = ContentRoadmap(
            roadmap_id=body.content_roadmap.roadmap_id,
            tenant_id=tenant_id,
            owner=body.content_roadmap.owner,
            method=method.signature_solution,
            topics=tuple(
                ContentTopic(
                    topic_id=topic.topic_id,
                    tenant_id=tenant_id,
                    name=topic.name,
                    signature_step=topic.signature_step,
                    question=topic.question,
                    channels=tuple(
                        ContentChannel(channel) for channel in topic.channels
                    ),
                    script_beats=AUTHORITY_AMPLIFIER_BEATS,
                )
                for topic in body.content_roadmap.topics
            ),
        )
        currency = PrimaryCurrency(
            tenant_id=tenant_id,
            currency=body.content_plan.primary_currency.currency,
            audience=body.content_plan.primary_currency.audience,
            current_measure=body.content_plan.primary_currency.current_measure,
            desired_measure=body.content_plan.primary_currency.desired_measure,
            mechanism=body.content_plan.primary_currency.mechanism,
        )
        content_plan = ContentPlan(
            plan_id=body.content_plan.plan_id,
            tenant_id=tenant_id,
            owner=body.content_plan.owner,
            method=method.signature_solution,
            currency=currency,
            themes=tuple(
                ContentTheme(
                    theme_id=theme.theme_id,
                    tenant_id=tenant_id,
                    name=theme.name,
                    currency_measure=theme.currency_measure,
                )
                for theme in body.content_plan.themes
            ),
            ideas=tuple(
                ContentIdea(
                    idea_id=idea.idea_id,
                    tenant_id=tenant_id,
                    signature_step=idea.signature_step,
                    source=ContentIdeaSource(idea.source),
                    prompt=idea.prompt,
                    theme_id=idea.theme_id,
                    channels=tuple(
                        ContentPlanChannel(channel) for channel in idea.channels
                    ),
                )
                for idea in body.content_plan.ideas
            ),
        )
        package = CampaignMessagePackage(
            package_id=body.campaign_message_package_id,
            tenant_id=tenant_id,
            message=message,
            message_version=body.message_version,
            roadmap=roadmap,
            roadmap_version=body.content_roadmap.version,
            crusher=ContentCrusher(
                crusher_id=body.content_crusher.crusher_id,
                tenant_id=tenant_id,
                owner=body.content_crusher.owner,
                roadmap=roadmap,
                topic_id=body.content_crusher.topic_id,
                title=body.content_crusher.title,
                promise=ContentPromise(
                    measure=body.content_crusher.promise_measure,
                    timeline=body.content_crusher.promise_timeline,
                ),
                frustrations=tuple(body.content_crusher.frustrations),
                goal=body.content_crusher.goal,
                model=body.content_crusher.model,
                metaphor=body.content_crusher.metaphor,
                context=body.content_crusher.context,
                steps=tuple(body.content_crusher.steps),
                story=body.content_crusher.story,
                choice=body.content_crusher.choice,
                action=body.content_crusher.action,
            ),
            crusher_version=body.content_crusher.version,
            plan=content_plan,
            plan_version=body.content_plan.version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 6, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=6,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 6 campaign message work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageSixGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageSixGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except ClientWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except (
        CommercialError,
        EngagementError,
        GovernanceError,
        MethodError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.post("/clients/{tenant_id}/stages/7/gate", status_code=201)
def record_stage_seven_gate(
    tenant_id: str,
    body: RecordStageSevenGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
    method_repository: MethodVersionRepository = Depends(
        get_method_version_repository
    ),
    offer_repository: OfferVersionRepository = Depends(
        get_offer_version_repository
    ),
    campaign_message_repository: CampaignMessageRepository = Depends(
        get_campaign_message_repository
    ),
    authority_amplifier_repository: AuthorityAmplifierRepository = Depends(
        get_authority_amplifier_repository
    ),
    workspace_store: ClientWorkspaceStore = Depends(
        get_client_workspace_store
    ),
) -> dict[str, Any]:
    """Record the stage 7 "Authority Amplifier Approved" gate through the use case.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageSevenGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageSevenGateHandler`` and appends
    the resulting ``GateDecision``. Stage 7 depends on stage 6, so governance
    refuses the decision unless the ledger already holds a passing stage 6
    decision (SPEC.md section 4). The stage 7 ``StageRun`` is loaded-or-created and
    upserted through the ``StageRunRepository`` port in the same operation.

    Stage 7 has two distinct approvals (SPEC.md section 4, stage 7; canon files
    13-18 and 28 per SPEC.md section 12.3): the script and its supported claims
    pass review before visual or video production, then final creative acceptance.
    The route rebuilds the reviewed amplifier from the request and drives those
    approvals in order -- ``approve_script`` (which the ``AuthorityAmplifierPolicy``
    only permits when the message is approved, the method is an approved
    dependency and every proof claim is a known, directly sourced method claim),
    then ``produce_visuals``, then ``approve_creative`` -- so the canonical order is
    enforced by the domain, not asserted. The route resolves the approved method,
    production ready offer and approved stage 6 message from their stores by exact
    identity, and stores the approved stage 7 amplifier so the stage 8 to 10 gates
    resolve it rather than trust a repeated request; every integrity rule -- the canonical script order,
    grounded proof, the approval sequence, the canonical kinds, exact versions,
    owner/approver authority and the tenant boundary -- stays enforced by the
    domain, and a rejection is a named 422 and never a partial write. The path
    tenant, not the body, is the authoritative client scope.

    SPEC.md sections 3 and 4 make the ClientWorkspace the tenant root that holds
    the authority registry a gate approves against. The workspace is resolved
    from the durable store by ``(tenant_id, workspace_id)`` rather than rebuilt
    from the request body, so the approver and owner are checked against the
    persisted registry and a caller cannot substitute its own; an unregistered
    workspace is a named 404, not a gate (SPEC.md section 11).
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = workspace_store.get(tenant_id, body.workspace_id)
        if workspace is None:
            raise ClientWorkspaceNotFoundError(
                f"workspace {body.workspace_id!r} is not registered for "
                f"{tenant_id!r}"
            )
        method, _method_reference, _offer, message = _approve_method_offer_message(
            tenant_id,
            method_body=body.method,
            offer_body=body.offer,
            message_body=body.message,
            method_repository=method_repository,
            offer_repository=offer_repository,
            message_repository=campaign_message_repository,
        )
        amplifier = _approve_authority_amplifier(
            tenant_id,
            method=method,
            message=message,
            amplifier_body=body.amplifier,
            claims_body=body.claims,
            amplifier_repository=authority_amplifier_repository,
        )
        package = AuthorityAmplifierPackage(
            package_id=body.amplifier_package_id,
            tenant_id=tenant_id,
            amplifier=amplifier,
            amplifier_version=body.amplifier_version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 7, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=7,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 7 authority amplifier work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageSevenGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageSevenGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except ClientWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except (
        CommercialError,
        EngagementError,
        GovernanceError,
        MethodError,
        ProductionError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.post("/clients/{tenant_id}/stages/8/gate", status_code=201)
def record_stage_eight_gate(
    tenant_id: str,
    body: RecordStageEightGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
    method_repository: MethodVersionRepository = Depends(
        get_method_version_repository
    ),
    offer_repository: OfferVersionRepository = Depends(
        get_offer_version_repository
    ),
    campaign_message_repository: CampaignMessageRepository = Depends(
        get_campaign_message_repository
    ),
    authority_amplifier_repository: AuthorityAmplifierRepository = Depends(
        get_authority_amplifier_repository
    ),
    funnel_repository: FunnelIntegrationRepository = Depends(
        get_funnel_integration_repository
    ),
    workspace_store: ClientWorkspaceStore = Depends(
        get_client_workspace_store
    ),
) -> dict[str, Any]:
    """Record the stage 8 "Funnel Complete" gate through the use case.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageEightGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageEightGateHandler`` and appends
    the resulting ``GateDecision``. Stage 8 depends on stage 7, so governance
    refuses the decision unless the ledger already holds a passing stage 7
    decision (SPEC.md section 4). The stage 8 ``StageRun`` is loaded-or-created and
    upserted through the ``StageRunRepository`` port in the same operation.

    SPEC.md section 4, stage 8 "Integrate" and its "Funnel Complete" checkpoint:
    a test prospect completes capture, engagement and conversion handoffs with
    reliable records and ownership (canon files 13, 14, 21 and 22 per SPEC.md
    section 12.3). The route rebuilds the reviewed funnel, grounds it on the
    rebuilt approved stage 7 amplifier and drives ``mark_funnel_complete`` with the
    prospect path dry run, so the ``FunnelCompletionPolicy`` -- not the transport
    layer -- decides whether the thirteen canonical kinds may be pinned as passing
    evidence. The route resolves the approved method, production ready offer,
    approved stage 6 message and approved stage 7 amplifier from their stores by
    exact identity; every integrity rule -- the funnel's own completion, the
    grounded stage 7 dependency, the canonical kinds, exact versions,
    owner/approver authority and the tenant boundary -- stays enforced by the
    domain, and a rejection is a named 422 and never a partial write. The path
    tenant, not the body, is the authoritative client scope.

    SPEC.md sections 3 and 4 make the ClientWorkspace the tenant root that holds
    the authority registry a gate approves against. The workspace is resolved
    from the durable store by ``(tenant_id, workspace_id)`` rather than rebuilt
    from the request body, so the approver and owner are checked against the
    persisted registry and a caller cannot substitute its own; an unregistered
    workspace is a named 404, not a gate (SPEC.md section 11).
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = workspace_store.get(tenant_id, body.workspace_id)
        if workspace is None:
            raise ClientWorkspaceNotFoundError(
                f"workspace {body.workspace_id!r} is not registered for "
                f"{tenant_id!r}"
            )
        method, _method_reference, _offer, message = _approve_method_offer_message(
            tenant_id,
            method_body=body.method,
            offer_body=body.offer,
            message_body=body.message,
            method_repository=method_repository,
            offer_repository=offer_repository,
            message_repository=campaign_message_repository,
        )
        amplifier = _approve_authority_amplifier(
            tenant_id,
            method=method,
            message=message,
            amplifier_body=body.amplifier,
            claims_body=body.claims,
            amplifier_repository=authority_amplifier_repository,
        )
        funnel = _complete_stage_eight_funnel(
            tenant_id, body.funnel, amplifier, funnel_repository
        )
        package = FunnelIntegrationPackage(
            package_id=body.funnel_package_id,
            tenant_id=tenant_id,
            funnel=funnel,
            funnel_version=body.funnel_version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 8, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=8,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 8 funnel integration work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageEightGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageEightGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except ClientWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except (
        CommercialError,
        EngagementError,
        ExecutionError,
        GovernanceError,
        MethodError,
        ProductionError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.post("/clients/{tenant_id}/stages/9/gate", status_code=201)
def record_stage_nine_gate(
    tenant_id: str,
    body: RecordStageNineGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
    method_repository: MethodVersionRepository = Depends(
        get_method_version_repository
    ),
    offer_repository: OfferVersionRepository = Depends(
        get_offer_version_repository
    ),
    campaign_message_repository: CampaignMessageRepository = Depends(
        get_campaign_message_repository
    ),
    authority_amplifier_repository: AuthorityAmplifierRepository = Depends(
        get_authority_amplifier_repository
    ),
    funnel_repository: FunnelIntegrationRepository = Depends(
        get_funnel_integration_repository
    ),
    launch_qa_repository: LaunchQARepository = Depends(
        get_launch_qa_repository
    ),
    workspace_store: ClientWorkspaceStore = Depends(
        get_client_workspace_store
    ),
) -> dict[str, Any]:
    """Record the stage 9 "Launch Approved" gate through the use case.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageNineGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageNineGateHandler`` and appends
    the resulting ``GateDecision``. Stage 9 depends on stage 8, so governance
    refuses the decision unless the ledger already holds a passing stage 8
    decision (SPEC.md section 4). The stage 9 ``StageRun`` is loaded-or-created and
    upserted through the ``StageRunRepository`` port in the same operation.

    SPEC.md section 4, stage 9 "QA" and its "Launch Approved" checkpoint: all
    critical path checks pass, exceptions have owners, and the designated human
    authorizes traffic, grounded on the completed stage 8 funnel (canon files 01,
    08, 21, 22 and 24 per SPEC.md section 12.3). The route rebuilds the reviewed QA
    on the rebuilt complete stage 8 funnel and drives ``authorize_traffic``, so the
    ``LaunchApprovedPolicy`` and ``ComplianceRequiredPolicy`` -- not the transport
    layer -- decide whether the seventeen canonical kinds may be pinned as passing
    evidence. The route resolves the approved method, production ready offer,
    approved stage 6 message and approved stage 7 amplifier from their stores by
    exact identity, and resolves the completed stage 8 funnel from its store by
    exact identity rather than trusting the repeated request body; every integrity
    rule -- the complete
    same-tenant check set, the critical path outcomes, the compliance package, the
    grounded stage 8 dependency, the canonical kinds, exact versions,
    owner/approver authority and the tenant boundary -- stays enforced by the
    domain, and a rejection is a named 422 and never a partial write. The path
    tenant, not the body, is the authoritative client scope.

    SPEC.md sections 3 and 4 make the ClientWorkspace the tenant root that holds
    the authority registry a gate approves against. The workspace is resolved
    from the durable store by ``(tenant_id, workspace_id)`` rather than rebuilt
    from the request body, so the approver and owner are checked against the
    persisted registry and a caller cannot substitute its own; an unregistered
    workspace is a named 404, not a gate (SPEC.md section 11).
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = workspace_store.get(tenant_id, body.workspace_id)
        if workspace is None:
            raise ClientWorkspaceNotFoundError(
                f"workspace {body.workspace_id!r} is not registered for "
                f"{tenant_id!r}"
            )
        method, _method_reference, _offer, message = _approve_method_offer_message(
            tenant_id,
            method_body=body.method,
            offer_body=body.offer,
            message_body=body.message,
            method_repository=method_repository,
            offer_repository=offer_repository,
            message_repository=campaign_message_repository,
        )
        amplifier = _approve_authority_amplifier(
            tenant_id,
            method=method,
            message=message,
            amplifier_body=body.amplifier,
            claims_body=body.claims,
            amplifier_repository=authority_amplifier_repository,
        )
        funnel = _complete_stage_eight_funnel(
            tenant_id, body.funnel, amplifier, funnel_repository
        )
        qa = _authorize_launch_qa(
            tenant_id, body.qa, funnel, launch_qa_repository
        )
        package = LaunchQAPackage(
            package_id=body.qa_package_id,
            tenant_id=tenant_id,
            qa=qa,
            qa_version=body.qa_version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 9, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=9,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 9 launch QA work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageNineGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageNineGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except ClientWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except (
        CommercialError,
        EngagementError,
        ExecutionError,
        GovernanceError,
        MethodError,
        ProductionError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.post("/clients/{tenant_id}/stages/10/gate", status_code=201)
def record_stage_ten_gate(
    tenant_id: str,
    body: RecordStageTenGateRequest,
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
    method_repository: MethodVersionRepository = Depends(
        get_method_version_repository
    ),
    offer_repository: OfferVersionRepository = Depends(
        get_offer_version_repository
    ),
    campaign_message_repository: CampaignMessageRepository = Depends(
        get_campaign_message_repository
    ),
    authority_amplifier_repository: AuthorityAmplifierRepository = Depends(
        get_authority_amplifier_repository
    ),
    funnel_repository: FunnelIntegrationRepository = Depends(
        get_funnel_integration_repository
    ),
    launch_qa_repository: LaunchQARepository = Depends(
        get_launch_qa_repository
    ),
    workspace_store: ClientWorkspaceStore = Depends(
        get_client_workspace_store
    ),
) -> dict[str, Any]:
    """Record the stage 10 "Performance Baseline Established" gate.

    SPEC.md section 6: the API calls the use case and never mutates persistence
    directly. This route maps the typed request to the Engagement
    ``RecordStageTenGateCommand``, loads the tenant's ledger through the
    ``GateLedgerRepository`` port, runs ``RecordStageTenGateHandler`` and appends
    the resulting ``GateDecision``. Stage 10 depends on stage 9, so governance
    refuses the decision unless the ledger already holds a passing stage 9
    decision (SPEC.md section 4). The stage 10 ``StageRun`` is loaded-or-created
    and upserted through the ``StageRunRepository`` port in the same operation.

    SPEC.md section 4, stage 10 "Launch" and its "Performance Baseline
    Established" checkpoint: the required live campaign, spend, lead, conversion,
    engagement, booking, close, acquisition cost, attribution and issue-log assets
    exist, the stage 9 launch QA authorized traffic and first qualified traffic
    was observed, with the later lead, appointment and sale milestones shown as
    distinct observed-or-pending observations (canon files 22, 23, 29-31, 33 and
    34 per SPEC.md section 12.3). The route rebuilds the reviewed baseline on the
    rebuilt ready-for-traffic stage 9 launch QA and drives ``establish``, so the
    ``PerformanceBaselinePolicy`` -- not the transport layer -- decides whether the
    twelve canonical kinds may be pinned as passing evidence. The route resolves
    the approved method, production ready offer, approved stage 6 message and
    approved stage 7 amplifier from their stores by exact identity, and resolves the
    completed stage 8 funnel and the ready-for-traffic stage 9 launch QA from their
    stores by exact identity rather than trusting the repeated request body; every
    integrity rule -- the
    grounded stage 9 dependency, the distinct
    milestones, the observed-first-traffic rule, the canonical kinds, exact
    versions, owner/approver authority and the tenant boundary -- stays enforced by
    the domain, and a rejection is a named 422 and never a partial write. The path
    tenant, not the body, is the authoritative client scope.

    SPEC.md sections 3 and 4 make the ClientWorkspace the tenant root that holds
    the authority registry a gate approves against. The workspace is resolved
    from the durable store by ``(tenant_id, workspace_id)`` rather than rebuilt
    from the request body, so the approver and owner are checked against the
    persisted registry and a caller cannot substitute its own; an unregistered
    workspace is a named 404, not a gate (SPEC.md section 11).
    """

    template = stage_zero_to_ten_template()
    try:
        workspace = workspace_store.get(tenant_id, body.workspace_id)
        if workspace is None:
            raise ClientWorkspaceNotFoundError(
                f"workspace {body.workspace_id!r} is not registered for "
                f"{tenant_id!r}"
            )
        method, _method_reference, _offer, message = _approve_method_offer_message(
            tenant_id,
            method_body=body.method,
            offer_body=body.offer,
            message_body=body.message,
            method_repository=method_repository,
            offer_repository=offer_repository,
            message_repository=campaign_message_repository,
        )
        amplifier = _approve_authority_amplifier(
            tenant_id,
            method=method,
            message=message,
            amplifier_body=body.amplifier,
            claims_body=body.claims,
            amplifier_repository=authority_amplifier_repository,
        )
        funnel = _complete_stage_eight_funnel(
            tenant_id, body.funnel, amplifier, funnel_repository
        )
        qa = _authorize_launch_qa(
            tenant_id, body.qa, funnel, launch_qa_repository
        )
        assets = LaunchAssetPackage(
            live_campaign=body.baseline.assets.live_campaign,
            spend_records=body.baseline.assets.spend_records,
            lead_records=body.baseline.assets.lead_records,
            conversion_measures=body.baseline.assets.conversion_measures,
            engagement_measures=body.baseline.assets.engagement_measures,
            applications=body.baseline.assets.applications,
            bookings=body.baseline.assets.bookings,
            shows=body.baseline.assets.shows,
            closes=body.baseline.assets.closes,
            acquisition_cost=body.baseline.assets.acquisition_cost,
            attribution=body.baseline.assets.attribution,
            issue_log=body.baseline.assets.issue_log,
        )
        baseline = PerformanceBaseline(
            baseline_id=body.baseline.baseline_id,
            tenant_id=tenant_id,
            launch_qa=qa,
            owner=body.baseline.owner,
            assets=assets,
            milestones=tuple(
                MilestoneObservation(
                    kind=MilestoneKind(entry.kind),
                    status=ObservationStatus(entry.status),
                    tenant_id=tenant_id,
                    observed_on=entry.observed_on,
                    source=entry.source,
                    detail=entry.detail,
                )
                for entry in body.baseline.milestones
            ),
        ).establish(on=body.on)
        package = PerformanceBaselinePackage(
            package_id=body.baseline_package_id,
            tenant_id=tenant_id,
            baseline=baseline,
            baseline_version=body.baseline_version,
        )
        stage_run = run_repository.load(
            template.version, workspace.workspace_id, 10, tenant_id
        )
        if stage_run is None:
            stage_run = StageRun(
                engagement=workspace.workspace_id,
                stage_number=10,
                template_version=template.version,
                assigned_owner=body.stage_owner,
                tenant_id=tenant_id,
            )
        stage_run.record_activity(
            actor=body.stage_owner,
            reason="stage 10 performance baseline work began",
            on=body.on,
            correlation_id=body.correlation_id,
        )
        command = RecordStageTenGateCommand(
            template=template,
            workspace=workspace,
            package=package,
            stage_run=stage_run,
            approver=body.approver,
            scope=body.scope,
            checkpoint_evidence=body.checkpoint_evidence,
            rationale=body.rationale,
            assigned_owner=body.assigned_owner,
            due_on=body.due_on,
            on=body.on,
            correlation_id=body.correlation_id,
            proposed_by=body.proposed_by,
            next_action=body.next_action,
        )
        ledger = repository.load(template, tenant_id)
        decision = RecordStageTenGateHandler().handle(command, ledger=ledger)
        repository.append(decision)
        run_repository.save(stage_run)
    except ClientWorkspaceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except (
        CommercialError,
        EngagementError,
        ExecutionError,
        GovernanceError,
        MethodError,
        ProductionError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return {
        "stage_number": decision.stage_number,
        "template_version": decision.template_version,
        "checkpoint": decision.checkpoint,
        "disposition": decision.disposition.value,
        "reviewer": decision.reviewer,
        "scope": decision.scope,
        "tenant_id": decision.tenant_id,
        "decided_on": decision.decided_on.isoformat(),
        "next_action": decision.next_action,
        "required_assets": [
            {
                "asset_id": asset.asset_id,
                "version": asset.version,
            }
            for asset in decision.required_assets
        ],
    }


@router.get(
    "/clients/{tenant_id}/engagements/{engagement}/production-view",
    response_model=EngagementProductionViewResponse,
)
def get_engagement_production_view(
    tenant_id: str,
    engagement: str,
    on: date,
    verified_post_launch_milestones: int = 0,
    activity_entries: int = 0,
    ledger_repository: GateLedgerRepository = Depends(
        get_gate_ledger_repository
    ),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
) -> EngagementProductionViewResponse:
    """Serve the production-manager view for one client engagement.

    SPEC.md section 4 requires the production view to answer, per client, the
    current stage, what should exist, what is present and approved, what is
    missing, who is accountable, which dependency blocks work, what approval is
    next and when it is due, and SPEC.md section 6 requires the API to call a use
    case through ports rather than read a store directly. This route maps the
    request to the Governance ``EngagementProductionViewQuery``, runs
    ``GetEngagementProductionViewHandler`` through the ``GateLedgerRepository``
    and ``StageRunRepository`` seams and returns the projected view. Every
    integrity rule -- the tenant boundary, the stage dependency graph, exact
    pinned versions and the separation of activity from verified progress -- stays
    enforced by the pure domain view; the route computes none of it. The
    evaluation instant ``on`` is required because a prerequisite's expiry is only
    meaningful against a fixed time (SPEC.md section 4).
    """

    query = EngagementProductionViewQuery(
        template=stage_zero_to_ten_template(),
        engagement=engagement,
        tenant_id=tenant_id,
        on=on,
        verified_post_launch_milestones=verified_post_launch_milestones,
        activity_entries=activity_entries,
    )
    try:
        view = GetEngagementProductionViewHandler(
            ledger_repository=ledger_repository,
            run_repository=run_repository,
        ).handle(query)
    except (GovernanceError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return _production_view_payload(view)


def get_workflow_run_store() -> Iterator[WorkflowRunStore]:
    """Provide the configured durable workflow run seam to the API (SPEC.md §7).

    SPEC.md section 7 exposes the workflow run as ``/workflows/{id}`` and section
    11 requires a restarting worker to preserve a waiting workflow, so the run
    state the route serves must come from the same durable store the worker
    writes. The dependency owns one adapter for the request and releases any
    connection it opened when the request ends; the store is chosen once from
    ``DATABASE_URL``, and a set-but-unusable configuration raises before the
    route runs, so a deployment cannot mistake a process-local run store for a
    durable one (SPEC.md section 6).
    """

    store = workflow_run_store_from_env(os.environ.get("DATABASE_URL"))
    try:
        yield store
    finally:
        store.close()


@router.get("/clients/{tenant_id}/workflows/{run_id}")
def get_workflow_run(
    tenant_id: str,
    run_id: str,
    store: WorkflowRunStore = Depends(get_workflow_run_store),
) -> dict[str, Any]:
    """Serve one client's durable workflow run for polling (SPEC.md section 7).

    SPEC.md section 7 streams workflow status by server sent events or polling
    with stable event IDs; this route is the polling read. The path tenant, not
    any request value, is the authoritative client scope, and the store read is
    tenant scoped (SPEC.md section 9), so another client's run is
    indistinguishable from a missing one and is served as 404 rather than
    leaked. Every status change keeps its actor, reason, timestamp, old and new
    status and correlation id (SPEC.md section 4), and the run pins the exact
    definition version it started on (SPEC.md section 10); the route computes
    none of that, it only projects the stored aggregate.
    """

    run = store.get(run_id, tenant_id=tenant_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "WorkflowRunNotFoundError",
                "message": (
                    f"no workflow run {run_id!r} for tenant {tenant_id!r}"
                ),
            },
        )

    transitions = run.transitions
    return {
        "run_id": run.run_id,
        "tenant_id": run.tenant_id,
        "definition_id": run.definition.definition_id,
        "definition_version": run.definition.version,
        "status": run.status.value,
        "completed_steps": list(run.completed_steps),
        "in_progress_step": run.in_progress_step,
        "pending_approval": run.pending_approval,
        "failure_reason": run.failure_reason,
        "next_step": None if run.next_step is None else run.next_step.name,
        "event_id": f"{run.run_id}:{len(transitions)}",
        "transitions": [
            {
                "event_id": f"{run.run_id}:{index}",
                "actor": transition.actor,
                "reason": transition.reason,
                "occurred_at": transition.occurred_at.isoformat(),
                "old_status": transition.old_status.value,
                "new_status": transition.new_status.value,
                "correlation_id": transition.correlation_id,
            }
            for index, transition in enumerate(transitions, start=1)
        ],
    }


def _workspace_payload(workspace: ClientWorkspace) -> dict[str, Any]:
    """Project a stored workspace onto the response shape, computing no rule."""

    return {
        "workspace_id": workspace.workspace_id,
        "tenant_id": workspace.tenant_id,
        "lifecycle": workspace.lifecycle.value,
        "authorities": [
            {"actor": entry.actor, "authority": entry.authority}
            for entry in workspace.authorities
        ],
        "children": list(workspace.children),
    }


@router.get("/clients", response_model=ClientWorkspaceListResponse)
def list_client_workspaces(
    tenant_id: str = Query(
        ..., description="The client tenant whose workspaces are returned"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    store: ClientWorkspaceStore = Depends(get_client_workspace_store),
) -> ClientWorkspaceListResponse:
    """List one client tenant's workspaces (SPEC.md sections 3, 7 and 9).

    SPEC.md section 7 lists ``/clients`` and requires list endpoints to enforce
    client access and pagination; SPEC.md section 9 requires every tenant
    resource query to carry ``tenant_id``. The tenant is a required query
    parameter, not an optional filter, so the endpoint cannot produce a
    portfolio-wide read across clients; the store read is tenant scoped and a
    blank tenant is refused by the domain seam. Pagination is applied after the
    tenant-scoped read so a page is stable.
    """

    workspaces = store.list(tenant_id)
    page = workspaces[offset : offset + limit]
    return ClientWorkspaceListResponse(
        tenant_id=tenant_id,
        total=len(workspaces),
        limit=limit,
        offset=offset,
        workspaces=[_workspace_payload(workspace) for workspace in page],
    )


@router.post(
    "/clients", status_code=201, response_model=ClientWorkspaceResponse
)
def create_client_workspace(
    body: CreateClientWorkspaceRequest,
    store: ClientWorkspaceStore = Depends(get_client_workspace_store),
) -> ClientWorkspaceResponse:
    """Create the stage 0 client workspace tenant root (SPEC.md section 3).

    SPEC.md section 6 requires the API to call a use case through ports rather
    than mutate a store directly; the route maps the typed request to a domain
    ``ClientWorkspace``, which enforces its own invariants -- an opaque id, the
    tenant and a duplicate-free non-empty authority registry -- and then persists
    it through the port. The workspace tenant comes from the body because it is
    being created, not resolved; a refusal is a named 422 and never a partial
    write (SPEC.md sections 3, 4 and 9).
    """

    try:
        workspace = ClientWorkspace(
            workspace_id=body.workspace_id,
            tenant_id=body.tenant_id,
            authorities=tuple(
                ClientAuthority(actor=entry.actor, authority=entry.authority)
                for entry in body.authorities
            ),
        )
        store.save(workspace)
    except (EngagementError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return _workspace_payload(workspace)


@router.get(
    "/clients/{tenant_id}/sources", response_model=SourceRecordListResponse
)
def list_source_records(
    tenant_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    store: SourceRecordStore = Depends(get_source_record_store),
) -> SourceRecordListResponse:
    """List one client tenant's immutable source records (SPEC.md sections 3, 7, 9).

    SPEC.md section 7 lists ``/clients/{id}/sources`` and requires pagination;
    SPEC.md section 9 requires every query to carry the client scope. The path
    tenant is the authoritative scope and the store read is tenant scoped, so
    another client's sources are unreadable here.
    """

    sources = store.list(tenant_id)
    page = sources[offset : offset + limit]
    return SourceRecordListResponse(
        tenant_id=tenant_id,
        total=len(sources),
        limit=limit,
        offset=offset,
        sources=[
            {
                "source_id": source.source_id,
                "tenant_id": source.tenant_id,
                "locator": source.locator,
                "checksum": source.checksum,
                "captured_on": source.captured_on,
                "access_rule": source.access_rule,
            }
            for source in page
        ],
    )


@router.post(
    "/clients/{tenant_id}/sources",
    status_code=201,
    response_model=SourceRecordResponse,
)
def create_source_record(
    tenant_id: str,
    body: CreateSourceRecordRequest,
    store: SourceRecordStore = Depends(get_source_record_store),
) -> SourceRecordResponse:
    """Ingest one immutable source record a claim can cite (SPEC.md section 3).

    SPEC.md section 3 keeps the original immutable and its tenant on every
    resource; SPEC.md section 11 requires source attribution to survive
    ingestion. The path tenant, not the body, is the authoritative client scope,
    so a caller cannot record a source under another client's tenant. The domain
    value object enforces the required locator, checksum, capture time and access
    rule and the store refuses a different same-key body, so an original is never
    silently rewritten; a refusal is a named 422 or 409 and never a partial
    write.
    """

    try:
        source = SourceRecord(
            source_id=body.source_id,
            tenant_id=tenant_id,
            locator=body.locator,
            checksum=body.checksum,
            captured_on=body.captured_on,
            access_rule=body.access_rule,
        )
        store.save(source)
    except KnowledgeError as exc:
        status = 409 if type(exc).__name__ == "SourceRecordImmutableError" else 422
        raise HTTPException(
            status_code=status,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return SourceRecordResponse(
        source_id=source.source_id,
        tenant_id=source.tenant_id,
        locator=source.locator,
        checksum=source.checksum,
        captured_on=source.captured_on,
        access_rule=source.access_rule,
    )


def _claim_payload(claim: Claim) -> dict[str, Any]:
    """Project a stored claim onto the response shape, computing no rule."""

    return {
        "claim_id": claim.claim_id,
        "tenant_id": claim.tenant_id,
        "statement": claim.statement,
        "provenance": claim.provenance.value,
        "confidence_note": claim.confidence_note,
        "is_directly_sourced": claim.is_directly_sourced,
        "citations": [
            {
                "source_id": citation.source_id,
                "checksum": citation.checksum,
                "location": citation.location,
            }
            for citation in sorted(
                claim.citations,
                key=lambda item: (item.source_id, item.location, item.checksum),
            )
        ],
    }


@router.get("/claims", response_model=ClaimListResponse)
def list_claims(
    tenant_id: str = Query(
        ..., description="The client tenant whose claims are returned"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    store: ClaimStore = Depends(get_claim_store),
) -> ClaimListResponse:
    """List one client tenant's claims (SPEC.md sections 3, 7 and 9).

    SPEC.md section 7 lists ``/claims`` and requires list endpoints to enforce
    client access and pagination; SPEC.md section 9 requires every tenant
    resource query to carry ``tenant_id``. The tenant is a required query
    parameter, not an optional filter, so the endpoint cannot produce a
    portfolio-wide read across clients; the store read is tenant scoped and a
    blank tenant is refused by the domain seam. Pagination is applied after the
    tenant-scoped read so a page is stable.
    """

    claims = store.list(tenant_id)
    page = claims[offset : offset + limit]
    return ClaimListResponse(
        tenant_id=tenant_id,
        total=len(claims),
        limit=limit,
        offset=offset,
        claims=[_claim_payload(claim) for claim in page],
    )


@router.post("/claims", status_code=201, response_model=ClaimResponse)
def create_claim(
    body: CreateClaimRequest,
    store: ClaimStore = Depends(get_claim_store),
    source_store: SourceRecordStore = Depends(get_source_record_store),
) -> ClaimResponse:
    """Record one claim with a verified source attribution (SPEC.md section 3).

    SPEC.md section 3 makes a Known claim cite at least one direct source and
    section 11 requires source attribution to survive ingestion. The route
    resolves every citation against the same tenant's immutable
    ``SourceRecordStore`` and refuses a citation whose source id is unknown or
    whose checksum does not match the stored original, so a caller cannot assert
    a Known claim against a fabricated citation. The claim's own invariants
    (unsupported Known, missing field) are enforced by the aggregate; a refusal
    is a named 422 or 409 and never a partial write.
    """

    try:
        for citation in body.citations:
            source = source_store.get(body.tenant_id, citation.source_id)
            if source is None or source.checksum != citation.checksum:
                raise ClaimCitationError(
                    f"claim {body.claim_id!r} cites source "
                    f"{citation.source_id!r}, which is not a stored original of "
                    f"tenant {body.tenant_id!r} with checksum "
                    f"{citation.checksum!r}; a claim cannot cite an unverifiable "
                    "source"
                )
        claim = Claim(
            claim_id=body.claim_id,
            tenant_id=body.tenant_id,
            statement=body.statement,
            provenance=ProvenanceClass(body.provenance),
            citations=frozenset(
                SourceCitation(
                    source_id=citation.source_id,
                    checksum=citation.checksum,
                    location=citation.location,
                )
                for citation in body.citations
            ),
            confidence_note=body.confidence_note,
        )
        store.save(claim)
    except KnowledgeError as exc:
        status = 409 if type(exc).__name__ == "ClaimConflictError" else 422
        raise HTTPException(
            status_code=status,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return _claim_payload(claim)


def _method_payload(method: MethodVersion) -> dict[str, Any]:
    """Project a stored approved method version, computing no rule."""

    approval = method.approval
    return {
        "method_id": method.method_id,
        "tenant_id": method.tenant_id,
        "parent_method": method.parent_method,
        "semantic_version": str(method.semantic_version),
        "stages": list(method.stages),
        "currency": method.currency,
        "claims": sorted(method.claims),
        "is_approved": method.is_approved,
        "approved_by": None if approval is None else approval.approved_by,
        "intended_use": None if approval is None else approval.intended_use,
        "approved_on": None if approval is None else approval.approved_on,
        "primary_currency": (
            None if method.primary_currency is None
            else method.primary_currency.currency
        ),
        "diagnostic_model_id": (
            None if method.diagnostic_model is None
            else method.diagnostic_model.model_id
        ),
        "signature_solution_id": (
            None if method.signature_solution is None
            else method.signature_solution.solution_id
        ),
    }


@router.get("/methods", response_model=MethodVersionListResponse)
def list_method_versions(
    tenant_id: str = Query(
        ..., description="The client tenant whose approved methods are returned"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repository: MethodVersionRepository = Depends(get_method_version_repository),
) -> MethodVersionListResponse:
    """List one client tenant's approved method versions (SPEC.md sections 3, 7, 9).

    SPEC.md section 7 lists ``/methods`` and requires pagination; SPEC.md section
    9 requires every query to carry the client scope. The tenant is a required
    query parameter and the repository read is tenant scoped, so another client's
    approved methods are unreadable here. The route is read-only: a method is born
    approved through its stage gate and a direct write here would let a caller
    confer the approval that governance owns (SPEC.md section 4), so no method
    write path is exposed.
    """

    methods = repository.list(tenant_id)
    page = methods[offset : offset + limit]
    return MethodVersionListResponse(
        tenant_id=tenant_id,
        total=len(methods),
        limit=limit,
        offset=offset,
        methods=[_method_payload(method) for method in page],
    )


def _method_reference_payload(reference: Any) -> MethodReferenceResponse:
    """Project one pinned method dependency of an offer, computing no rule."""

    return MethodReferenceResponse(
        method_id=reference.method_id,
        version=str(reference.version),
        intended_use=reference.intended_use,
    )


def _offer_payload(offer: OfferVersion) -> OfferVersionResponse:
    """Project a stored production ready offer, computing no rule."""

    return OfferVersionResponse(
        offer_id=offer.offer_id,
        tenant_id=offer.tenant_id,
        audience=offer.audience,
        promise=offer.promise,
        eligibility=offer.eligibility,
        price_hypothesis=offer.price_hypothesis,
        owner=offer.owner,
        state=offer.state.value,
        is_production_ready=offer.is_production_ready,
        method_refs=[
            _method_reference_payload(reference)
            for reference in offer.method_refs
        ],
        review_reason=offer.review_reason,
    )


@router.get("/offers", response_model=OfferListResponse)
def list_offer_versions(
    tenant_id: str = Query(
        ..., description="The client tenant whose approved offers are returned"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repository: OfferVersionRepository = Depends(get_offer_version_repository),
) -> OfferListResponse:
    """List one client tenant's production ready offers (SPEC.md sections 3, 7, 9).

    SPEC.md section 7 lists ``/offers`` and requires pagination; SPEC.md section 9
    requires every query to carry the client scope. The tenant is a required query
    parameter and the repository read is tenant scoped, so another client's offers
    are unreadable here. The route is read-only: an offer becomes production ready
    through the stage 5 "Offer Locked" gate and a direct write here would let a
    caller confer the readiness the offer's approved method dependencies own
    (SPEC.md sections 3 and 4), so no offer write path is exposed.
    """

    offers = repository.list(tenant_id)
    page = offers[offset : offset + limit]
    return OfferListResponse(
        tenant_id=tenant_id,
        total=len(offers),
        limit=limit,
        offset=offset,
        offers=[_offer_payload(offer) for offer in page],
    )


def _build_payload(build: BuildObject) -> BuildObjectResponse:
    """Project a stored production work item, computing no rule."""

    return BuildObjectResponse(
        build_id=build.build_id,
        tenant_id=build.tenant_id,
        build_type=build.build_type,
        purpose=build.purpose,
        audience=build.audience,
        owner=build.owner,
        next_action=build.next_action,
        state=build.state.value,
        is_active=build.is_active,
        is_blocked=build.is_blocked,
        blockers=sorted(build.blockers),
        refs=sorted(build.refs),
    )


@router.get("/builds", response_model=BuildListResponse)
def list_builds(
    tenant_id: str = Query(
        ..., description="The client tenant whose production builds are returned"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repository: BuildObjectRepository = Depends(get_build_object_repository),
) -> BuildListResponse:
    """List one client tenant's production work items (SPEC.md sections 3, 7, 9).

    SPEC.md section 7 lists ``/builds`` and requires pagination, and SPEC.md
    section 3 makes a BuildObject the unit of production work whose invariant is
    that an active build always has an owner and a next action. The tenant is a
    required query parameter and the repository read is tenant scoped, so another
    client's builds are unreadable here. Pagination is applied after the
    tenant-scoped read so a page is stable.
    """

    builds = repository.list(tenant_id)
    page = builds[offset : offset + limit]
    return BuildListResponse(
        tenant_id=tenant_id,
        total=len(builds),
        limit=limit,
        offset=offset,
        builds=[_build_payload(build) for build in page],
    )


@router.post("/builds", status_code=201, response_model=BuildObjectResponse)
def create_build(
    body: CreateBuildRequest,
    repository: BuildObjectRepository = Depends(get_build_object_repository),
) -> BuildObjectResponse:
    """Record one production work item as an Identified proposal (SPEC.md section 3).

    SPEC.md section 3 makes an active build always carry an owner and a next
    action, and section 5 keeps agent and caller output a proposal rather than an
    implicit grant of authority. The route constructs the aggregate, so a blank
    owner, purpose or next action is refused by the domain as a named 422 and the
    build starts Identified; it is not a gate and it approves nothing. The tenant
    is carried on the aggregate and the store refuses an unscoped write.
    """

    try:
        build = BuildObject(
            build_id=body.build_id,
            tenant_id=body.tenant_id,
            build_type=body.build_type,
            purpose=body.purpose,
            audience=body.audience,
            owner=body.owner,
            next_action=body.next_action,
            refs=frozenset(body.refs),
        )
        repository.save(build)
    except (InvalidBuildError, BuildTenantBoundaryError) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return _build_payload(build)


def _decision_payload(decision: Any) -> DecisionRecordResponse:
    """Project one durable gate decision onto the decision record, computing no rule.

    SPEC.md section 3 makes a Decision an append-only record of its subject,
    choice, rationale, actor, timestamp and exact affected version. The pinned
    required assets are sorted by kind and version so a decision's affected
    versions render deterministically; the exact versions are exactly those the
    gate sealed, never re-declared from a request.
    """

    return DecisionRecordResponse(
        stage_number=decision.stage_number,
        template_version=decision.template_version,
        checkpoint=decision.checkpoint,
        disposition=decision.disposition.value,
        reviewer=decision.reviewer,
        scope=decision.scope,
        rationale=decision.rationale,
        decided_on=decision.decided_on,
        assigned_owner=decision.assigned_owner,
        due_on=decision.due_on,
        next_action=decision.next_action,
        tenant_id=decision.tenant_id,
        required_assets=[
            AssetVersionResponse(asset_id=asset.asset_id, version=asset.version)
            for asset in sorted(
                decision.required_assets,
                key=lambda asset: (asset.asset_id, asset.version),
            )
        ],
    )


@router.get("/decisions", response_model=DecisionListResponse)
def list_decisions(
    tenant_id: str = Query(
        ..., description="The client tenant whose decisions are returned"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
) -> DecisionListResponse:
    """List one client tenant's append-only governance decisions (SPEC.md sections 3, 7, 9).

    SPEC.md section 7 lists ``/decisions`` and section 3 makes decision history
    append only; SPEC.md section 9 requires every query to carry the client
    scope. The tenant is a required query parameter and the ledger read is tenant
    scoped, so another client's decisions are unreadable here. Decisions are
    returned in canonical stage order, and within a stage in the order they were
    recorded, so the history never reorders or edits an earlier decision. The
    route is read-only: a decision is recorded through its stage gate and a
    direct write here would let a caller confer the approval governance owns
    (SPEC.md section 4).
    """

    template = stage_zero_to_ten_template()
    ledger = repository.load(template, tenant_id)
    decisions = [
        decision
        for stage in template.stages
        for decision in ledger.decisions_for(stage.stage_number)
    ]
    page = decisions[offset : offset + limit]
    return DecisionListResponse(
        tenant_id=tenant_id,
        total=len(decisions),
        limit=limit,
        offset=offset,
        decisions=[_decision_payload(decision) for decision in page],
    )


def _approval_payload(decision: Any, approval: Any) -> ApprovalRecordResponse:
    """Project one version-specific approval from a decision, computing no rule.

    SPEC.md sections 3 and 4 keep an approval pinned to one exact asset version
    and one intended scope. The projection surfaces that exact version and scope
    plus the requester, the designated approver and the outcome; it carries the
    stage and decision date so an approval is traceable to the decision that
    recorded it.
    """

    return ApprovalRecordResponse(
        asset_id=approval.asset.asset_id,
        version=approval.asset.version,
        scope=approval.scope,
        requested_by=approval.requested_by,
        approver=approval.approver,
        outcome=approval.outcome.value,
        expires_on=approval.expires_on,
        stage_number=decision.stage_number,
        decided_on=decision.decided_on,
    )


@router.get("/approvals", response_model=ApprovalListResponse)
def list_approvals(
    tenant_id: str = Query(
        ..., description="The client tenant whose approvals are returned"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repository: GateLedgerRepository = Depends(get_gate_ledger_repository),
) -> ApprovalListResponse:
    """List one client tenant's version-specific approvals (SPEC.md sections 3, 4, 7, 9).

    SPEC.md section 7 lists ``/approvals``; sections 3 and 4 keep an approval
    version specific and scoped to one intended use, and section 9 requires the
    client scope on every query. Each approval is read from the durable decision
    that recorded it, so the exact asset version and scope are the ones the gate
    sealed. The tenant is a required query parameter and the ledger read is
    tenant scoped. The route is read-only and never grants authority: only the
    passing decision's pinned approvals authorize downstream use, so listing an
    approval cannot itself authorize production or traffic (SPEC.md section 4).
    """

    template = stage_zero_to_ten_template()
    ledger = repository.load(template, tenant_id)
    approvals = [
        (decision, approval)
        for stage in template.stages
        for decision in ledger.decisions_for(stage.stage_number)
        for approval in decision.asset_approvals
    ]
    page = approvals[offset : offset + limit]
    return ApprovalListResponse(
        tenant_id=tenant_id,
        total=len(approvals),
        limit=limit,
        offset=offset,
        approvals=[
            _approval_payload(decision, approval)
            for decision, approval in page
        ],
    )


def _metric_payload(metric: MetricDefinition) -> MetricDefinitionResponse:
    """Project a registered metric definition, computing no rule."""

    return MetricDefinitionResponse(
        metric_id=metric.metric_id,
        tenant_id=metric.tenant_id,
        name=metric.name,
        funnel_step=metric.funnel_step.value,
        unit=metric.unit.value,
        direction=metric.direction.value,
        version=metric.version,
    )


def _measurement_payload(record: MeasurementRecord) -> MeasurementRecordResponse:
    """Project a recorded observation, computing no rule.

    SPEC.md section 3 keys an observation by its metric, window, basis and
    source; the projection surfaces the exact metric version, the closed window
    and whether the figure is observed or placeholder, so a placeholder never
    reads as a measured result.
    """

    return MeasurementRecordResponse(
        record_id=record.record_id,
        tenant_id=record.tenant_id,
        metric=_metric_payload(record.metric),
        value=record.value,
        window_start=record.window.start,
        window_end=record.window.end,
        basis=record.basis.value,
        source=record.source,
        sample_size=record.sample_size,
        recorded_on=record.recorded_on,
        is_observed=record.is_observed,
    )


@router.get("/measurements", response_model=MeasurementListResponse)
def list_measurements(
    tenant_id: str = Query(
        ..., description="The client tenant whose observations are returned"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    registry: MeasurementRegistry = Depends(get_measurement_registry),
) -> MeasurementListResponse:
    """List one client tenant's recorded observations (SPEC.md sections 3, 7, 9).

    SPEC.md section 7 lists ``/measurements`` and requires list endpoints to
    enforce client access and pagination; SPEC.md section 9 requires every tenant
    resource query to carry ``tenant_id``. The tenant is a required query
    parameter, not an optional filter, so the endpoint cannot produce a
    portfolio-wide read across clients; the registry read is tenant scoped and a
    blank tenant is refused by the domain seam. Pagination is applied after the
    tenant-scoped read so a page is stable. The route is read-only and computes
    no metric or movement.
    """

    records = registry.list_records(tenant_id)
    page = records[offset : offset + limit]
    return MeasurementListResponse(
        tenant_id=tenant_id,
        total=len(records),
        limit=limit,
        offset=offset,
        records=[_measurement_payload(record) for record in page],
    )


@router.post(
    "/measurements", status_code=201, response_model=MeasurementRecordResponse
)
def record_measurement(
    body: RecordMeasurementRequest,
    registry: MeasurementRegistry = Depends(get_measurement_registry),
) -> MeasurementRecordResponse:
    """Record one observation of a versioned metric (SPEC.md sections 3 and 7).

    SPEC.md section 3 keys a Measurement aggregate by its metric definition and
    window and its invariant keeps observations distinct from causal
    conclusions. The route registers the exact versioned metric definition and
    then records the observation, both append-only; the domain refuses a record
    written before its window closed and one that attaches to another tenant's
    metric. An identical replay is idempotent and a changed same-key re-statement
    is a named 409, never a silent rewrite. Recording an observation is not a
    gate and grants no authority; a material optimization still needs the owner
    approval of SPEC.md section 4.
    """

    metric = MetricDefinition(
        metric_id=body.metric.metric_id,
        tenant_id=body.metric.tenant_id,
        name=body.metric.name,
        funnel_step=MetricFunnelStep(body.metric.funnel_step),
        unit=MetricUnit(body.metric.unit),
        direction=MetricDirection(body.metric.direction),
        version=body.metric.version,
    )
    try:
        record = MeasurementRecord(
            record_id=body.record_id,
            tenant_id=body.tenant_id,
            metric=metric,
            value=body.value,
            window=MeasurementWindow(
                start=body.window.start, end=body.window.end
            ),
            basis=MeasurementBasis(body.basis),
            source=body.source,
            sample_size=body.sample_size,
            recorded_on=body.recorded_on,
        )
        registry.save_metric(metric)
        registry.save_record(record)
    except MeasurementError as exc:
        status = (
            409 if type(exc).__name__ == "MeasurementConflictError" else 422
        )
        raise HTTPException(
            status_code=status,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return _measurement_payload(record)


def _journey_release_payload(release: JourneyRelease) -> JourneyReleaseResponse:
    """Project one authorized journey release onto the read surface.

    SPEC.md sections 3 and 4 pin exact asset versions at a passing gate, so the
    released assets are returned in a deterministic order with their exact
    identity, tenant, kind and version, and the grounding QA id is surfaced so the
    release stays traceable to the stage 9 authorization that permitted it. The
    route computes no rule; the aggregate already re-validated on construction.
    """

    assets = sorted(
        release.assets, key=lambda asset: (asset.kind, asset.asset_id)
    )
    return JourneyReleaseResponse(
        release_id=release.release_id,
        tenant_id=release.tenant_id,
        qa_id=release.qa.qa_id,
        assets=[
            JourneyReleaseAssetResponse(
                asset_id=asset.asset_id,
                tenant_id=asset.tenant_id,
                kind=asset.kind,
                version=asset.version,
            )
            for asset in assets
        ],
        routing=release.routing,
        configuration_digest=release.configuration_digest,
        rollback_ref=release.rollback_ref,
        released_kinds=sorted(release.released_kinds),
        is_signed_ready=release.is_signed_ready,
        is_authorized=release.is_authorized,
    )


@router.get("/journeys", response_model=JourneyReleaseListResponse)
def list_journeys(
    tenant_id: str = Query(
        ..., description="The client tenant whose journey releases are returned"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repository: JourneyReleaseRepository = Depends(
        get_journey_release_repository
    ),
) -> JourneyReleaseListResponse:
    """List one client tenant's authorized journey releases (SPEC.md sections 3, 7, 9).

    SPEC.md section 7 lists ``/journeys`` and requires list endpoints to enforce
    client access and pagination; SPEC.md section 9 requires every tenant resource
    query to carry ``tenant_id``. The tenant is a required query parameter and the
    repository read is tenant scoped, so another client's releases are unreadable
    here. Pagination is applied after the tenant-scoped read so a page is stable,
    and the route is read-only: a release is recorded through its own route and
    listing one never authorizes traffic.
    """

    releases = repository.list(tenant_id)
    page = releases[offset : offset + limit]
    return JourneyReleaseListResponse(
        tenant_id=tenant_id,
        total=len(releases),
        limit=limit,
        offset=offset,
        releases=[_journey_release_payload(release) for release in page],
    )


@router.post(
    "/journeys", status_code=201, response_model=JourneyReleaseResponse
)
def create_journey_release(
    body: RecordJourneyReleaseRequest,
    repository: JourneyReleaseRepository = Depends(
        get_journey_release_repository
    ),
    launch_qa_repository: LaunchQARepository = Depends(
        get_launch_qa_repository
    ),
) -> JourneyReleaseResponse:
    """Authorize one journey release grounded on a durable stage 9 launch QA.

    SPEC.md section 3 names ``JourneyRelease`` (assets, routing, configuration
    digest, rollback ref) with the invariant "launch needs signed readiness and
    authorized release", and SPEC.md section 7 lists ``/journeys``. The route
    resolves the named stage 9 launch QA from the durable ``LaunchQARepository``
    rather than trusting a repeated QA body, so the release is grounded on the
    exact QA a prior gate authorized; a missing QA is a named 404, not a release.
    The released assets are mapped to exact ``StageAssetVersion`` evidence scoped
    to the release tenant, and the ``JourneyRelease`` aggregate -- not this route
    -- enforces the signed-ready and authorized QA, the non-blank routing, digest
    and rollback reference, and exactly one exact version per released kind. A
    rejection is a named 422 (a same-id re-statement is a named 409) and never a
    partial write. Recording a release does not authorize live traffic; that stays
    a stage 10 observation and a human approval.
    """

    try:
        qa = launch_qa_repository.get(body.tenant_id, body.qa_id)
        if qa is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "LaunchQANotFoundError",
                    "message": (
                        f"launch QA {body.qa_id!r} is not registered for "
                        f"{body.tenant_id!r}"
                    ),
                },
            )
        release = JourneyRelease(
            release_id=body.release_id,
            tenant_id=body.tenant_id,
            qa=qa,
            assets=tuple(
                StageAssetVersion(
                    asset_id=asset.asset_id,
                    tenant_id=body.tenant_id,
                    kind=asset.kind,
                    version=asset.version,
                )
                for asset in body.assets
            ),
            routing=body.routing,
            configuration_digest=body.configuration_digest,
            rollback_ref=body.rollback_ref,
        )
        repository.save(release)
    except JourneyReleaseError as exc:
        status = (
            409
            if type(exc).__name__ == "JourneyReleaseVersionConflictError"
            else 422
        )
        raise HTTPException(
            status_code=status,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return _journey_release_payload(release)


def _intervention_payload(card: Intervention) -> InterventionResponse:
    """Project one ranked intervention card onto the command center read surface.

    SPEC.md section 7 pins the card fields, so the payload carries them verbatim
    and sorts the evidence and affected builds for a stable response. The route
    computes no rule; the ranking policy and the ``Intervention`` value object
    already validated the card.
    """

    return InterventionResponse(
        client=card.client,
        reason=card.reason.value,
        severity=card.severity.value,
        subject=card.subject,
        explanation=card.explanation,
        evidence=sorted(card.evidence),
        owner=card.owner,
        next_action=card.next_action,
        due_on=card.due_on,
        state=card.state.value,
        affected_builds=sorted(card.affected_builds),
        resolution_note=card.resolution_note,
    )


@router.get("/interventions", response_model=InterventionListResponse)
def list_interventions(
    tenant_id: str = Query(
        ..., description="The client tenant whose interventions are returned"
    ),
    engagement: str = Query(
        ..., description="The client engagement the command center is scoped to"
    ),
    on: date = Query(
        ..., description="The evaluation instant the ranking is computed against"
    ),
    ledger_repository: GateLedgerRepository = Depends(
        get_gate_ledger_repository
    ),
    run_repository: StageRunRepository = Depends(get_stage_run_repository),
    dismissal_repository: InterventionDismissalRepository = Depends(
        get_intervention_dismissal_repository
    ),
) -> InterventionListResponse:
    """Rank one client's command center intervention cards (SPEC.md section 7).

    SPEC.md section 7 lists ``/interventions`` and requires the command center to
    surface, per client, the blocked critical path and overdue approvals (derived
    here from the production view) and to deduplicate them, and section 9 requires
    every tenant resource query to carry ``tenant_id``. Failed live journeys and
    nearing commitments are caller-supplied signals the Execution, Measurement and
    Engagement contexts own; they are not fabricated here and their own surfaces
    remain a follow-up, so this read currently ranks the two signals the platform
    itself derives. Stored operator dismissals are applied to the matching derived
    cards so a suppressed card is returned dismissed with its rationale; a
    dismissal whose card no longer surfaces is inert. Listing a card authorizes no
    action.
    """

    query = EngagementProductionViewQuery(
        template=stage_zero_to_ten_template(),
        engagement=engagement,
        tenant_id=tenant_id,
        on=on,
        verified_post_launch_milestones=0,
        activity_entries=0,
    )
    try:
        view = GetEngagementProductionViewHandler(
            ledger_repository=ledger_repository,
            run_repository=run_repository,
        ).handle(query)
        cards = InterventionRankingPolicy().rank(view, on=on)
    except (GovernanceError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    dismissals = {
        dismissal.key: dismissal
        for dismissal in dismissal_repository.list(tenant_id, engagement)
    }
    cards = tuple(
        card.dismiss(dismissals[card.key].rationale)
        if card.key in dismissals
        else card
        for card in cards
    )
    return InterventionListResponse(
        tenant_id=tenant_id,
        engagement=engagement,
        on=on,
        total=len(cards),
        interventions=[_intervention_payload(card) for card in cards],
    )


@router.post(
    "/interventions/dismiss",
    status_code=201,
    response_model=InterventionDismissalResponse,
)
def dismiss_intervention(
    body: DismissInterventionRequest,
    repository: InterventionDismissalRepository = Depends(
        get_intervention_dismissal_repository
    ),
) -> InterventionDismissalResponse:
    """Record one operator dismissal of an intervention card (SPEC.md section 7).

    SPEC.md section 7 allows a card to be dismissed with rationale. The route
    builds the typed ``InterventionDismissal`` (which refuses a missing tenant,
    client, reason, subject, rationale or actor) and stores it durably so the
    decision survives a restart (SPEC.md section 9). Recording a dismissal
    resolves no underlying blocker and takes no production action; it only
    suppresses the matching card on later reads. A same-key re-statement with
    different content is a named 409 rather than a rewritten decision.
    """

    try:
        dismissal = InterventionDismissal(
            tenant_id=body.tenant_id,
            client=body.client,
            reason=InterventionReason(body.reason),
            subject=body.subject,
            rationale=body.rationale,
            actor=body.actor,
            dismissed_on=body.dismissed_on,
        )
        repository.save(dismissal)
    except OperationsError as exc:
        status = (
            409
            if type(exc).__name__ == "InterventionDismissalConflictError"
            else 422
        )
        raise HTTPException(
            status_code=status,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc

    return InterventionDismissalResponse(
        tenant_id=dismissal.tenant_id,
        client=dismissal.client,
        reason=dismissal.reason.value,
        subject=dismissal.subject,
        rationale=dismissal.rationale,
        actor=dismissal.actor,
        dismissed_on=dismissal.dismissed_on,
    )
