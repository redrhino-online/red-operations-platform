// Workflow run detail container (Q40; SPEC.md sections 7 and 8). It owns the
// tenant-scoped read from `GET /red/clients/{tenant_id}/workflows/{run_id}` and
// hands the durable run to the presentational `WorkflowRunDetail`. It can
// advance no run; a read authorizes no action.

"use client";

import { useCallback, useEffect, useState } from "react";

import { RedOperationsApi, type WorkflowRunView } from "@/shared/api/client";
import { WorkflowRunDetail } from "./WorkflowRunDetail";

const PILOT_TENANT = process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";

export function WorkflowRunDetailScreen() {
  const [tenantId, setTenantId] = useState(PILOT_TENANT);
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
      const api = new RedOperationsApi();
      setRun(await api.getWorkflowRun(tenantId, runId.trim()));
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
    <div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void load();
        }}
      >
        <label>
          Tenant
          <input
            value={tenantId}
            onChange={(event) => setTenantId(event.target.value)}
          />
        </label>
        <label>
          Run id
          <input
            value={runId}
            onChange={(event) => setRunId(event.target.value)}
          />
        </label>
        <button type="submit">Load</button>
      </form>
      <WorkflowRunDetail run={run} loading={loading} error={error} />
    </div>
  );
}
