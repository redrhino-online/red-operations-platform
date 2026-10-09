"use client";

// Workflow run detail container, native cockpit page (K4; SPEC.md section 14
// conditions 2 and 3). Additive file (ADR 0014). It reads the shared workspace
// selection from `useRedClient()` (K2) for the tenant scope and owns the
// tenant-scoped read from `GET /red/clients/{tenant_id}/workflows/{run_id}`;
// there is no per-screen free-text tenant input. The run id is the specific
// resource being inspected, not a tenant or engagement scope. It can advance no
// run; a read authorizes no action.

import { useCallback, useEffect, useState } from "react";

import { useRedClient } from "@/components/workspace/RedClientContext";
import { getWorkflowRun, type WorkflowRunView } from "@/lib/redOperationsApi";
import { WorkflowRunDetail } from "./WorkflowRunDetail";

export function WorkflowRunDetailScreen() {
  const { tenantId } = useRedClient();
  const [runId, setRunId] = useState("");
  const [run, setRun] = useState<WorkflowRunView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (runId.trim() === "") {
      setRun(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setRun(await getWorkflowRun(tenantId, runId.trim()));
    } catch (err) {
      setRun(null);
      setError(
        err instanceof Error ? err.message : "Failed to load workflow run",
      );
    } finally {
      setLoading(false);
    }
  }, [tenantId, runId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="flex-1 min-h-0 overflow-y-auto">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <label className="text-xs text-fg-muted flex items-center gap-2">
            Run id
            <input
              value={runId}
              onChange={(event) => setRunId(event.target.value)}
              className="rounded-lg border border-line bg-surface px-2 py-1 text-xs text-fg focus:outline-none focus:border-line-strong"
            />
          </label>
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-lg border border-line bg-surface-overlay px-3 py-1.5 text-xs font-medium text-fg hover:border-line-strong"
          >
            Load
          </button>
        </div>
        <WorkflowRunDetail run={run} loading={loading} error={error} />
      </div>
    </main>
  );
}
