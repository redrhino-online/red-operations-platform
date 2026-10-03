// Client workspace overview (SPEC.md sections 4 and 8; DoD condition 6, Q34).
//
// Pure presentational view over the production-manager view the backend returns
// from `GET /red/clients/{tenant}/engagements/{engagement}/production-view`. It
// holds no RED business logic: it renders, per stage, the state, the exact
// pinned asset versions (provenance and version history), the dependency that
// blocks work, the accountable owner and the next action, and it keeps verified
// progress apart from activity. The backend decides all of that (SPEC.md
// section 4); the UI only shows it and can approve nothing.

import type {
  AssetVersion,
  EngagementProductionView,
  StageProductionView,
} from "@/shared/api/client";

export interface ClientWorkspaceOverviewProps {
  view: EngagementProductionView | null;
  loading?: boolean;
  error?: string | null;
}

// Provenance: an approved asset is only ever shown at an exact pinned version.
export function assetPins(assets: AssetVersion[]): string[] {
  return assets.map((asset) => `${asset.asset_id}@v${asset.version}`);
}

function dependencyLabel(stage: StageProductionView): string {
  if (stage.blocking_dependencies.length > 0) {
    return `blocked by stage ${stage.blocking_dependencies.join(", ")}`;
  }
  if (stage.dependencies.length > 0) {
    return `after stage ${stage.dependencies.join(", ")}`;
  }
  return "no dependency";
}

export function ClientWorkspaceOverview({
  view,
  loading = false,
  error = null,
}: ClientWorkspaceOverviewProps) {
  return (
    <section aria-labelledby="client-workspace-heading">
      <h1 id="client-workspace-heading">Client workspace overview</h1>

      {loading ? <p role="status">Loading workspace overview...</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      {view ? (
        <div>
          <p>
            Engagement <strong>{view.engagement}</strong> for tenant{" "}
            {view.tenant_id} on template {view.template_version}.
          </p>
          <p data-testid="verified-progress">
            {view.progress.approved_gates} of {view.progress.total_gates} gates
            approved, {view.progress.gates_remaining} gates remaining;{" "}
            {view.progress.verified_post_launch_milestones} verified milestones
            and {view.progress.activity_entries} activity entries.
          </p>
          <p>
            Current stage:{" "}
            {view.current_stage_number ?? "none (pipeline complete)"}; next
            approval: {view.next_approval_stage_number ?? "none"}.
          </p>

          <table>
            <thead>
              <tr>
                <th scope="col">Stage</th>
                <th scope="col">Checkpoint</th>
                <th scope="col">State</th>
                <th scope="col">Approved assets</th>
                <th scope="col">Missing</th>
                <th scope="col">Dependency</th>
                <th scope="col">Owner</th>
                <th scope="col">Next action</th>
                <th scope="col">Due</th>
              </tr>
            </thead>
            <tbody>
              {view.stages.map((stage) => (
                <tr key={stage.stage_number}>
                  <td>{stage.name}</td>
                  <td>{stage.checkpoint}</td>
                  <td>{stage.is_approved ? "approved" : stage.status}</td>
                  <td>{assetPins(stage.approved_assets).join(", ") || "none"}</td>
                  <td>{stage.missing_asset_kinds.join(", ") || "none"}</td>
                  <td>{dependencyLabel(stage)}</td>
                  <td>{stage.assigned_owner ?? stage.accountable_role}</td>
                  <td>{stage.next_action || "none"}</td>
                  <td>{stage.due_on ?? "no due date"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
