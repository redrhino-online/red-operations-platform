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
