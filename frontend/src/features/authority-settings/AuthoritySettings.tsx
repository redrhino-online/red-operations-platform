// Authority settings (SPEC.md sections 3, 4, 7 and 8; DoD condition 6, Q44).
//
// Pure presentational view over two tenant-scoped reads: the client workspace
// authority registry (`GET /red/clients`) and the engagement production view
// (`GET /red/clients/{tenant}/engagements/{engagement}/production-view`).
// SPEC.md section 3 records each workspace's authorities and requires every
// child resource to belong to exactly one client; SPEC.md section 4 requires a
// client-designated authority per gate and forbids an agent conferring human
// approval on itself. This view shows each named authority and, per stage, the
// gate's approver scope and who recorded the decision. It grants no authority:
// the concrete authority roles remain an open decision (SPEC.md section 11), so
// the view never invents one.

import type { ClientWorkspace, StageProductionView } from "@/shared/api/client";

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
      <h1 id="authority-settings-heading">Authority settings</h1>
      <p style={{ color: "var(--red-muted)" }}>
        Designated authorities and the gate scope each stage approves against
        for {tenantId ?? "the active client"}. This view grants no authority and
        approves no gate.
      </p>

      {loading ? <p role="status">Loading authority settings...</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <h2>Designated authorities ({holders.length})</h2>
      {!loading && holders.length === 0 ? (
        <p data-testid="authority-settings-empty">
          No designated authorities recorded.
        </p>
      ) : null}
      <ul data-testid="authority-holders">
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

      <h2>Gate approval scopes ({scopes.length})</h2>
      <ol data-testid="approval-scopes">
        {scopes.map((scope) => (
          <li
            key={scope.stage_number}
            data-testid={`approval-scope-${scope.stage_number}`}
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
