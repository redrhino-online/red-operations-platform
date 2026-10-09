// Client workspace overview, native cockpit page (K3; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). Pure presentational
// view over the production-manager view the backend returns from
// `GET /red/clients/{tenant}/engagements/{engagement}/production-view`: it
// renders, per stage, the state, the exact pinned asset versions (provenance and
// version history), the dependency that blocks work, the accountable owner and
// the next action, and it keeps verified progress apart from activity. The
// backend decides all of that (SPEC.md section 4); the UI only shows it and can
// approve nothing.

import type {
  AssetVersion,
  EngagementProductionView,
  StageProductionView,
} from "@/lib/redOperationsApi";

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
      <h1 id="client-workspace-heading" className="text-xl font-semibold text-fg">
        Client workspace overview
      </h1>

      {loading ? (
        <p role="status" className="mt-4 text-sm text-fg-muted">
          Loading workspace overview…
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">
          {error}
        </p>
      ) : null}

      {view ? (
        <div className="mt-4">
          <p className="text-sm text-fg-muted">
            Engagement <strong className="text-fg">{view.engagement}</strong> for
            tenant {view.tenant_id} on template {view.template_version}.
          </p>
          <p data-testid="verified-progress" className="mt-2 text-sm text-fg-muted">
            {view.progress.approved_gates} of {view.progress.total_gates} gates
            approved, {view.progress.gates_remaining} gates remaining;{" "}
            {view.progress.verified_post_launch_milestones} verified milestones
            and {view.progress.activity_entries} activity entries.
          </p>
          <p className="mt-2 text-sm text-fg-muted">
            Current stage:{" "}
            {view.current_stage_number ?? "none (pipeline complete)"}; next
            approval: {view.next_approval_stage_number ?? "none"}.
          </p>

          <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface-elevated">
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-fg-muted">
                <tr className="border-b border-line">
                  <th scope="col" className="px-3 py-2 font-medium">Stage</th>
                  <th scope="col" className="px-3 py-2 font-medium">Checkpoint</th>
                  <th scope="col" className="px-3 py-2 font-medium">State</th>
                  <th scope="col" className="px-3 py-2 font-medium">Approved assets</th>
                  <th scope="col" className="px-3 py-2 font-medium">Missing</th>
                  <th scope="col" className="px-3 py-2 font-medium">Dependency</th>
                  <th scope="col" className="px-3 py-2 font-medium">Owner</th>
                  <th scope="col" className="px-3 py-2 font-medium">Next action</th>
                  <th scope="col" className="px-3 py-2 font-medium">Due</th>
                </tr>
              </thead>
              <tbody>
                {view.stages.map((stage) => (
                  <tr
                    key={stage.stage_number}
                    className="border-b border-line last:border-0 align-top"
                  >
                    <td className="px-3 py-2 text-fg">{stage.name}</td>
                    <td className="px-3 py-2 text-fg">{stage.checkpoint}</td>
                    <td className="px-3 py-2 text-fg">
                      {stage.is_approved ? "approved" : stage.status}
                    </td>
                    <td className="px-3 py-2 text-fg">
                      {assetPins(stage.approved_assets).join(", ") || "none"}
                    </td>
                    <td className="px-3 py-2 text-fg">
                      {stage.missing_asset_kinds.join(", ") || "none"}
                    </td>
                    <td className="px-3 py-2 text-fg">{dependencyLabel(stage)}</td>
                    <td className="px-3 py-2 text-fg">
                      {stage.assigned_owner ?? stage.accountable_role}
                    </td>
                    <td className="px-3 py-2 text-fg">{stage.next_action || "none"}</td>
                    <td className="px-3 py-2 text-fg">{stage.due_on ?? "no due date"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  );
}
