// Typed thin client over the RED backend REST surface (SPEC.md section 7).
//
// The UI never holds RED business logic (ADR 0007). Every read carries the
// tenant explicitly, because the backend refuses an unscoped query (SPEC.md
// sections 3 and 9). This client is the seam Q33-Q45 use; it adds no authority
// of its own and cannot approve or release anything.

export const RED_API_BASE = process.env.NEXT_PUBLIC_RED_API_BASE ?? "";

export class RedApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, body: unknown, message?: string) {
    super(message ?? `RED API request failed with status ${status}`);
    this.name = "RedApiError";
    this.status = status;
    this.body = body;
  }
}

export type QueryValue = string | number | boolean | undefined | null;

export interface RedApiClientOptions {
  baseUrl?: string;
  fetcher?: typeof fetch;
}

export class RedApiClient {
  private readonly baseUrl: string;
  private readonly fetcher: typeof fetch;

  constructor(options: RedApiClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? RED_API_BASE;
    this.fetcher = options.fetcher ?? fetch;
  }

  async get<T>(path: string, params: Record<string, QueryValue> = {}): Promise<T> {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        query.set(key, String(value));
      }
    }
    const suffix = query.size > 0 ? `?${query.toString()}` : "";
    return this.request<T>(`${path}${suffix}`, { method: "GET" });
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const response = await this.fetcher(url, { ...init, cache: "no-store" });
    const text = await response.text();
    const payload = text ? safeJson(text) : undefined;
    if (!response.ok) {
      throw new RedApiError(response.status, payload);
    }
    return payload as T;
  }
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export interface ListParams {
  limit?: number;
  offset?: number;
}

export interface ClientSummary {
  id: string;
  tenant_id: string;
}

// One durable workflow run and its stable append-only event log (SPEC.md
// sections 4, 7 and 8; Q40). Mirrors the polling read `GET
// /red/clients/{tenant_id}/workflows/{run_id}` in `backend/redops/api/routes.py`.
// The run pins the exact definition version it started on and reports its
// canonical status, completed prefix, in-progress step, pending approval and
// next step. `event_id` is stable for a given run state, and every transition
// keeps its actor, reason, timestamp, old and new status and correlation id
// (SPEC.md section 4). The detail screen reads these; the UI recomputes no
// transition rule and can advance no run.
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

// One command center card from `GET /red/interventions` (SPEC.md section 7).
// The fields mirror `InterventionResponse` in `backend/redops/api/schemas.py`;
// the UI only reads them and never recomputes the ranking.
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

// One immutable source record and its grounded claims (SPEC.md sections 3, 7, 8
// and 11; Q35). Mirrors `SourceRecordResponse`, `ClaimResponse` and their list
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
// (SPEC.md sections 3, 4, 7 and 8; Q36). Mirrors `MethodVersionResponse` and its
// nested `SignatureSolutionResponse` in `backend/redops/api/schemas.py`. The
// transformation map screen reads the exact approved structure; the UI
// recomputes no stage rule and can approve nothing.
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

// One unit of production work with its lifecycle, dependency refs and blockers
// (SPEC.md sections 3, 4, 7 and 8; Q38). Mirrors `BuildObjectResponse` in
// `backend/redops/api/schemas.py`. The BuildObject is the unit of production
// work; an active build always carries an owner and a next action, and its
// `refs` name the assets or artifacts it depends on while `blockers` name what
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

// One production ready offer version and its pinned method dependencies
// (SPEC.md sections 3, 5, 7 and 8; Q37). The stage 5 shape is informed by canon
// files 11 and 12 (Perfect Product, Product Matrix, pricing by outcome). Mirrors
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

// One authorized journey release and its routing (SPEC.md sections 3, 7 and 8;
// Q37). The stage 8 routing shape is informed by canon files 13, 14, 21 and 22
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

// One version-specific approval from `GET /red/approvals` (SPEC.md sections 3,
// 4, 7 and 8; Q39). Mirrors `ApprovalRecordResponse` in
// `backend/redops/api/schemas.py`. An approval pins exactly one asset version
// and one intended scope; `asset_id` is the pinned asset kind, so the same
// kind re-approved at a later stage yields its version history. The inbox reads
// these; the UI recomputes no approval rule and grants no authority.
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

// The production-manager view one client engagement (SPEC.md sections 4 and 8;
// Q34). Mirrors `EngagementProductionViewResponse` in `backend/redops/api/
// schemas.py`. State, provenance (exact pinned asset versions), dependencies,
// version history and next action all come from the backend; the UI recomputes
// none of it and can approve nothing.
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

export interface EngagementProductionView {
  engagement: string;
  tenant_id: string;
  template_version: string;
  current_stage_number: number | null;
  next_approval_stage_number: number | null;
  blocked_stage_numbers: number[];
  progress: PipelineProgress;
  stages: StageProductionView[];
  metric_reporting: MetricReporting[];
}

// Tenant-scoped reads used by the first screens. Paths match `backend/redops/
// api/routes.py` (router prefix `/red`).
export class RedOperationsApi extends RedApiClient {
  listClients(tenantId: string, params: ListParams = {}): Promise<ClientSummary[]> {
    return this.get<ClientSummary[]>("/red/clients", { tenant_id: tenantId, ...params });
  }

  getWorkflowRun(tenantId: string, runId: string): Promise<WorkflowRunView> {
    return this.get<WorkflowRunView>(
      `/red/clients/${encodeURIComponent(tenantId)}/workflows/${encodeURIComponent(runId)}`,
    );
  }

  // The command center read (SPEC.md sections 7 and 8). Tenant, engagement and
  // the evaluation date are all required by the backend, which refuses an
  // unscoped query.
  listInterventions(
    tenantId: string,
    engagement: string,
    on: string,
  ): Promise<InterventionList> {
    return this.get<InterventionList>("/red/interventions", {
      tenant_id: tenantId,
      engagement,
      on,
    });
  }

  // The client workspace overview read (SPEC.md sections 4 and 8; Q34). Tenant
  // and engagement are the path authority and `on` is required by the backend,
  // which evaluates prerequisite expiry against a fixed instant.
  getProductionView(
    tenantId: string,
    engagement: string,
    on: string,
  ): Promise<EngagementProductionView> {
    return this.get<EngagementProductionView>(
      `/red/clients/${encodeURIComponent(tenantId)}/engagements/${encodeURIComponent(
        engagement,
      )}/production-view`,
      { on },
    );
  }

  // The source and claim explorer reads (SPEC.md sections 3, 7 and 8; Q35).
  // The tenant is the source path authority and the required claim query scope;
  // both reads refuse an unscoped query, so a client never sees another's
  // material.
  listSources(
    tenantId: string,
    params: ListParams = {},
  ): Promise<SourceRecordList> {
    return this.get<SourceRecordList>(
      `/red/clients/${encodeURIComponent(tenantId)}/sources`,
      { ...params },
    );
  }

  listClaims(tenantId: string, params: ListParams = {}): Promise<ClaimList> {
    return this.get<ClaimList>("/red/claims", {
      tenant_id: tenantId,
      ...params,
    });
  }

  // The transformation map read (SPEC.md sections 3, 4, 7 and 8; Q36). The
  // tenant is a required query scope and the route is read-only; a method is
  // born approved through its stage gate, so the screen can read the pinned
  // structure but can write and approve nothing.
  listMethods(
    tenantId: string,
    params: ListParams = {},
  ): Promise<MethodVersionList> {
    return this.get<MethodVersionList>("/red/methods", {
      tenant_id: tenantId,
      ...params,
    });
  }

  // The build board read (SPEC.md sections 3, 4, 7 and 8; Q38). The tenant is a
  // required query scope and the route is read-only; a build is born Identified
  // as a proposal and only a later transition changes its state, so the board
  // reads the work items and can transition none.
  listBuilds(tenantId: string, params: ListParams = {}): Promise<BuildList> {
    return this.get<BuildList>("/red/builds", {
      tenant_id: tenantId,
      ...params,
    });
  }

  // The offer and journey editor reads (SPEC.md sections 3, 5, 7, 8 and 9;
  // Q37). The tenant is the required query scope on both routes and both reads
  // are read-only, so a client never sees another's offers or releases and the
  // screen can approve no offer and authorize no traffic.
  listOffers(
    tenantId: string,
    params: ListParams = {},
  ): Promise<OfferList> {
    return this.get<OfferList>("/red/offers", {
      tenant_id: tenantId,
      ...params,
    });
  }

  listJourneys(
    tenantId: string,
    params: ListParams = {},
  ): Promise<JourneyReleaseList> {
    return this.get<JourneyReleaseList>("/red/journeys", {
      tenant_id: tenantId,
      ...params,
    });
  }

  // The approval inbox read (SPEC.md sections 3, 4, 7 and 8; Q39). The tenant is
  // a required query scope and the route is read-only; an approval is pinned to
  // an exact asset version by the passing gate decision, so listing an approval
  // cannot itself authorize production or traffic.
  listApprovals(
    tenantId: string,
    params: ListParams = {},
  ): Promise<ApprovalList> {
    return this.get<ApprovalList>("/red/approvals", {
      tenant_id: tenantId,
      ...params,
    });
  }

  health(): Promise<{ status: string }> {
    return this.get<{ status: string }>("/red/health");
  }
}
