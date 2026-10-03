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

  health(): Promise<{ status: string }> {
    return this.get<{ status: string }>("/red/health");
  }
}
