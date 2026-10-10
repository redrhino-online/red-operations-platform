"use client";

// Approval inbox container, native cockpit page (K3; SPEC.md section 14
// conditions 2 and 3). Additive file (ADR 0014). It reads the shared workspace
// selection from `useRedClient()` (K2) and owns the tenant-scoped read from
// `GET /red/approvals`; there is no per-screen free-text tenant input. It can
// approve nothing; a read authorizes no action.

import { useCallback, useEffect, useState } from "react";

import { useRedClient } from "@/components/workspace/RedClientContext";
import {
  listApprovals,
  listAwaitingApprovals,
  type ApprovalRecord,
  type AwaitingApprovalRun,
} from "@/lib/redOperationsApi";
import { ApprovalInbox } from "./ApprovalInbox";

export function ApprovalInboxScreen() {
  const { tenantId } = useRedClient();
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [awaiting, setAwaiting] = useState<AwaitingApprovalRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        />
      </div>
    </main>
  );
}
