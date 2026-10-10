"use client";

// Approval inbox container, native cockpit page (K3; SPEC.md section 14
// conditions 2 and 3). Additive file (ADR 0014). It reads the shared workspace
// selection from `useRedClient()` (K2) and owns the tenant-scoped read from
// `GET /red/approvals`; there is no per-screen free-text tenant input. The
// pending gates' Approve forms suggest the actors of the selected workspace's
// authority registry (asset review and approval spec section 3.2) and refresh
// the reads after a successful approval; the backend validates every approval.

import { useCallback, useEffect, useMemo, useState } from "react";

import { useRedClient } from "@/components/workspace/RedClientContext";
import {
  listApprovals,
  listAwaitingApprovals,
  type ApprovalRecord,
  type AwaitingApprovalRun,
} from "@/lib/redOperationsApi";
import { ApprovalInbox } from "./ApprovalInbox";

export function ApprovalInboxScreen() {
  const { tenantId, workspaceId, workspaces } = useRedClient();
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [awaiting, setAwaiting] = useState<AwaitingApprovalRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The selected workspace's registered actors, from the listing the shared
  // context already loaded; the inbox only suggests them.
  const authorities = useMemo(() => {
    const workspace = workspaces.find(
      (candidate) => candidate.workspace_id === workspaceId,
    );
    return workspace ? workspace.authorities.map((entry) => entry.actor) : [];
  }, [workspaces, workspaceId]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [page, waiting] = await Promise.all([
        listApprovals(tenantId),
        listAwaitingApprovals(tenantId),
      ]);
      setApprovals(page.approvals);
      setAwaiting(waiting.runs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="flex-1 min-h-0 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <div className="mb-4">
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-lg border border-line bg-surface-overlay px-3 py-1.5 text-xs font-medium text-fg hover:border-line-strong"
          >
            Refresh
          </button>
        </div>
        <ApprovalInbox
          approvals={approvals}
          awaiting={awaiting}
          loading={loading}
          error={error}
          tenantId={tenantId}
          authorities={authorities}
          onApproved={() => void load()}
        />
      </div>
    </main>
  );
}
