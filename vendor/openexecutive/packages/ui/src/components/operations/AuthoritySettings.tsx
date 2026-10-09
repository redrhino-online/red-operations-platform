// Authority settings, native cockpit page (K6; SPEC.md section 14 conditions 2
// and 3, section 8). Additive file (ADR 0014). Pure presentational view over two
// tenant-scoped reads: the client workspace authority registry (the shared
// context's `GET /red/clients` listing) and the engagement production view
// (`GET /red/clients/{tenant}/engagements/{engagement}/production-view`).
// SPEC.md section 3 records each workspace's authorities and requires every
// child resource to belong to exactly one client; SPEC.md section 4 requires a
// client-designated authority per gate and forbids an agent conferring human
// approval on itself. This view shows each named authority and, per stage, the
// gate's approver scope and who recorded the decision. It grants no authority:
// the concrete authority roles remain an open decision (SPEC.md section 11), so
// the view never invents one.

import type { ClientWorkspace, StageProductionView } from "@/lib/redOperationsApi";

export interface AuthoritySettingsProps {
  workspaces: ClientWorkspace[];
  stages: StageProductionView[];
  loading?: boolean;
  error?: string | null;
  tenantId?: string;
}

// One named authority in the registry, flattened with its owning workspace so a
// reader sees which workspace grants it (SPEC.md section 3).
export interface AuthorityHolder {
  workspace_id: string;
  actor: string;
  authority: string;
}

// The scope one stage gate approves against: the accountable role, the required
// approver role and the human who recorded the decision (SPEC.md section 4).
export interface ApprovalScope {
  stage_number: number;
  name: string;
  checkpoint: string;
  accountable_role: string;
  approver_role: string;
  recorded_approver: string | null;
  is_approved: boolean;
}

export function authorityHolders(
  workspaces: ClientWorkspace[],
): AuthorityHolder[] {
  return workspaces.flatMap((workspace) =>
    workspace.authorities.map((entry) => ({
      workspace_id: workspace.workspace_id,
      actor: entry.actor,
      authority: entry.authority,
    })),
  );
}

export function approvalScopes(stages: StageProductionView[]): ApprovalScope[] {
  return stages.map((stage) => ({
    stage_number: stage.stage_number,
    name: stage.name,
    checkpoint: stage.checkpoint,
    accountable_role: stage.accountable_role,
    approver_role: stage.approver_role,
    recorded_approver: stage.recorded_approver,
    is_approved: stage.is_approved,
  }));
}

// A gate is only approved by a named human; an unrecorded gate stays unapproved
// in the view rather than appearing waived (SPEC.md sections 1 and 4).
export function approverLabel(scope: ApprovalScope): string {
  return scope.recorded_approver ?? "not recorded";
}

export function AuthoritySettings({
  workspaces,
  stages,
  loading = false,
  error = null,
  tenantId,
}: AuthoritySettingsProps) {
  const holders = authorityHolders(workspaces);
  const scopes = approvalScopes(stages);

  return (
    <section aria-labelledby="authority-settings-heading">
      <h1 id="authority-settings-heading" className="text-xl font-semibold text-fg">
        Authority settings
      </h1>
      <p className="mt-1 text-sm text-fg-muted">
        Designated authorities and the gate scope each stage approves against
        for {tenantId ?? "the active client"}. This view grants no authority and
        approves no gate.
      </p>

      {loading ? (
        <p role="status" className="mt-4 text-sm text-fg-muted">
          Loading authority settings…
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">
          {error}
        </p>
      ) : null}

      <h2 className="mt-6 text-sm font-medium text-fg">
        Designated authorities ({holders.length})
      </h2>
      {!loading && holders.length === 0 ? (
        <p
          data-testid="authority-settings-empty"
          className="mt-2 text-sm text-fg-muted"
        >
          No designated authorities recorded.
        </p>
      ) : null}
      <ul
        data-testid="authority-holders"
        className="mt-2 list-disc pl-5 text-sm text-fg"
      >
        {holders.map((holder) => (
          <li
            key={`${holder.workspace_id}:${holder.actor}:${holder.authority}`}
            data-testid={`authority-holder-${holder.actor}`}
          >
            <strong>{holder.actor}</strong>: {holder.authority} (workspace:{" "}
            {holder.workspace_id})
          </li>
        ))}
      </ul>

      <h2 className="mt-6 text-sm font-medium text-fg">
        Gate approval scopes ({scopes.length})
      </h2>
      <ol
        data-testid="approval-scopes"
        className="mt-2 space-y-2 text-sm text-fg"
      >
        {scopes.map((scope) => (
          <li
            key={scope.stage_number}
            data-testid={`approval-scope-${scope.stage_number}`}
            className="rounded-lg border border-line bg-surface p-3"
          >
            Stage {scope.stage_number} {scope.name} ({scope.checkpoint}):{" "}
            accountable {scope.accountable_role}, approver {scope.approver_role},
            recorded by {approverLabel(scope)}
            {scope.is_approved ? " (approved)" : ""}
          </li>
        ))}
      </ol>
    </section>
  );
}
