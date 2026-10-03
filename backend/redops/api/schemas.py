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

    The caller supplies the registered workspace id, the real intake assets,
    the supporting claims and the decision metadata. The route resolves the
    workspace and its authority registry from the durable store, so the request
    carries no authorities and cannot substitute a caller supplied registry for
    the persisted one (SPEC.md sections 3, 4 and 11). It deliberately accepts no
    pre-built gate, so owner authority and sourced evidence cannot be bypassed.
    """

    workspace_id: str
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


class AwarenessMapInput(BaseModel):
    """The stage 1 typed market awareness map (canon file 04).

    SPEC.md section 4 requires stage 1 to pin an awareness asset and section 12.5
    records the market awareness levels as canon-informed. The typed
    ``MarketAwarenessMap`` carries the research evidence and message requirements
    the avatar's free-text awareness note does not, so the route accepts this
    shape and the domain projects it as the ``awareness-map`` gate kind.
    """

    map_id: str
    version: int
    primary_level: str
    research_evidence: list[str]
    message_requirements: list[str]
    retarget_level: str | None = None


class InterestSignalInput(BaseModel):
    """One canon interest signal an audience sizing narrows on (canon file 02)."""

    kind: str
    value: str


class AudienceDefinitionInput(BaseModel):
    """The location, age, gender and interests that define a sized audience."""

    location: str
    age: str
    gender: str
    interests: list[InterestSignalInput]


class AudienceReachEstimateInput(BaseModel):
    """The stage 1 typed audience reach estimate (canon files 02 and 03).

    SPEC.md section 12.3 maps audience sizing research onto stage 1 "Diagnose".
    The typed ``AudienceReachEstimate`` carries the research platform, the sized
    audience, the reachable size, the source note and the capture date, so the
    route accepts this shape and the domain projects it as the
    ``audience-reach-estimate`` gate kind.
    """

    estimate_id: str
    version: int
    owner: str
    platform: str
    audience: AudienceDefinitionInput
    estimated_reach: int
    source_note: str
    captured_on: date


class TargetMarketCandidateInput(BaseModel):
    """One candidate target market judged by the canon match criteria (canon 00)."""

    market_id: str
    name: str
    passion: str
    problem: str
    profit: str
    reachability: str
    pathway: str


class TargetMarketMatchmakerInput(BaseModel):
    """The stage 1 typed target market matchmaker (canon file 00).

    SPEC.md section 12.5 records the positioning and decision tools as a canon
    gap and the owner decision makes a canon-informed asset already implemented a
    required kind of its target stage. The typed ``TargetMarketMatchmaker`` narrows
    two or more candidate markets to the one to serve now, so the route accepts
    this shape and the domain projects it as the ``target-market-match`` gate kind.
    RED reuses the stage 1 researched awareness map for the chosen market rather
    than accepting a second, divergent copy (an intentional narrowing of the canon,
    SPEC.md section 12.4).
    """

    matchmaker_id: str
    version: int
    candidates: list[TargetMarketCandidateInput]
    selected_market_id: str


class RecordStageOneGateRequest(BaseModel):
    """The stage 1 "Avatar Locked" gate request (SPEC.md section 4).

    The caller supplies the registered workspace id, the reviewed diagnosis
    values, the supporting claims and the decision metadata. The route resolves
    the workspace and its authority registry from the durable store, so the
    request carries no authorities and cannot substitute a caller supplied
    registry for the persisted one (SPEC.md sections 3, 4 and 11). It deliberately
    accepts no pre-built gate, so approver authority and sourced evidence cannot
    be bypassed. Stage 1 depends on a passing stage 0 decision already in the
    ledger.
    """

    workspace_id: str
    diagnosis_package_id: str
    avatar: AvatarProfileInput
    business_snapshot: BusinessSnapshotInput
    offer_funnel_audit: OfferFunnelAuditInput
    awareness_map: AwarenessMapInput
    audience_reach_estimate: AudienceReachEstimateInput
    target_market_match: TargetMarketMatchmakerInput
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

    The caller supplies the reviewed positioning values and the decision
    metadata; the authority registry is resolved from the durable workspace
    store, never the body. The route builds the canonical gate from these through
    the use case; it deliberately accepts no pre-built gate, so approver authority
    and exact-version evidence cannot be bypassed. Stage 2 depends on a passing
    stage 1 decision already in the ledger. The currency inventory carries no
    claims: the "Currency Locked" checkpoint turns on the primary currency's
    internal specificity, not external customer evidence.
    """

    workspace_id: str
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

    The caller supplies the reviewed model values and the decision metadata; the
    authority registry is resolved from the durable workspace store, never the
    body. The route builds the canonical gate from these through the use case; it
    deliberately accepts no pre-built gate, so approver authority and
    exact-version evidence cannot be bypassed. Stage 3 depends on a passing
    stage 2 decision already in the ledger. The model carries no claims: the
    "Diagnostic Model Approved" checkpoint turns on adjacent-level observable
    distinguishability, which the domain enforces, rather than external customer
    evidence.
    """

    workspace_id: str
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


class TransformationsInput(BaseModel):
    """The reviewed stage 4 thirteen transformations and their exact version.

    SPEC.md sections 4 and 12.5 make the canon-informed
    ``ThirteenTransformations`` (canon files 09 and 10) a required stage 4 asset.
    The caller supplies the asset identity, the exact version and the Million
    Dollar Message the overall shift is titled with; the route derives the three
    phase shifts and nine step shifts from the already-reviewed solution's own
    states, so every shift moves the client between the solution's real points A
    and B. The domain enforces the thirteen-shift coverage, the titling and the
    solution grounding, so the transport layer only carries the values and the
    exact version.
    """

    transformations_id: str
    version: int
    million_dollar_message: str


class RecordStageFourGateRequest(BaseModel):
    """The stage 4 "IP Architecture Locked" gate request (SPEC.md section 4).

    The caller supplies the reviewed transformation values and the decision
    metadata; the authority registry is resolved from the durable workspace
    store, never the body. The route builds the canonical gate from these through
    the use case; it deliberately accepts no pre-built gate, so approver authority
    and exact-version evidence cannot be bypassed. Stage 4 depends on a passing
    stage 3 decision already in the ledger. The solution carries no claims: the
    "IP Architecture Locked" checkpoint turns on the coherence and continuity of
    the reviewed transformation, which the domain enforces at construction, rather
    than external customer evidence.
    """

    workspace_id: str
    signature_package_id: str
    solution: SignatureSolutionInput
    transformations: TransformationsInput
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


class ProductModuleInput(BaseModel):
    """One stage 5 product program module for a named method step (canon 11, 12).

    The canon's Perfect Product training breaks the signature solution into one
    module per step, each naming the outcome it produces and the deliverable it
    leaves with the client (SPEC.md section 12.3). The domain refuses a module
    that leaves its step, outcome or deliverable unstated, so the transport layer
    only carries the values.
    """

    module_id: str
    signature_step: str
    position: int
    outcome: str
    deliverable: str


class ProductProgramInput(BaseModel):
    """The reviewed stage 5 product program and its exact version (canon 11, 12).

    SPEC.md sections 4 and 12.5 make the canon-informed ``ProductProgram`` a
    required stage 5 asset. The program chooses one of the canon's seven product
    matrix models, prices on outcomes rather than time and materials, runs six to
    twelve weeks on the Monday and Thursday cadence, and delivers each named
    signature solution step as one module. The domain enforces every rule and the
    grounding on the same stage 5 signature solution, so the transport layer only
    carries the values and the exact version.
    """

    program_id: str
    version: int
    owner: str
    model: str
    pricing_basis: str
    duration_weeks: int
    cadence: str
    modules: list[ProductModuleInput]


class RecordStageFiveGateRequest(BaseModel):
    """The stage 5 "Offer Locked" gate request (SPEC.md section 4).

    The caller supplies the reviewed delivery values, the reviewed product
    program and the decision metadata; the authority registry is resolved from
    the durable workspace store, never the body. The route builds the canonical
    gate from these through the use case; it deliberately accepts no pre-built
    gate, so approver authority and exact-version evidence cannot be bypassed.
    Stage 5 depends on a passing stage 4 decision already in the ledger. The
    delivery carries no claims: the "Offer Locked" checkpoint turns on every
    method step carrying an action, actor, deliverable, timing and measure and
    on the typed product program, which the domain enforces at construction,
    rather than external customer evidence.
    """

    workspace_id: str
    offer_package_id: str
    delivery: DeliverySpecificationInput
    product_program: ProductProgramInput
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


class ContentTopicInput(BaseModel):
    """One content roadmap topic mapped from a Signature Solution step.

    SPEC.md sections 4 and 12.5 (canon files 25-28): the stage 6 content roadmap
    maps each step of the locked stage 4 Signature Solution to the FAQs,
    questions and channels the audience asks about it, and every piece follows
    the fixed Authority Amplifier script order. The route derives those script
    beats from the canonical order, so this transport model carries only the
    step, question and channels the domain validates.
    """

    topic_id: str
    name: str
    signature_step: str
    question: str
    channels: list[str]


class ContentRoadmapInput(BaseModel):
    """The stage 6 content roadmap the gate pins as a required asset kind.

    SPEC.md sections 4 and 12.5 (owner decision 2026-10-03): the canon-informed
    content roadmap is a required asset of the stage 6 "Campaign Message
    Approved" gate. The route grounds it on the locked stage 4 Signature
    Solution, so the caller supplies its identity, owner and topics.
    """

    roadmap_id: str
    version: int
    owner: str
    topics: list[ContentTopicInput]


class ContentCrusherInput(BaseModel):
    """The stage 6 content crusher the gate pins as a required asset kind.

    SPEC.md sections 4 and 12.5 (owner decision 2026-10-03; canon files 12, 16 and
    32): the canon-informed content crusher is a required asset of the stage 6
    "Campaign Message Approved" gate. The route grounds it on the same content
    roadmap it builds from the request, so the caller supplies its identity, owner,
    the roadmap topic it outlines, the promise and the outline beats.
    """

    crusher_id: str
    version: int
    owner: str
    topic_id: str
    title: str
    promise_measure: str
    promise_timeline: str
    frustrations: list[str]
    goal: str
    model: str
    metaphor: str
    context: str
    steps: list[str]
    story: str
    choice: str
    action: str


class ContentThemeInput(BaseModel):
    """One currency-aligned theme grouping extracted stage 6 ideas.

    SPEC.md sections 4 and 12.5 (canon files 25, 27 and 28): the Extract motion
    groups the ideas it pulls from the Signature Solution around the one locked
    currency, so a theme carries the currency measure it advances.
    """

    theme_id: str
    name: str
    currency_measure: str


class ContentIdeaInput(BaseModel):
    """One idea the Extract motion pulls from a Signature Solution step.

    The idea names the step it comes from, the typed source it was extracted as,
    the question the audience asks, the theme it groups under and the plan
    channels it feeds.
    """

    idea_id: str
    signature_step: str
    source: str
    prompt: str
    theme_id: str
    channels: list[str]


class ContentPlanInput(BaseModel):
    """The stage 6 Extract content plan the gate pins as a required asset kind.

    SPEC.md sections 4 and 12.5 (owner decision 2026-10-03; canon files 25, 27 and
    28): the canon-informed content plan is a required asset of the stage 6
    "Campaign Message Approved" gate. The route grounds it on the locked stage 4
    Signature Solution and the stage 2 Primary Currency carried here, so the
    caller supplies its identity, owner, the locked currency, its themes and its
    extracted ideas.
    """

    plan_id: str
    version: int
    owner: str
    primary_currency: PrimaryCurrencyInput
    themes: list[ContentThemeInput]
    ideas: list[ContentIdeaInput]


class RecordStageSixGateRequest(BaseModel):
    """The stage 6 "Campaign Message Approved" gate request (SPEC.md section 4).

    The caller supplies the reviewed message, the approved method and production
    ready offer it grounds on and the decision metadata; the authority registry is
    resolved from the durable workspace store, never the body. The route builds
    the canonical gate from these through the use case; it deliberately accepts no
    pre-built gate, so approver authority and exact-version evidence cannot be
    bypassed. Stage 6 depends on a passing stage 5 decision already in the ledger.
    The message carries no claims: the "Campaign Message Approved" checkpoint
    turns on the congruence of avatar, currency, problem, promise, method, product
    and CTA, which the domain enforces, rather than external customer evidence.
    """

    workspace_id: str
    campaign_message_package_id: str
    message_version: int
    message: CampaignMessageInput
    content_roadmap: ContentRoadmapInput
    content_crusher: ContentCrusherInput
    content_plan: ContentPlanInput
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
    known claims that support its proof and the decision metadata; the authority
    registry is resolved from the durable workspace store, never the body. The
    route builds the canonical gate from these through the
    use case; it deliberately accepts no pre-built gate, so the tenant boundary,
    the script-before-visuals-before-creative approval order, approver authority
    and exact-version evidence cannot be bypassed. Stage 7 depends on a passing
    stage 6 decision already in the ledger. The amplifier carries claims because
    the checkpoint requires every proof claim to be a claim of the approved
    method backed by a known, directly sourced knowledge claim.
    """

    workspace_id: str
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


class FunnelAssetPackageInput(BaseModel):
    """The stage 8 required funnel asset package (SPEC.md section 4, stage 8).

    SPEC.md section 4, stage 8 "Integrate": the required asset package is the
    campaign architecture, pages, forms, qualification, booking, sequences, CRM,
    tags, automation, analytics, tracking, sales handoff and SOPs. The domain
    refuses a blank artifact, so a missing deliverable cannot be represented as a
    completed stage 8 funnel.
    """

    campaign_architecture: str
    pages: str
    forms: str
    qualification: str
    booking: str
    sequences: str
    crm: str
    tags: str
    automation: str
    analytics: str
    tracking: str
    sales_handoff: str
    sops: str


class HandoffRecordInput(BaseModel):
    """One capture, engagement or conversion handoff of the stage 8 dry run.

    The "Funnel Complete" checkpoint requires reliable records and ownership, so
    the domain refuses a routed handoff without a record reference and any
    handoff without an owner; the transport model only carries the observed
    values.
    """

    kind: str
    outcome: str
    record_id: str = ""
    owner: str
    detail: str = ""


class ProspectPathDryRunInput(BaseModel):
    """The stage 8 test prospect path dry run (SPEC.md section 4, stage 8).

    Records the capture, engagement and conversion handoffs. The domain refuses
    a repeated handoff kind and completes the funnel only when every canonical
    handoff is present exactly once and routed.
    """

    dry_run_id: str
    handoffs: list[HandoffRecordInput]


class FunnelIntegrationInput(BaseModel):
    """The reviewed stage 8 funnel before its "Funnel Complete" checkpoint.

    Carries the funnel identity, owner, the thirteen required assets and the
    prospect path dry run. The route grounds the funnel on the rebuilt approved
    stage 7 amplifier and drives ``mark_funnel_complete``, so the domain, not the
    transport layer, decides whether the funnel may be pinned as passing
    evidence.
    """

    integration_id: str
    owner: str
    assets: FunnelAssetPackageInput
    dry_run: ProspectPathDryRunInput


class RecordStageEightGateRequest(BaseModel):
    """The stage 8 "Funnel Complete" gate request (SPEC.md section 4).

    The caller supplies the reviewed funnel and its prospect path dry run, the
    approved stage 7 amplifier the funnel grounds on (rebuilt from the approved
    method, production ready offer and approved stage 6 message), the known claims
    that support the amplifier proof and the decision metadata; the authority
    registry is resolved from the durable workspace store, never the body. The
    route builds the canonical gate from these through the use case; it
    deliberately accepts no pre-built gate, so the tenant boundary, approver
    authority, owner authority and exact-version evidence cannot be bypassed.
    Stage 8 depends on a passing stage 7 decision already in the ledger. Unlike
    stages 2 through 6 the funnel checkpoint turns on its own same-tenant prospect
    path, not external customer claims; claims remain only because the amplified
    stage 7 dependency must still be rebuilt and re-proved.
    """

    workspace_id: str
    funnel_package_id: str
    funnel_version: int
    message: CampaignMessageInput
    offer: OfferVersionInput
    method: MethodVersionInput
    amplifier: AuthorityAmplifierInput
    claims: list[ClaimInput] = Field(default_factory=list)
    funnel: FunnelIntegrationInput
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


class QACheckInput(BaseModel):
    """One recorded stage 9 launch QA check (SPEC.md section 4, stage 9).

    Every check carries the evidence that supports its outcome. An excepted check
    must name a human owner; the domain, not the transport layer, refuses an
    unowned exception, a missing check or a failed critical path check.
    """

    kind: str
    outcome: str
    evidence: str
    owner: str = ""
    detail: str = ""


class ComplianceAssetInput(BaseModel):
    """One reviewed stage 9 compliance asset at an exact version."""

    kind: str
    reference: str
    version: int


class ComplianceWaiverInput(BaseModel):
    """A scoped human waiver of an absent stage 9 compliance asset."""

    kind: str
    reason: str
    risk_owner: str
    review_trigger: str
    expires_on: date | None = None


class CompliancePackageInput(BaseModel):
    """The reviewed stage 9 compliance and consent package (SPEC.md 4/9).

    The target markets decide whether consent is applicable; the domain refuses a
    missing launch-blocking asset unless a live scoped waiver covers it, and a
    waiver never makes an absent asset appear present.
    """

    package_id: str
    target_markets: list[str]
    assets: list[ComplianceAssetInput]
    waivers: list[ComplianceWaiverInput] = Field(default_factory=list)


class TrafficAuthorizationInput(BaseModel):
    """A designated human's authorization to begin stage 9 traffic."""

    authorized_by: str
    intended_use: str
    authorized_on: date


class LaunchQAInput(BaseModel):
    """The reviewed stage 9 launch QA before its "Launch Approved" checkpoint.

    Carries the QA identity, owner, designated authority, the complete launch
    check set, the reviewed compliance package and the traffic authorization. The
    route grounds the QA on the rebuilt stage 8 funnel and drives
    ``authorize_traffic``, so the domain decides whether traffic may begin.
    """

    qa_id: str
    owner: str
    designated_authority: str
    checks: list[QACheckInput]
    compliance: CompliancePackageInput
    authorization: TrafficAuthorizationInput


class RecordStageNineGateRequest(BaseModel):
    """The stage 9 "Launch Approved" gate request (SPEC.md section 4).

    The caller supplies the reviewed launch QA and its traffic authorization, the
    approved stage 8 funnel the QA grounds on (rebuilt from the approved method,
    production ready offer, approved stage 6 message and approved stage 7
    amplifier), the known claims that support the amplifier proof and the decision
    metadata; the authority registry is resolved from the durable workspace store,
    never the body. The route builds the canonical
    gate from these through the use case; it deliberately accepts no pre-built
    gate, so the tenant boundary, approver authority, owner authority and
    exact-version evidence cannot be bypassed. Stage 9 depends on a passing stage
    8 decision already in the ledger. The checkpoint requires every critical path
    check to pass, exceptions to have owners, a complete reviewed compliance
    package and the designated human to authorize traffic.
    """

    workspace_id: str
    qa_package_id: str
    qa_version: int
    message: CampaignMessageInput
    offer: OfferVersionInput
    method: MethodVersionInput
    amplifier: AuthorityAmplifierInput
    claims: list[ClaimInput] = Field(default_factory=list)
    funnel: FunnelIntegrationInput
    qa: LaunchQAInput
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


class MilestoneObservationInput(BaseModel):
    """One recorded or pending stage 10 post-launch milestone (SPEC.md 4).

    First qualified traffic and the later lead, appointment and sale are distinct
    milestones; a pending milestone carries no observation. The domain refuses an
    observed milestone without a date and source, and a pending milestone that
    carries an observation.
    """

    kind: str
    status: str
    observed_on: date | None = None
    source: str = ""
    detail: str = ""


class LaunchAssetPackageInput(BaseModel):
    """The stage 10 required asset package (SPEC.md section 4, stage 10).

    Twelve non-blank artifact references: the live campaign, spend and lead
    records, conversion and engagement measures, applications, bookings, shows,
    closes, acquisition cost, attribution and issue log. The domain refuses a
    missing one rather than letting an incomplete launch look complete.
    """

    live_campaign: str
    spend_records: str
    lead_records: str
    conversion_measures: str
    engagement_measures: str
    applications: str
    bookings: str
    shows: str
    closes: str
    acquisition_cost: str
    attribution: str
    issue_log: str


class PerformanceBaselineInput(BaseModel):
    """The reviewed stage 10 baseline before its checkpoint (SPEC.md section 4).

    Carries the baseline identity, owner, the twelve-asset package and the
    observed-or-pending milestone set. The route grounds the baseline on the
    rebuilt ready-for-traffic stage 9 launch QA and drives ``establish``, so the
    ``PerformanceBaselinePolicy`` decides whether the first qualified traffic was
    observed and the milestones are ordered.
    """

    baseline_id: str
    owner: str
    assets: LaunchAssetPackageInput
    milestones: list[MilestoneObservationInput]


class RecordStageTenGateRequest(BaseModel):
    """The stage 10 "Performance Baseline Established" gate request.

    SPEC.md section 4, stage 10. The caller supplies the reviewed baseline and its
    milestone observations, the stage 9 launch QA the baseline grounds on (rebuilt
    from the approved stage 8 funnel and the traffic authorization), the approved
    stages 6-8 assets that the funnel re-grounds on, the known claims that support
    the amplifier proof, the workspace authority registry and the decision
    metadata. The route builds the canonical gate from these through the use case;
    it deliberately accepts no pre-built gate, so the tenant boundary, approver
    authority, owner authority and exact-version evidence cannot be bypassed.
    Stage 10 depends on a passing stage 9 decision already in the ledger. The
    checkpoint requires the stage 9 traffic authorization and first qualified
    traffic observed, with later milestones shown as pending.
    """

    workspace_id: str
    authorities: list[ClientAuthorityInput]
    baseline_package_id: str
    baseline_version: int
    message: CampaignMessageInput
    offer: OfferVersionInput
    method: MethodVersionInput
    amplifier: AuthorityAmplifierInput
    claims: list[ClaimInput] = Field(default_factory=list)
    funnel: FunnelIntegrationInput
    qa: LaunchQAInput
    baseline: PerformanceBaselineInput
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


class CreateClientWorkspaceRequest(BaseModel):
    """Create the stage 0 client workspace tenant root (SPEC.md section 3).

    The caller supplies the opaque workspace id, the client tenant and at least
    one named authority. The domain refuses a blank id or tenant or an empty or
    duplicate authority registry, so the transport carries no rule (SPEC.md
    section 6).
    """

    workspace_id: str
    tenant_id: str
    authorities: list[ClientAuthorityInput]


class ClientAuthorityResponse(BaseModel):
    """A named actor and the authority they hold in a client workspace."""

    actor: str
    authority: str


class ClientWorkspaceResponse(BaseModel):
    """One client workspace's identity, authorities and engagement state."""

    workspace_id: str
    tenant_id: str
    lifecycle: str
    authorities: list[ClientAuthorityResponse]
    children: list[str]


class ClientWorkspaceListResponse(BaseModel):
    """A paginated page of one client tenant's workspaces."""

    tenant_id: str
    total: int
    limit: int
    offset: int
    workspaces: list[ClientWorkspaceResponse]


class CreateSourceRecordRequest(BaseModel):
    """Ingest one immutable source record a claim can cite (SPEC.md section 3).

    The caller supplies the original's locator, checksum, capture time and access
    rule. The domain refuses a missing field so a source cannot be recorded
    without the evidence a future retrieval must verify (SPEC.md section 6).
    """

    source_id: str
    locator: str
    checksum: str
    captured_on: date
    access_rule: str


class SourceRecordResponse(BaseModel):
    """One immutable source record, re-validated through the value object."""

    source_id: str
    tenant_id: str
    locator: str
    checksum: str
    captured_on: date
    access_rule: str


class SourceRecordListResponse(BaseModel):
    """A paginated page of one client tenant's source records."""

    tenant_id: str
    total: int
    limit: int
    offset: int
    sources: list[SourceRecordResponse]
