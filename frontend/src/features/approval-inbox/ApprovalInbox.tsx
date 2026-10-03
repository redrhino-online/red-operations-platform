// Approval inbox with exact version diff (SPEC.md sections 3, 4 and 8; DoD
// condition 6, Q39).
//
// Pure presentational inbox over the tenant-scoped version-specific approvals
// the backend returns from `GET /red/approvals`. Each approval pins exactly one
// asset version and one intended scope (SPEC.md sections 3 and 4), so the inbox
// groups approvals by the pinned asset kind and shows, per approval, the exact
// version it sealed and the exact diff against the previous version of the same
// asset. The diff is computed only from the append-only approval records the
// backend already returns; it asserts no approval rule, resolves no asset
// content and grants no authority. The backend owns the gate, so the inbox can
// approve nothing.

import type { ApprovalRecord } from "@/shared/api/client";

export interface ApprovalInboxProps {
  approvals: ApprovalRecord[];
  loading?: boolean;
  error?: string | null;
  tenantId?: string;
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

export function ApprovalInbox({
  approvals,
  loading = false,
  error = null,
  tenantId,
}: ApprovalInboxProps) {
  const histories = approvalHistories(approvals);

  return (
    <section aria-labelledby="approval-inbox-heading">
      <h1 id="approval-inbox-heading">Approval inbox</h1>
      <p style={{ color: "var(--red-muted)" }}>
        The exact-version approvals for {tenantId ?? "the active client"}, each
        pinned to one asset version and one intended scope, with the version diff
        against the prior approval.
      </p>

      {loading ? <p role="status">Loading approvals...</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <p data-testid="approval-count">
        {approvals.length} approval{approvals.length === 1 ? "" : "s"}
      </p>

      {!loading && approvals.length === 0 ? <p>No approvals.</p> : null}

      {histories.map(({ asset_id, history, latest }) => (
        <article key={asset_id} aria-label={`Approvals for ${asset_id}`}>
          <h2>{asset_id}</h2>
          <p data-testid={`latest-version-${asset_id}`}>
            Latest exact version: {exactVersion(latest)}
          </p>
          <ol>
            {[...history].reverse().map((approval) => {
              const previous = priorApproval(history, approval);
              const diff = approvalDiff(previous, approval);
              const key = exactVersion(approval);
              return (
                <li key={`${key}-${approval.stage_number}-${approval.decided_on}`}>
                  <h3 data-testid={`approval-${key}`}>
                    Version {approval.version}
                  </h3>
                  <p>Scope: {approval.scope}</p>
                  <p>
                    Requested by: {approval.requested_by} | Approver:{" "}
                    {approval.approver}
                  </p>
                  <p>
                    Outcome: {approval.outcome} | Stage: {approval.stage_number} |
                    Decided: {approval.decided_on}
                  </p>
                  <p>Expires: {display(approval.expires_on)}</p>
                  <div data-testid={`diff-${key}-${approval.stage_number}`}>
                    {previous === null ? (
                      <p>Baseline approval, no prior version to diff.</p>
                    ) : diff.length === 0 ? (
                      <p>No change from the prior version.</p>
                    ) : (
                      <ul>
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
    </section>
  );
}
