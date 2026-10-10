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
  // Selecting an approved-asset pin opens the asset detail panel (asset review
  // and approval spec section 3.1); the overview itself fetches nothing.
  onSelectAsset?: (assetId: string) => void;
  // Opens the schema-driven record-gate form for one stage (asset review and
  // approval spec section 3.3). Rendered for every stage 0-10; the backend
  // remains the sole enforcer of prerequisites, expiry and authority.
  onRecordGate?: (stageNumber: number) => void;
  // Opens the markdown artifact drop form for one stage (stage artifact
  // archive spec section 3). Rendered for every stage 0-10 beside Record gate;
  // the backend remains the sole enforcer of the archive's fields.
  onAddArtifact?: (stageNumber: number) => void;
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
  onSelectAsset,
  onRecordGate,
  onAddArtifact,
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
                  {onRecordGate || onAddArtifact ? (
                    <th scope="col" className="px-3 py-2 font-medium">Actions</th>
                  ) : null}
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
                      {stage.approved_assets.length === 0 ? (
                        "none"
                      ) : (
                        <span className="inline-flex flex-wrap gap-x-2 gap-y-1">
                          {stage.approved_assets.map((asset) => {
                            const pin = `${asset.asset_id}@v${asset.version}`;
                            return (
                              <button
                                key={pin}
                                type="button"
                                data-testid={`asset-pin-${pin}`}
                                aria-label={`Asset detail for ${asset.asset_id}`}
                                onClick={() => onSelectAsset?.(asset.asset_id)}
                                className="rounded border border-line bg-surface px-1.5 py-0.5 text-left text-xs text-fg hover:border-line-strong focus:outline-none focus:border-line-strong"
                              >
                                {pin}
                              </button>
                            );
                          })}
                        </span>
                      )}
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
                    {onRecordGate || onAddArtifact ? (
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap items-center gap-2">
                          {onRecordGate ? (
                            <button
                              type="button"
                              data-testid={`record-gate-${stage.stage_number}`}
                              onClick={() => onRecordGate(stage.stage_number)}
                              className="rounded-lg border border-line bg-surface-overlay px-2 py-1 text-xs font-medium text-fg hover:border-line-strong focus:outline-none focus:border-line-strong"
                            >
                              Record gate
                            </button>
                          ) : null}
                          {onAddArtifact ? (
                            <button
                              type="button"
                              data-testid={`add-artifact-${stage.stage_number}`}
                              onClick={() => onAddArtifact(stage.stage_number)}
                              className="rounded-lg border border-line bg-surface-overlay px-2 py-1 text-xs font-medium text-fg hover:border-line-strong focus:outline-none focus:border-line-strong"
                            >
                              Add artifact
                            </button>
                          ) : null}
                        </div>
                      </td>
                    ) : null}
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
