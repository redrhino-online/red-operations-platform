// Approval inbox with exact version diff, native cockpit page (K3; SPEC.md
// section 14 conditions 2 and 3, section 8). Additive file (ADR 0014). Pure
// presentational inbox over the tenant-scoped version-specific approvals the
// backend returns from `GET /red/approvals`. Each approval pins exactly one
// asset version and one intended scope (SPEC.md sections 3 and 4), so the inbox
// groups approvals by the pinned asset kind and shows, per approval, the exact
// version it sealed and the exact diff against the previous version of the same
// asset. The diff is computed only from the append-only approval records the
// backend already returns; it asserts no approval rule, resolves no asset
// content and grants no authority. The backend owns the gate, so the inbox can
// approve nothing.

import type {
  ApprovalRecord,
  AwaitingApprovalRun,
} from "@/lib/redOperationsApi";

export interface ApprovalInboxProps {
  approvals: ApprovalRecord[];
  loading?: boolean;
  error?: string | null;
  tenantId?: string;
  awaiting?: AwaitingApprovalRun[];
}

// One field that changed between two versions of the same pinned asset, with
// the exact prior and current value, so the diff is exact rather than implied.
export interface ApprovalDiffEntry {
  field: string;
  from: string;
  to: string;
}

// One asset kind's approval history in ascending decision order, with the
// newest approval surfaced for the inbox header.
export interface AssetApprovalHistory {
  asset_id: string;
  history: ApprovalRecord[];
  latest: ApprovalRecord;
}

function orderKey(approval: ApprovalRecord): string {
  // ISO dates sort lexicographically; stage then version break a same-day tie so
  // the order is stable and the diff has a well-defined predecessor.
  const stage = String(approval.stage_number).padStart(3, "0");
  const version = String(approval.version).padStart(6, "0");
  return `${approval.decided_on}|${stage}|${version}`;
}

function display(value: string | null): string {
  return value === null || value === "" ? "none" : value;
}

// The exact diff between the previous approval of one asset kind and the
// current one. Returns an empty list when there is no previous version (a
// baseline approval) or when nothing changed; a changed field is reported with
// its exact prior and current value.
export function approvalDiff(
  previous: ApprovalRecord | null,
  current: ApprovalRecord,
): ApprovalDiffEntry[] {
  if (previous === null) {
    return [];
  }
  const entries: ApprovalDiffEntry[] = [];
  const compare = (
    field: string,
    from: string | number | null,
    to: string | number | null,
  ) => {
    const fromText = display(from === null ? null : String(from));
    const toText = display(to === null ? null : String(to));
    if (fromText !== toText) {
      entries.push({ field, from: fromText, to: toText });
    }
  };
  compare("version", previous.version, current.version);
  compare("scope", previous.scope, current.scope);
  compare("outcome", previous.outcome, current.outcome);
  compare("approver", previous.approver, current.approver);
  compare("requested_by", previous.requested_by, current.requested_by);
  compare("expires_on", previous.expires_on, current.expires_on);
  compare("stage_number", previous.stage_number, current.stage_number);
  compare("decided_on", previous.decided_on, current.decided_on);
  return entries;
}

// Group the tenant approvals by pinned asset kind, each history in ascending
// decision order, and the groups ordered by asset id for a stable inbox.
export function approvalHistories(
  approvals: ApprovalRecord[],
): AssetApprovalHistory[] {
  const byAsset = new Map<string, ApprovalRecord[]>();
  for (const approval of approvals) {
    const bucket = byAsset.get(approval.asset_id) ?? [];
    bucket.push(approval);
    byAsset.set(approval.asset_id, bucket);
  }
  return [...byAsset.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([asset_id, bucket]) => {
      const history = [...bucket].sort((a, b) =>
        orderKey(a).localeCompare(orderKey(b)),
      );
      return { asset_id, history, latest: history[history.length - 1] };
    });
}

// The exact version an approval pins, `<asset kind>@<version>`.
export function exactVersion(approval: ApprovalRecord): string {
  return `${approval.asset_id}@${approval.version}`;
}

// The prior approval of the same asset kind before the given one, or null when
// it is the baseline (first) approval in its history.
export function priorApproval(
  history: ApprovalRecord[],
  current: ApprovalRecord,
): ApprovalRecord | null {
  const ordered = [...history].sort((a, b) =>
    orderKey(a).localeCompare(orderKey(b)),
  );
  const index = ordered.findIndex(
    (entry) =>
      entry.stage_number === current.stage_number &&
      entry.version === current.version &&
      entry.decided_on === current.decided_on &&
      entry.scope === current.scope,
  );
  return index > 0 ? ordered[index - 1] : null;
}

// The pipeline gates waiting for their RED approval (K12; SPEC.md section 14
// condition 8). A waiting run pins the exact definition version it started on
// and names the gate it is waiting at, so the inbox shows the pending gate with
// its exact version; listing one approves nothing.
export function pendingGateApprovals(
  awaiting: AwaitingApprovalRun[],
): AwaitingApprovalRun[] {
  return awaiting
    .filter((run) => run.pending_approval !== null)
    .sort((a, b) => a.run_id.localeCompare(b.run_id));
}

export function ApprovalInbox({
  approvals,
  loading = false,
  error = null,
  tenantId,
  awaiting = [],
}: ApprovalInboxProps) {
  const histories = approvalHistories(approvals);
  const pending = pendingGateApprovals(awaiting);

  return (
    <section aria-labelledby="approval-inbox-heading">
      <h1 id="approval-inbox-heading" className="text-xl font-semibold text-fg">
        Approval inbox
      </h1>
      <p className="mt-1 text-sm text-fg-muted">
        The exact-version approvals for {tenantId ?? "the active client"}, each
        pinned to one asset version and one intended scope, with the version diff
        against the prior approval.
      </p>

      {loading ? (
        <p role="status" className="mt-4 text-sm text-fg-muted">
          Loading approvals…
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">
          {error}
        </p>
      ) : null}

      <p data-testid="approval-count" className="mt-4 text-sm text-fg-muted">
        {approvals.length} approval{approvals.length === 1 ? "" : "s"}
      </p>

      <section
        aria-labelledby="pending-gates-heading"
        data-testid="pending-gate-approvals"
        className="mt-6 rounded-xl border border-line bg-surface-elevated p-4"
      >
        <h2 id="pending-gates-heading" className="text-sm font-medium text-fg">
          Pending gate approvals
        </h2>
        <p data-testid="pending-gate-count" className="mt-1 text-sm text-fg-muted">
          {pending.length} pipeline gate{pending.length === 1 ? "" : "s"} waiting
          for their RED approval
        </p>
        {pending.length === 0 ? (
          <p className="mt-2 text-sm text-fg-muted">
            No pipeline gate is waiting for an approval.
          </p>
        ) : (
          <ul className="mt-3 space-y-3">
            {pending.map((run) => (
              <li
                key={run.run_id}
                data-testid={`pending-gate-${run.run_id}`}
                className="rounded-lg border border-line bg-surface p-3 text-xs text-fg"
              >
                <p>
                  <strong>{run.pending_approval}</strong> on{" "}
                  <code>{run.definition_id}@{run.definition_version}</code>
                </p>
                <p className="text-fg-muted">
                  Run: {run.run_id} | Committed:{" "}
                  {run.completed_steps.join(", ") || "none"}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {!loading && approvals.length === 0 ? (
        <p className="mt-2 text-sm text-fg-muted">No approvals.</p>
      ) : null}

      <div className="mt-4 space-y-4">
        {histories.map(({ asset_id, history, latest }) => (
          <article
            key={asset_id}
            aria-label={`Approvals for ${asset_id}`}
            className="rounded-xl border border-line bg-surface-elevated p-4"
          >
            <h2 className="text-sm font-medium text-fg">{asset_id}</h2>
            <p
              data-testid={`latest-version-${asset_id}`}
              className="mt-1 text-xs text-fg-muted"
            >
              Latest exact version: {exactVersion(latest)}
            </p>
            <ol className="mt-3 space-y-3">
              {[...history].reverse().map((approval) => {
                const previous = priorApproval(history, approval);
                const diff = approvalDiff(previous, approval);
                const key = exactVersion(approval);
                return (
                  <li
                    key={`${key}-${approval.stage_number}-${approval.decided_on}`}
                    className="rounded-lg border border-line bg-surface p-3"
                  >
                    <h3
                      data-testid={`approval-${key}`}
                      className="text-xs font-medium text-fg"
                    >
                      Version {approval.version}
                    </h3>
                    <p className="mt-1 text-xs text-fg-muted">
                      Scope: {approval.scope}
                    </p>
                    <p className="text-xs text-fg-muted">
                      Requested by: {approval.requested_by} | Approver:{" "}
                      {approval.approver}
                    </p>
                    <p className="text-xs text-fg-muted">
                      Outcome: {approval.outcome} | Stage: {approval.stage_number} |
                      Decided: {approval.decided_on}
                    </p>
                    <p className="text-xs text-fg-muted">
                      Expires: {display(approval.expires_on)}
                    </p>
                    <div
                      data-testid={`diff-${key}-${approval.stage_number}`}
                      className="mt-2 text-xs text-fg-muted"
                    >
                      {previous === null ? (
                        <p>Baseline approval, no prior version to diff.</p>
                      ) : diff.length === 0 ? (
                        <p>No change from the prior version.</p>
                      ) : (
                        <ul className="list-disc pl-4">
                          {diff.map((entry) => (
                            <li key={entry.field}>
                              {entry.field}: {entry.from} &rarr; {entry.to}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </li>
                );
              })}
            </ol>
          </article>
        ))}
      </div>
    </section>
  );
}
