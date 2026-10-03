"""HTTP request schemas for RED write endpoints.

These models are the entry-point adapter described in SPEC.md section 6: the API
calls use cases and never mutates persistence directly. They shape and type
inbound HTTP data only and carry no domain rule. Every integrity rule -- the
canonical intake asset kinds, exact positive asset versions, named owners and
the designated approver on the same workspace, directly sourced evidence and the
tenant boundary -- stays in the Engagement, Governance and Knowledge domains and
is surfaced as a named error, not validated here. Mapping these inputs to domain
value objects happens in the route so a malformed or unauthorized request is
refused by the domain, not accepted by the transport layer.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SourceCitationInput(BaseModel):
    """A checksum and location based reference to an exact source location."""

    source_id: str
    checksum: str
    location: str


class ClaimInput(BaseModel):
    """A statement with an explicit provenance class and citations."""

    claim_id: str
    statement: str
    provenance: str
    confidence_note: str = ""
    citations: list[SourceCitationInput] = Field(default_factory=list)


class ClientAuthorityInput(BaseModel):
    """A named actor and the authority they hold in a client workspace."""

    actor: str
    authority: str


class IntakeAssetInput(BaseModel):
    """One stage 0 intake asset with a kind, exact version, owner and source."""

    asset_id: str
    kind: str
    version: int
    owner: str
    summary: str
    evidence_claim_ids: list[str]


class RecordStageZeroGateRequest(BaseModel):
    """The stage 0 "Production Ready" gate request (SPEC.md section 4).

    The caller supplies the real intake assets, the workspace authority registry,
    the supporting claims and the decision metadata. The route builds the
    canonical gate from these through the use case; it deliberately accepts no
    pre-built gate, so owner authority and sourced evidence cannot be bypassed.
    """

    workspace_id: str
    authorities: list[ClientAuthorityInput]
    intake_package_id: str
    assets: list[IntakeAssetInput]
    claims: list[ClaimInput]
    stage_owner: str
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


class AvatarProfileInput(BaseModel):
    """The stage 1 avatar with the seven fields its checkpoint locks."""

    avatar_id: str
    version: int
    name: str
    demographics: str
    psychographics: str
    pains: list[str]
    goals: list[str]
    consequences_of_inaction: list[str]
    awareness: str
    customer_evidence_claim_ids: list[str]
    voice_notes: list[str]


class BusinessSnapshotInput(BaseModel):
    """The stage 1 business snapshot grounded on Knowledge claims."""

    snapshot_id: str
    version: int
    business_model: str
    current_offers: list[str]
    lead_sources: list[str]
    constraints: list[str]
    narrative: str
    evidence_claim_ids: list[str]


class OfferFunnelAuditInput(BaseModel):
    """The stage 1 offer and funnel audit grounded on Knowledge claims."""

    audit_id: str
    version: int
    offer_findings: list[str]
    funnel_steps: list[str]
    conversion_evidence: list[str]
    gaps: list[str]
    narrative: str
    evidence_claim_ids: list[str]


class RecordStageOneGateRequest(BaseModel):
    """The stage 1 "Avatar Locked" gate request (SPEC.md section 4).

    The caller supplies the reviewed diagnosis values, the workspace authority
    registry, the supporting claims and the decision metadata. The route builds
    the canonical gate from these through the use case; it deliberately accepts no
    pre-built gate, so approver authority and sourced evidence cannot be bypassed.
    Stage 1 depends on a passing stage 0 decision already in the ledger.
    """

    workspace_id: str
    authorities: list[ClientAuthorityInput]
    diagnosis_package_id: str
    avatar: AvatarProfileInput
    business_snapshot: BusinessSnapshotInput
    offer_funnel_audit: OfferFunnelAuditInput
    claims: list[ClaimInput]
    stage_owner: str
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


class CurrencyInventoryInput(BaseModel):
    """The reviewed stage 2 currency inventory (SPEC.md section 4, stage 2)."""

    inventory_id: str
    version: int
    category: str
    currencies_to_increase: list[str]
    currencies_to_decrease: list[str]


class PositioningDecisionInput(BaseModel):
    """The reviewed stage 2 positioning decision (SPEC.md section 4, stage 2)."""

    decision_id: str
    version: int
    core_problem: str
    transformation_statement: str
    horizon: str
    qualifications: list[str]
    disqualifications: list[str]


class PrimaryCurrencyInput(BaseModel):
    """The one locked stage 2 currency with its measurable movement."""

    currency: str
    version: int
    audience: str
    current_measure: str
    desired_measure: str
    mechanism: str


class MillionDollarMessageInput(BaseModel):
    """The stage 2 million dollar message and its formula components."""

    message_id: str
    version: int
    avatar: str
    currency: str
    metric: str
    timeline: str
    pain: str
    message: str


class RecordStageTwoGateRequest(BaseModel):
    """The stage 2 "Currency Locked" gate request (SPEC.md section 4).

    The caller supplies the reviewed positioning values, the workspace authority
    registry and the decision metadata. The route builds the canonical gate from
    these through the use case; it deliberately accepts no pre-built gate, so
    approver authority and exact-version evidence cannot be bypassed. Stage 2
    depends on a passing stage 1 decision already in the ledger. The currency
    inventory carries no claims: the "Currency Locked" checkpoint turns on the
    primary currency's internal specificity, not external customer evidence.
    """

    workspace_id: str
    authorities: list[ClientAuthorityInput]
    currency_package_id: str
    inventory: CurrencyInventoryInput
    positioning: PositioningDecisionInput
    primary_currency: PrimaryCurrencyInput
    million_dollar_message: MillionDollarMessageInput
    stage_owner: str
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


class ProfitPyramidLevelInput(BaseModel):
    """One reviewed stage 3 Profit Pyramid level (SPEC.md section 4, stage 3).

    Every level carries observable measures, symptoms, behaviors and problems,
    so a prospect can recognize which level they are on. The domain rejects a
    level that leaves any observable dimension unspecified.
    """

    level_id: str
    name: str
    observable_measures: list[str]
    symptoms: list[str]
    behaviors: list[str]
    problems: list[str]


class DiagnosticModelInput(BaseModel):
    """The reviewed stage 3 diagnostic model and its exact version.

    The model records the ordered Profit Pyramid levels, its progression and
    qualification logic, and the required visual and explanatory copy. The
    version is positive so the gate can pin the reviewed model exactly.
    """

    model_id: str
    version: int
    name: str
    levels: list[ProfitPyramidLevelInput]
    progression: str
    qualification_logic: str
    visual: str
    explanatory_copy: str


class RecordStageThreeGateRequest(BaseModel):
    """The stage 3 "Diagnostic Model Approved" gate request (SPEC.md section 4).

    The caller supplies the reviewed model values, the workspace authority
    registry and the decision metadata. The route builds the canonical gate from
    these through the use case; it deliberately accepts no pre-built gate, so
    approver authority and exact-version evidence cannot be bypassed. Stage 3
    depends on a passing stage 2 decision already in the ledger. The model
    carries no claims: the "Diagnostic Model Approved" checkpoint turns on
    adjacent-level observable distinguishability, which the domain enforces,
    rather than external customer evidence.
    """

    workspace_id: str
    authorities: list[ClientAuthorityInput]
    diagnostic_package_id: str
    model: DiagnosticModelInput
    stage_owner: str
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


class SignatureStepInput(BaseModel):
    """One reviewed stage 4 named stage (SPEC.md section 4, stage 4).

    Every named stage carries its own starting and final state and its inputs,
    actions and outputs, so the domain can enforce that the stages form one
    continuous chain from the declared starting state to the declared final
    state. The domain rejects a stage that leaves any dimension unspecified or
    that does not move the client between two distinct states.
    """

    step_id: str
    name: str
    starting_state: str
    final_state: str
    inputs: list[str]
    actions: list[str]
    outputs: list[str]


class TransformationPhaseInput(BaseModel):
    """One of the three stage 4 phases grouping the named stages.

    The domain requires exactly three phases and nine steps across them, so a
    phase that groups no step is refused rather than silently pinned.
    """

    phase_id: str
    name: str
    steps: list[SignatureStepInput]


class SignatureSolutionInput(BaseModel):
    """The reviewed stage 4 transformation and its exact version.

    The solution records the transformation map, process inventory, three
    phases, named stages, starting and final states, narrative and visual. The
    version is positive so the gate can pin the reviewed solution exactly.
    """

    solution_id: str
    version: int
    transformation_map: str
    process_inventory: list[str]
    phases: list[TransformationPhaseInput]
    starting_state: str
    final_state: str
    narrative: str
    visual: str


class RecordStageFourGateRequest(BaseModel):
    """The stage 4 "IP Architecture Locked" gate request (SPEC.md section 4).

    The caller supplies the reviewed transformation values, the workspace
    authority registry and the decision metadata. The route builds the canonical
    gate from these through the use case; it deliberately accepts no pre-built
    gate, so approver authority and exact-version evidence cannot be bypassed.
    Stage 4 depends on a passing stage 3 decision already in the ledger. The
    solution carries no claims: the "IP Architecture Locked" checkpoint turns on
    the coherence and continuity of the reviewed transformation, which the domain
    enforces at construction, rather than external customer evidence.
    """

    workspace_id: str
    authorities: list[ClientAuthorityInput]
    signature_package_id: str
    solution: SignatureSolutionInput
    stage_owner: str
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


class StepDeliveryInput(BaseModel):
    """One stage 5 delivery row for a named method step (SPEC.md section 4).

    The "Offer Locked" checkpoint requires every method step to carry an action,
    actor, deliverable, timing and measure. The domain refuses a row that leaves
    any of those unstated, so the transport layer only carries the values.
    """

    step_id: str
    action: str
    actor: str
    deliverable: str
    timing: str
    measure: str


class DeliverySpecificationInput(BaseModel):
    """The reviewed stage 5 delivery and its exact version (SPEC.md section 4).

    The specification grounds on the locked stage 4 transformation, so the same
    ``SignatureSolutionInput`` shape is nested here. The domain enforces the
    delivery model, duration, modules, responsibilities, cadence, step
    deliveries, outcome measures, pricing, scope, guarantee, eligibility and
    offer stack, and refuses a delivery for a step the method does not name or a
    method step left undelivered.
    """

    delivery_id: str
    version: int
    signature_solution: SignatureSolutionInput
    delivery_model: str
    duration: str
    modules: list[str]
    responsibilities: list[str]
    support_cadence: str
    step_deliveries: list[StepDeliveryInput]
    outcome_measures: list[str]
    pricing_payments: str
    scope: str
    guarantee_decision: str
    eligibility: str
    offer_stack: list[str]


class RecordStageFiveGateRequest(BaseModel):
    """The stage 5 "Offer Locked" gate request (SPEC.md section 4).

    The caller supplies the reviewed delivery values, the workspace authority
    registry and the decision metadata. The route builds the canonical gate from
    these through the use case; it deliberately accepts no pre-built gate, so
    approver authority and exact-version evidence cannot be bypassed. Stage 5
    depends on a passing stage 4 decision already in the ledger. The delivery
    carries no claims: the "Offer Locked" checkpoint turns on every method step
    carrying an action, actor, deliverable, timing and measure, which the domain
    enforces at construction, rather than external customer evidence.
    """

    workspace_id: str
    authorities: list[ClientAuthorityInput]
    offer_package_id: str
    delivery: DeliverySpecificationInput
    stage_owner: str
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


class SemanticVersionInput(BaseModel):
    """An exact method version (SPEC.md section 3, MethodVersion)."""

    major: int
    minor: int
    patch: int


class MethodVersionInput(BaseModel):
    """The stage 6 dependency: the approved method version the message grounds on.

    SPEC.md section 3: production requires approved dependencies, and stage 6's
    "Campaign Message Approved" checkpoint requires the message's method to be an
    approved version for the same tenant, exact version and intended use. The
    method pins its locked stage 2 primary currency, stage 3 diagnostic model and
    stage 4 Signature Solution; the route re-states them from the request because
    no MethodVersion store is exposed yet, so the caller supplies the approval
    that governance would otherwise own. That limitation is recorded in the plan.
    """

    method_id: str
    parent_method: str
    semantic_version: SemanticVersionInput
    stages: list[str]
    currency: str
    primary_currency: PrimaryCurrencyInput
    diagnostic_model: DiagnosticModelInput
    approved_by: str
    intended_use: str
    approved_on: date
    claims: list[str] = Field(default_factory=list)


class OfferVersionInput(BaseModel):
    """The stage 6 dependency: the production ready stage 5 offer.

    The offer carries the audience, promise, eligibility, price hypothesis,
    owner and the complete stage 5 delivery package (nested
    ``DeliverySpecificationInput``, which itself grounds on the locked stage 4
    transformation). The route derives the message's single method reference from
    the method input, so the offer is production ready once the method is
    approved.
    """

    offer_id: str
    audience: str
    promise: str
    eligibility: str
    price_hypothesis: str
    owner: str
    delivery: DeliverySpecificationInput


class CampaignMessageInput(BaseModel):
    """The reviewed stage 6 message fields (SPEC.md section 4, stage 6).

    The message carries the promise, problem hierarchy, desired outcome, proof and
    objections, story, method explanation, CTA, lead magnet, hook, angles, landing
    message and Authority Amplifier outline. The domain refuses a message whose
    avatar, currency, problem, promise or product do not agree with the approved
    method and offer, so the transport layer only carries the values.
    """

    message_id: str
    owner: str
    avatar: str
    currency: str
    problem: str
    promise: str
    cta: str
    product_offer_id: str
    problem_hierarchy: list[str]
    desired_outcome: str
    proof_objections: list[str]
    story: str
    method_explanation: str
    lead_magnet: str
    hook: str
    angles: list[str]
    landing_message: str
    authority_amplifier_outline: str


class RecordStageSixGateRequest(BaseModel):
    """The stage 6 "Campaign Message Approved" gate request (SPEC.md section 4).

    The caller supplies the reviewed message, the approved method and production
    ready offer it grounds on, the workspace authority registry and the decision
    metadata. The route builds the canonical gate from these through the use case;
    it deliberately accepts no pre-built gate, so approver authority and
    exact-version evidence cannot be bypassed. Stage 6 depends on a passing stage
    5 decision already in the ledger. The message carries no claims: the
    "Campaign Message Approved" checkpoint turns on the congruence of avatar,
    currency, problem, promise, method, product and CTA, which the domain
    enforces, rather than external customer evidence.
    """

    workspace_id: str
    authorities: list[ClientAuthorityInput]
    campaign_message_package_id: str
    message_version: int
    message: CampaignMessageInput
    offer: OfferVersionInput
    method: MethodVersionInput
    stage_owner: str
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


class ScriptSectionInput(BaseModel):
    """One section of the stage 7 script, carried in its canonical order.

    SPEC.md section 4, stage 7 "Produce": the approved script is Promise, Proof,
    Problems, Steps, Context, Action. The domain refuses a missing or out-of-order
    section, so this transport model only carries the kind and content.
    """

    kind: str
    content: str


class VisualProductionPackageInput(BaseModel):
    """The stage 7 visual and video assets produced after script approval.

    The package carries the storyboard, brand treatment, presentation, speaker
    notes, recording, edited and hosted video and player assets; the domain
    refuses a blank artifact so a missing deliverable cannot be represented as a
    completed stage 7 package.
    """

    storyboard: str
    brand_treatment: str
    presentation: str
    speaker_notes: str
    recording: str
    edited_video: str
    hosted_video: str
    player_assets: str


class AmplifierApprovalInput(BaseModel):
    """One version-scoped stage 7 approval, either script or creative.

    Stage 7 has two distinct approvals; the domain stores them separately so
    script approval alone never constitutes final creative acceptance.
    """

    approved_by: str
    intended_use: str
    approved_on: date


class AuthorityAmplifierInput(BaseModel):
    """The reviewed stage 7 Authority Amplifier (SPEC.md section 4, stage 7).

    Carries the amplifier identity, owner, six canonical script sections, the
    proof claim ids the script stands on, the visual production package and the
    two distinct approvals. The domain enforces the canonical script order, the
    grounded proof and the script-before-visuals-before-creative approval
    sequence, so the transport layer only carries the reviewed values.
    """

    amplifier_id: str
    owner: str
    script: list[ScriptSectionInput]
    proof_claim_ids: list[str]
    visuals: VisualProductionPackageInput
    script_approval: AmplifierApprovalInput
    creative_approval: AmplifierApprovalInput


class RecordStageSevenGateRequest(BaseModel):
    """The stage 7 "Authority Amplifier Approved" gate request (SPEC.md section 4).

    The caller supplies the reviewed amplifier, the approved stage 6 message, the
    approved method and production ready offer the amplifier grounds on, the
    known claims that support its proof, the workspace authority registry and the
    decision metadata. The route builds the canonical gate from these through the
    use case; it deliberately accepts no pre-built gate, so the tenant boundary,
    the script-before-visuals-before-creative approval order, approver authority
    and exact-version evidence cannot be bypassed. Stage 7 depends on a passing
    stage 6 decision already in the ledger. The amplifier carries claims because
    the checkpoint requires every proof claim to be a claim of the approved
    method backed by a known, directly sourced knowledge claim.
    """

    workspace_id: str
    authorities: list[ClientAuthorityInput]
    amplifier_package_id: str
    amplifier_version: int
    message: CampaignMessageInput
    offer: OfferVersionInput
    method: MethodVersionInput
    amplifier: AuthorityAmplifierInput
    claims: list[ClaimInput] = Field(default_factory=list)
    stage_owner: str
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


class AssetVersionResponse(BaseModel):
    """One exact asset version pinned or approved for a stage."""

    asset_id: str
    version: int


class MetricMovementResponse(BaseModel):
    """A measured before and after of one approved stage 10 improvement."""

    improvement_id: str
    before: float
    after: float
    measured_on: date


class MetricReportingResponse(BaseModel):
    """One observed metric row of the production view's METRICS dimension.

    The Measurement context owns the metric registry and observations; this is
    its typed projection onto the read model, so a placeholder figure never
    appears as verified progress (SPEC.md section 4).
    """

    metric_id: str
    tenant_id: str
    name: str
    funnel_step: str
    unit: str
    direction: str
    value: float
    window_start: date
    window_end: date
    sample_size: int
    source: str
    recorded_on: date
    basis: str
    movement: MetricMovementResponse | None = None


class StageProductionViewResponse(BaseModel):
    """One stage of the production-manager view (SPEC.md section 4).

    Answers what should exist, what is present and approved, what is missing,
    who is accountable, which dependency blocks work and what approval is next.
    """

    stage_number: int
    name: str
    checkpoint: str
    status: str
    required_asset_kinds: list[str]
    approved_assets: list[AssetVersionResponse]
    missing_asset_kinds: list[str]
    accountable_role: str
    approver_role: str
    dependencies: list[int]
    blocking_dependencies: list[int]
    assigned_owner: str | None = None
    recorded_approver: str | None = None
    due_on: date | None = None
    next_action: str = ""
    blockers: list[str] = []
    entered_at: date | None = None
    is_approved: bool


class PipelineProgressResponse(BaseModel):
    """Verified progress across the pipeline, kept apart from activity."""

    approved_gates: int
    total_gates: int
    verified_post_launch_milestones: int
    activity_entries: int
    verified_progress: int
    gates_remaining: int


class EngagementProductionViewResponse(BaseModel):
    """The production-manager view for one client engagement (SPEC.md section 4).

    The eight reporting dimensions are reported separately: assets,
    checkpoints, owner, dependency, status and due date per stage; milestones
    and metrics at the engagement level. Activity is reported apart from gate
    completion so progress is never shown as tasks checked off.
    """

    engagement: str
    tenant_id: str
    template_version: str
    current_stage_number: int | None
    next_approval_stage_number: int | None
    blocked_stage_numbers: list[int]
    progress: PipelineProgressResponse
    stages: list[StageProductionViewResponse]
    metric_reporting: list[MetricReportingResponse]
