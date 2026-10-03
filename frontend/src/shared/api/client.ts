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

export interface WorkflowRunView {
  run_id: string;
  event_id: string;
  state: string;
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

  health(): Promise<{ status: string }> {
    return this.get<{ status: string }>("/red/health");
  }
}
