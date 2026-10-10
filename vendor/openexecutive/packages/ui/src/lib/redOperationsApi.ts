// RED operations reads for the ported cockpit screens (K3; SPEC.md section 14
// conditions 2 and 3). Additive file (ADR 0014): the native `/operations/*`
// pages read the same-origin `/red` REST surface the thin client used, so the
// cockpit holds no RED business logic and grants no authority. It approves
// nothing, spends nothing and deploys nothing.

export interface InterventionCard {
  client: string;
  reason: string;
  severity: string;
  subject: string;
  explanation: string;
  evidence: string[];
  owner: string;
  next_action: string;
  due_on: string | null;
  state: string;
  affected_builds: string[];
  resolution_note: string;
}

export interface InterventionList {
  tenant_id: string;
  engagement: string;
  on: string;
  total: number;
  interventions: InterventionCard[];
}

export interface AssetVersion {
  asset_id: string;
  version: number;
}

export interface StageProductionView {
  stage_number: number;
  name: string;
  checkpoint: string;
  status: string;
  required_asset_kinds: string[];
  approved_assets: AssetVersion[];
  missing_asset_kinds: string[];
  accountable_role: string;
  approver_role: string;
  dependencies: number[];
  blocking_dependencies: number[];
  assigned_owner: string | null;
  recorded_approver: string | null;
  due_on: string | null;
  next_action: string;
  blockers: string[];
  entered_at: string | null;
  is_approved: boolean;
}

export interface PipelineProgress {
  approved_gates: number;
  total_gates: number;
  verified_post_launch_milestones: number;
  activity_entries: number;
  verified_progress: number;
  gates_remaining: number;
}

export interface EngagementProductionView {
  engagement: string;
  tenant_id: string;
  template_version: string;
  current_stage_number: number | null;
  next_approval_stage_number: number | null;
  blocked_stage_numbers: number[];
  progress: PipelineProgress;
  stages: StageProductionView[];
}

export interface ApprovalRecord {
  asset_id: string;
  version: number;
  scope: string;
  requested_by: string;
  approver: string;
  outcome: string;
  expires_on: string | null;
  stage_number: number;
  decided_on: string;
}

export interface ApprovalList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  approvals: ApprovalRecord[];
}

// One unit of production work with its lifecycle, dependency refs and blockers
// (K4; SPEC.md sections 3, 4, 7 and 8). Mirrors `BuildObjectResponse` in
// `backend/redops/api/schemas.py`. An active build always carries an owner and a
// next action; `refs` name the assets it depends on and `blockers` name what
// stalls it. The board reads them; the UI recomputes no state rule and can
// transition no build.
export interface BuildObject {
  build_id: string;
  tenant_id: string;
  build_type: string;
  purpose: string;
  audience: string;
  owner: string;
  next_action: string;
  state: string;
  is_active: boolean;
  is_blocked: boolean;
  blockers: string[];
  refs: string[];
}

export interface BuildList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  builds: BuildObject[];
}

// One durable workflow run and its stable append-only event log (K4; SPEC.md
// sections 4, 7 and 8). Mirrors the polling read `GET
// /red/clients/{tenant_id}/workflows/{run_id}` in `backend/redops/api/routes.py`.
// The run pins the exact definition version it started on; `event_id` is stable
// for a given run state and every transition keeps its actor, reason, timestamp,
// old and new status and correlation id. The detail reads these; the UI
// recomputes no transition rule and can advance no run.
export interface WorkflowRunTransition {
  event_id: string;
  actor: string;
  reason: string;
  occurred_at: string;
  old_status: string;
  new_status: string;
  correlation_id: string;
}

export interface WorkflowRunView {
  run_id: string;
  tenant_id: string;
  definition_id: string;
  definition_version: string;
  status: string;
  completed_steps: string[];
  in_progress_step: string | null;
  pending_approval: string | null;
  failure_reason: string | null;
  next_step: string | null;
  event_id: string;
  transitions: WorkflowRunTransition[];
}

// One authorized stage 9 launch QA and its launch checks (K4; SPEC.md sections 4
// and 8). Mirrors `LaunchQAResponse` in `backend/redops/api/schemas.py`. The
// launch readiness screen reads the QA state, each required check's outcome,
// evidence and owner, whether the check is on the critical path, and the
// designated human's pinned traffic authorization. The UI recomputes no gate
// rule and can authorize no traffic.
export interface LaunchQACheck {
  kind: string;
  outcome: string;
  evidence: string;
  owner: string;
  detail: string;
  is_critical_path: boolean;
}

export interface TrafficAuthorization {
  authorized_by: string;
  intended_use: string;
  authorized_on: string;
}

export interface LaunchQA {
  qa_id: string;
  tenant_id: string;
  owner: string;
  designated_authority: string;
  state: string;
  checks: LaunchQACheck[];
  authorization: TrafficAuthorization | null;
  review_reason: string | null;
  is_ready_for_traffic: boolean;
}

export interface LaunchQAList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  launch_qas: LaunchQA[];
}

// One immutable source record and its grounded claims (K5; SPEC.md sections 3, 7
// and 8). Mirrors `SourceRecordResponse`, `ClaimResponse` and their list
// envelopes in `backend/redops/api/schemas.py`. The explorer reads them; it
// recomputes no claim rule and can set no provenance.
export interface SourceRecord {
  source_id: string;
  tenant_id: string;
  locator: string;
  checksum: string;
  captured_on: string;
  access_rule: string;
}

export interface SourceRecordList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  sources: SourceRecord[];
}

export interface ClaimCitation {
  source_id: string;
  checksum: string;
  location: string;
}

export interface Claim {
  claim_id: string;
  tenant_id: string;
  statement: string;
  provenance: string;
  confidence_note: string;
  is_directly_sourced: boolean;
  citations: ClaimCitation[];
}

export interface ClaimList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  claims: Claim[];
}

// One approved method version and its pinned stage 4 transformation structure
// (K5; SPEC.md sections 3, 4, 7 and 8). Mirrors `MethodVersionResponse` and its
// nested `SignatureSolutionResponse` in `backend/redops/api/schemas.py`. The
// transformation map reads the exact approved structure; the UI recomputes no
// stage rule and can approve nothing.
export interface SignatureStep {
  step_id: string;
  tenant_id: string;
  name: string;
  starting_state: string;
  final_state: string;
  inputs: string[];
  actions: string[];
  outputs: string[];
}

export interface TransformationPhase {
  phase_id: string;
  tenant_id: string;
  name: string;
  steps: SignatureStep[];
}

export interface SignatureSolution {
  solution_id: string;
  tenant_id: string;
  transformation_map: string;
  process_inventory: string[];
  phases: TransformationPhase[];
  starting_state: string;
  final_state: string;
  narrative: string;
  visual: string;
}

export interface MethodVersion {
  method_id: string;
  tenant_id: string;
  parent_method: string;
  semantic_version: string;
  stages: string[];
  currency: string;
  claims: string[];
  is_approved: boolean;
  approved_by: string | null;
  intended_use: string | null;
  approved_on: string | null;
  primary_currency: string | null;
  diagnostic_model_id: string | null;
  signature_solution_id: string | null;
  signature_solution: SignatureSolution | null;
}

export interface MethodVersionList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  methods: MethodVersion[];
}

// One production ready offer version and its pinned method dependencies (K5;
// SPEC.md sections 3, 5, 7 and 8). The stage 5 shape is informed by canon files
// 11 and 12 (Perfect Product, Product Matrix, pricing by outcome). Mirrors
// `OfferVersionResponse` in `backend/redops/api/schemas.py`. The editor reads the
// exact approved offer and its pinned method references; the UI recomputes no
// readiness rule and can approve nothing.
export interface MethodReference {
  method_id: string;
  version: string;
  intended_use: string;
}

export interface OfferVersion {
  offer_id: string;
  tenant_id: string;
  audience: string;
  promise: string;
  eligibility: string;
  price_hypothesis: string;
  owner: string;
  state: string;
  is_production_ready: boolean;
  method_refs: MethodReference[];
  review_reason: string | null;
}

export interface OfferList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  offers: OfferVersion[];
}

// One authorized journey release and its routing (K5; SPEC.md sections 3, 7 and
// 8). The stage 8 routing shape is informed by canon files 13, 14, 21 and 22
// (CAC funnel, funnel template, page set, swimlanes). Mirrors
// `JourneyReleaseResponse` in `backend/redops/api/schemas.py`. The release pins
// exact asset versions and is only surfaced after a signed, authorized stage 9
// launch QA, so the editor shows routing but can authorize no traffic.
export interface JourneyReleaseAsset {
  asset_id: string;
  tenant_id: string;
  kind: string;
  version: number;
}

export interface JourneyRelease {
  release_id: string;
  tenant_id: string;
  qa_id: string;
  assets: JourneyReleaseAsset[];
  routing: string;
  configuration_digest: string;
  rollback_ref: string;
  released_kinds: string[];
  is_signed_ready: boolean;
  is_authorized: boolean;
}

export interface JourneyReleaseList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  releases: JourneyRelease[];
}

// The client workspace authority registry (K6; SPEC.md sections 3, 7 and 8).
// Mirrors `ClientWorkspaceResponse`/`ClientWorkspaceListResponse` in
// `backend/redops/api/schemas.py`. The authority settings screen reads the
// registry the shared context already loaded; the UI invents no authority role
// and grants no authority.
export interface ClientAuthority {
  actor: string;
  authority: string;
}

export interface ClientWorkspace {
  workspace_id: string;
  tenant_id: string;
  lifecycle: string;
  authorities: ClientAuthority[];
  children: string[];
}

export interface ClientWorkspaceList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  workspaces: ClientWorkspace[];
}

// The stage 10 measurement read (K6; SPEC.md sections 3, 4 and 8). Mirrors
// `MeasurementRecordResponse`/`MeasurementListResponse` in
// `backend/redops/api/schemas.py`. An observation pins the exact metric version,
// the closed window, the basis and the source; `is_observed` is false for a
// placeholder, so a placeholder never reads as a measured result.
export interface MetricDefinitionSummary {
  metric_id: string;
  tenant_id: string;
  name: string;
  funnel_step: string;
  unit: string;
  direction: string;
  version: number;
}

export interface MetricMovement {
  improvement_id: string;
  before: number;
  after: number;
  measured_on: string;
}

export interface MetricReporting {
  metric_id: string;
  tenant_id: string;
  name: string;
  funnel_step: string;
  unit: string;
  direction: string;
  value: number;
  window_start: string;
  window_end: string;
  sample_size: number;
  source: string;
  recorded_on: string;
  basis: string;
  movement: MetricMovement | null;
}

export interface MeasurementRecord {
  record_id: string;
  tenant_id: string;
  metric: MetricDefinitionSummary;
  value: number;
  window_start: string;
  window_end: string;
  basis: string;
  source: string;
  sample_size: number;
  recorded_on: string;
  is_observed: boolean;
}

export interface MeasurementList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  records: MeasurementRecord[];
}

// The portfolio opportunity register read (K6; SPEC.md sections 3, 7 and 8).
// Mirrors `OpportunityResponse`/`OpportunityListResponse` in
// `backend/redops/api/schemas.py`. An opportunity is a proposal grounded on the
// exact same-tenant `(asset_id, kind, version)` of the approved stage asset it
// expands, so the source is always shown pinned; `state` is `proposed` until a
// human investment authority acts, and the register never stores an approved
// investment.
export interface PortfolioOpportunity {
  tenant_id: string;
  opportunity_id: string;
  title: string;
  kind: string;
  source_asset_id: string;
  source_kind: string;
  source_version: number;
  investment_case: string;
  expected_outcome: string;
  owner: string;
  next_action: string;
  captured_on: string;
  state: string;
}

export interface OpportunityList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  opportunities: PortfolioOpportunity[];
}

function redApiBase(): string {
  return process.env.NEXT_PUBLIC_RED_API_BASE ?? "";
}

async function redGet<T>(path: string, params: Record<string, string>): Promise<T> {
  const query = new URLSearchParams(params);
  const res = await fetch(`${redApiBase()}${path}?${query.toString()}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`RED request failed (${res.status})`);
  }
  return (await res.json()) as T;
}

// The write twin of `redGet`: same base and path handling with a JSON body. A
// failure raises with the backend's own error detail when it provides one (a
// FastAPI string detail or the `{error, message}` dict the domain refusals
// use), so a caller renders the refusal verbatim and never re-derives it.
async function redPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${redApiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(await redRequestError(res));
  }
  return (await res.json()) as T;
}

async function redRequestError(res: Response): Promise<string> {
  try {
    const parsed = (await res.json()) as { detail?: unknown };
    const detail = parsed?.detail;
    if (typeof detail === "string" && detail !== "") return detail;
    if (detail !== null && typeof detail === "object") {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === "string" && message !== "") return message;
    }
  } catch {
    // Not a JSON error body; fall through to the status-only message.
  }
  return `RED request failed (${res.status})`;
}

// The command center read (SPEC.md sections 7 and 8). Tenant, engagement and the
// evaluation date are all required by the backend, which refuses an unscoped
// query; the route is read-only, so listing a card authorizes no action.
export function listInterventions(
  tenantId: string,
  engagement: string,
  on: string,
): Promise<InterventionList> {
  return redGet<InterventionList>("/red/interventions", {
    tenant_id: tenantId,
    engagement,
    on,
  });
}

// The client workspace overview read (SPEC.md sections 4 and 8). Tenant and
// engagement are the path authority and `on` is required by the backend, which
// evaluates prerequisite expiry against a fixed instant.
export function getProductionView(
  tenantId: string,
  engagement: string,
  on: string,
): Promise<EngagementProductionView> {
  return redGet<EngagementProductionView>(
    `/red/clients/${encodeURIComponent(tenantId)}/engagements/${encodeURIComponent(
      engagement,
    )}/production-view`,
    { on },
  );
}

// The approval inbox read (SPEC.md sections 3, 4 and 8). The tenant is a
// required query scope and the route is read-only; an approval is pinned to an
// exact asset version by the passing gate decision, so listing one cannot itself
// authorize production or traffic.
export function listApprovals(tenantId: string): Promise<ApprovalList> {
  return redGet<ApprovalList>("/red/approvals", { tenant_id: tenantId });
}

// The build board read (K4; SPEC.md sections 3, 4, 7 and 8). The tenant is a
// required query scope and the route is read-only; a build is born Identified as
// a proposal and only a later transition changes its state, so the board reads
// the work items and can transition none.
export function listBuilds(tenantId: string): Promise<BuildList> {
  return redGet<BuildList>("/red/builds", { tenant_id: tenantId });
}

// The workflow run detail read (K4; SPEC.md sections 4, 7 and 8). The path
// tenant, not any request value, is the authoritative client scope, so another
// client's run is served as 404 rather than leaked. The route is read-only; the
// detail polls the run and can advance none.
export function getWorkflowRun(
  tenantId: string,
  runId: string,
): Promise<WorkflowRunView> {
  return redGet<WorkflowRunView>(
    `/red/clients/${encodeURIComponent(tenantId)}/workflows/${encodeURIComponent(
      runId,
    )}`,
    {},
  );
}

// The launch readiness read (K4; SPEC.md sections 4, 7 and 8). The tenant is a
// required query scope and the route is read-only; a QA is authorized through
// its stage 9 gate, so listing one never authorizes traffic.
export function listLaunchQAs(tenantId: string): Promise<LaunchQAList> {
  return redGet<LaunchQAList>("/red/launch-qas", { tenant_id: tenantId });
}

// The source and claim explorer reads (K5; SPEC.md sections 3, 7 and 8). The
// tenant is the source path authority and the required claim query scope; both
// reads refuse an unscoped query, so a client never sees another's material.
export function listSources(tenantId: string): Promise<SourceRecordList> {
  return redGet<SourceRecordList>(
    `/red/clients/${encodeURIComponent(tenantId)}/sources`,
    {},
  );
}

export function listClaims(tenantId: string): Promise<ClaimList> {
  return redGet<ClaimList>("/red/claims", { tenant_id: tenantId });
}

// The transformation map read (K5; SPEC.md sections 3, 4, 7 and 8). The tenant
// is a required query scope and the route is read-only; a method is born
// approved through its stage gate, so the screen can read the pinned structure
// but can write and approve nothing.
export function listMethods(tenantId: string): Promise<MethodVersionList> {
  return redGet<MethodVersionList>("/red/methods", { tenant_id: tenantId });
}

// The offer and journey editor reads (K5; SPEC.md sections 3, 5, 7, 8 and 9).
// The tenant is the required query scope on both routes and both reads are
// read-only, so a client never sees another's offers or releases and the screen
// can approve no offer and authorize no traffic.
export function listOffers(tenantId: string): Promise<OfferList> {
  return redGet<OfferList>("/red/offers", { tenant_id: tenantId });
}

export function listJourneys(tenantId: string): Promise<JourneyReleaseList> {
  return redGet<JourneyReleaseList>("/red/journeys", { tenant_id: tenantId });
}

// The performance review read (K6; SPEC.md sections 3, 4 and 8). The tenant is a
// required query scope; the route is read-only and a recorded observation is not
// a gate, so reading the registry changes no metric and starts no optimization.
export function listMeasurements(tenantId: string): Promise<MeasurementList> {
  return redGet<MeasurementList>("/red/measurements", { tenant_id: tenantId });
}

// The portfolio opportunity register read (K6; SPEC.md sections 3, 7 and 8). The
// tenant is a required query scope and the route is read-only; the register
// holds proposals only, so listing one approves no investment, spend or launch.
export function listOpportunities(tenantId: string): Promise<OpportunityList> {
  return redGet<OpportunityList>("/red/opportunities", { tenant_id: tenantId });
}

// One durable workflow run waiting at a RED approval gate (K12; SPEC.md section
// 14 condition 8). Mirrors the workflow-run read payload: the run pins the exact
// definition version it started on and names the gate it is waiting at, so the
// approval experience shows the pending gate with its exact version.
export interface AwaitingApprovalRun {
  run_id: string;
  tenant_id: string;
  definition_id: string;
  definition_version: string;
  status: string;
  completed_steps: string[];
  in_progress_step: string | null;
  pending_approval: string | null;
  failure_reason: string | null;
  next_step: string | null;
  event_id: string;
  transitions: WorkflowRunTransition[];
}

export interface AwaitingApprovalList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  runs: AwaitingApprovalRun[];
}

// The pending gate approval read (K12). The tenant is a required query scope
// and the route is read-only: listing a waiting run approves nothing, so the
// approval experience can surface the pending gate without granting authority.
export function listAwaitingApprovals(
  tenantId: string,
): Promise<AwaitingApprovalList> {
  return redGet<AwaitingApprovalList>(
    `/red/clients/${encodeURIComponent(tenantId)}/workflows/awaiting-approval`,
    {},
  );
}

// One stored campaign message with its full stage 6 content (asset review and
// approval spec sections 4.1 and 5). Mirrors the tenant-scoped list route
// `GET /red/messages`. The fields are tolerant: the backend may omit any
// optional content field and the panel renders only what an aggregate carries.
export interface MessageRecord {
  message_id: string;
  owner?: string | null;
  avatar?: string | null;
  currency?: string | null;
  problem?: string | null;
  promise?: string | null;
  cta?: string | null;
  problem_hierarchy?: string[];
  desired_outcome?: string | null;
  proof_objections?: string[];
  story?: string | null;
  method_explanation?: string | null;
  lead_magnet?: string | null;
  hook?: string | null;
  angles?: string[];
  landing_message?: string | null;
  authority_amplifier_outline?: string | null;
  product_offer_id?: string | null;
  is_approved?: boolean | null;
}

export interface MessageList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  messages: MessageRecord[];
}

// One stored authority amplifier with its script sections and visual refs
// (asset review and approval spec sections 4.1 and 5). Mirrors the
// tenant-scoped list route `GET /red/amplifiers`.
export interface AmplifierScriptSection {
  kind: string;
  content: string;
}

export interface AmplifierRecord {
  amplifier_id: string;
  method_ref?: string | null;
  offer_ref?: string | null;
  script_sections?: AmplifierScriptSection[];
  storyboard?: string | null;
  recording?: string | null;
  edited_video?: string | null;
  hosted_video?: string | null;
  player_assets?: string[];
  is_approved?: boolean | null;
}

export interface AmplifierList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  amplifiers: AmplifierRecord[];
}

// One stored funnel integration with its asset references and routing (asset
// review and approval spec sections 4.1 and 5). Mirrors the tenant-scoped list
// route `GET /red/funnels`.
export interface FunnelAssetRef {
  asset_id: string;
  kind?: string | null;
  version?: number | null;
}

export interface FunnelRecord {
  funnel_id: string;
  asset_refs?: FunnelAssetRef[];
  routing?: string | null;
  is_released?: boolean | null;
  is_authorized?: boolean | null;
  is_approved?: boolean | null;
}

export interface FunnelList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  funnels: FunnelRecord[];
}

// One append-only governance decision read from the durable ledger (asset
// review and approval spec section 3.1). Mirrors `DecisionRecordResponse` in
// `backend/redops/api/schemas.py`; `checkpoint_evidence` is optional because a
// decision may predate the evidence field.
export interface DecisionRecord {
  stage_number: number;
  checkpoint: string;
  disposition: string;
  reviewer: string;
  scope: string;
  rationale: string;
  checkpoint_evidence?: string | null;
  decided_on?: string | null;
  required_assets: AssetVersion[];
}

export interface DecisionList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  decisions: DecisionRecord[];
}

// The campaign message read (asset review and approval spec section 4.1). The
// tenant is a required query scope and the route is read-only; listing the
// stored messages approves nothing.
export function listMessages(tenantId: string): Promise<MessageList> {
  return redGet<MessageList>("/red/messages", { tenant_id: tenantId });
}

// The authority amplifier read (asset review and approval spec section 4.1).
// The tenant is a required query scope and the route is read-only; listing the
// stored amplifiers approves nothing.
export function listAmplifiers(tenantId: string): Promise<AmplifierList> {
  return redGet<AmplifierList>("/red/amplifiers", { tenant_id: tenantId });
}

// The funnel integration read (asset review and approval spec section 4.1).
// The tenant is a required query scope and the route is read-only; listing the
// stored funnels releases nothing.
export function listFunnels(tenantId: string): Promise<FunnelList> {
  return redGet<FunnelList>("/red/funnels", { tenant_id: tenantId });
}

// The governance decision history read (asset review and approval spec section
// 3.1). The tenant is a required query scope and the route is read-only; the
// ledger is append-only, so reading it changes no decision.
export function listDecisions(tenantId: string): Promise<DecisionList> {
  return redGet<DecisionList>("/red/decisions", { tenant_id: tenantId });
}

// The stage gate schema read (asset review and approval spec section 4.2). The
// schema describes exactly the body `POST /red/clients/{t}/stages/{n}/gate`
// accepts, so the form renders it and re-implements no validation rule.
export type GateSchema = Record<string, unknown>;

export function getGateSchema(stageNumber: number): Promise<GateSchema> {
  return redGet<GateSchema>(`/red/stages/${stageNumber}/gate-schema`, {});
}

// The workflow approval write (asset review and approval spec section 3.2).
// The backend validates the actor against the workspace authority registry and
// refuses a run whose gate has no passing decision; the UI renders whatever
// error the backend returns and re-implements no approval rule.
export function approveWorkflowRun(
  tenantId: string,
  runId: string,
  actor: string,
  reason: string,
): Promise<unknown> {
  return redPost(
    `/red/clients/${encodeURIComponent(tenantId)}/workflows/${encodeURIComponent(
      runId,
    )}/approval`,
    { actor, reason },
  );
}

// The stage gate write (asset review and approval spec section 3.3). The body
// is the stage's typed gate request, assembled by the schema-driven form; the
// backend remains the sole enforcer of prerequisites and authority.
export function recordStageGate(
  tenantId: string,
  stageNumber: number,
  body: Record<string, unknown>,
): Promise<unknown> {
  return redPost(
    `/red/clients/${encodeURIComponent(tenantId)}/stages/${stageNumber}/gate`,
    body,
  );
}

// The content source a pinned asset kind resolves to (asset review and
// approval spec section 5), derived from the canonical stage template kinds in
// `backend/redops/contexts/governance/domain/templates.py`. Kinds absent from
// the map — the stage 0 intake, stage 1 diagnose, stage 2 position and stage 4
// IP-architecture kinds, plus any unlisted kind — have no stored content
// source and render provenance only. `swimlanes-plan` appears in both the
// stage 8 and stage 9 template lists; the stage 8 funnel source wins, matching
// template order.
export type AssetContentSource =
  | "methods"
  | "offers"
  | "messages"
  | "amplifiers"
  | "funnels"
  | "launch-qas"
  | "measurements";

export const ASSET_CONTENT_SOURCES: Readonly<
  Record<string, AssetContentSource>
> = {
  // Stage 3 Model kinds → /red/methods.
  "profit-pyramid-levels": "methods",
  "observable-measures": "methods",
  "level-symptoms": "methods",
  "level-behaviors": "methods",
  "level-problems": "methods",
  progression: "methods",
  "qualification-logic": "methods",
  "diagnostic-model-name": "methods",
  "diagnostic-model-visual": "methods",
  "diagnostic-model-copy": "methods",
  // Stage 5 Productize kinds → /red/offers.
  "delivery-model": "offers",
  duration: "offers",
  modules: "offers",
  responsibilities: "offers",
  "support-cadence": "offers",
  "stage-deliverables": "offers",
  "outcome-measures": "offers",
  "pricing-payments": "offers",
  scope: "offers",
  "guarantee-decision": "offers",
  eligibility: "offers",
  "offer-stack": "offers",
  "product-program": "offers",
  // Stage 6 Message kinds → /red/messages.
  promise: "messages",
  "problem-hierarchy": "messages",
  "desired-outcome": "messages",
  "proof-objections": "messages",
  story: "messages",
  "method-explanation": "messages",
  cta: "messages",
  "lead-magnet": "messages",
  hook: "messages",
  angles: "messages",
  "landing-message": "messages",
  "authority-amplifier-outline": "messages",
  "content-roadmap": "messages",
  "content-crusher": "messages",
  "content-plan": "messages",
  // Stage 7 Produce kinds → /red/amplifiers.
  "authority-amplifier-script": "amplifiers",
  "aa-storyboard": "amplifiers",
  "brand-treatment": "amplifiers",
  "aa-presentation": "amplifiers",
  "aa-speaker-notes": "amplifiers",
  "aa-recording": "amplifiers",
  "aa-edited-video": "amplifiers",
  "aa-hosted-video": "amplifiers",
  "aa-player-assets": "amplifiers",
  // Stage 8 Integrate kinds → /red/funnels.
  "campaign-architecture": "funnels",
  pages: "funnels",
  forms: "funnels",
  qualification: "funnels",
  booking: "funnels",
  sequences: "funnels",
  crm: "funnels",
  tags: "funnels",
  automation: "funnels",
  analytics: "funnels",
  tracking: "funnels",
  "sales-handoff": "funnels",
  sops: "funnels",
  "swimlanes-plan": "funnels",
  // Stage 9 QA kinds → /red/launch-qas.
  "recorded-message": "launch-qas",
  "technical-tests": "launch-qas",
  "commercial-tests": "launch-qas",
  "qa-forms": "launch-qas",
  "qa-crm": "launch-qas",
  "qa-email": "launch-qas",
  "qa-automation": "launch-qas",
  "qa-booking": "launch-qas",
  "qa-tracking": "launch-qas",
  "qa-payment": "launch-qas",
  "qa-handoff": "launch-qas",
  "client-approval": "launch-qas",
  "budget-approval": "launch-qas",
  "creative-approval": "launch-qas",
  "launch-dashboard": "launch-qas",
  "launch-decision": "launch-qas",
  "compliance-package": "launch-qas",
  "enrollment-plan": "launch-qas",
  "client-process": "launch-qas",
  // Stage 10 Launch kinds → /red/measurements.
  "live-campaign": "measurements",
  "spend-records": "measurements",
  "lead-records": "measurements",
  "conversion-measures": "measurements",
  "engagement-measures": "measurements",
  applications: "measurements",
  bookings: "measurements",
  shows: "measurements",
  closes: "measurements",
  "acquisition-cost": "measurements",
  attribution: "measurements",
  "issue-log": "measurements",
  "nurture-plan": "measurements",
};

export function contentSourceForKind(kind: string): AssetContentSource | null {
  return ASSET_CONTENT_SOURCES[kind] ?? null;
}

// The stored content entities for one asset kind's mapped source (asset review
// and approval spec sections 3.1 and 5). The panel renders the matching
// group's entities and marks the ones whose approval state is approved.
export type AssetContentEntry =
  | { source: "methods"; methods: MethodVersion[] }
  | { source: "offers"; offers: OfferVersion[] }
  | { source: "messages"; messages: MessageRecord[] }
  | { source: "amplifiers"; amplifiers: AmplifierRecord[] }
  | { source: "funnels"; funnels: FunnelRecord[] }
  | { source: "launch-qas"; launch_qas: LaunchQA[] }
  | { source: "measurements"; records: MeasurementRecord[] };

// The tenant's stored entities for one mapped content source, reusing the
// existing list getters; the panel shows the group, not a single pinned entity,
// because gate decisions record kinds rather than content entity ids.
export async function listAssetContent(
  tenantId: string,
  source: AssetContentSource,
): Promise<AssetContentEntry> {
  switch (source) {
    case "methods":
      return { source, methods: (await listMethods(tenantId)).methods };
    case "offers":
      return { source, offers: (await listOffers(tenantId)).offers };
    case "messages":
      return { source, messages: (await listMessages(tenantId)).messages };
    case "amplifiers":
      return { source, amplifiers: (await listAmplifiers(tenantId)).amplifiers };
    case "funnels":
      return { source, funnels: (await listFunnels(tenantId)).funnels };
    case "launch-qas":
      return { source, launch_qas: (await listLaunchQAs(tenantId)).launch_qas };
    case "measurements":
      return { source, records: (await listMeasurements(tenantId)).records };
  }
}
