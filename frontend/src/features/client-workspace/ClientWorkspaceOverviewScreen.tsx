// Client workspace overview container (Q34; SPEC.md sections 4 and 8). It owns
// the tenant-scoped read from the engagement production view and hands it to the
// presentational `ClientWorkspaceOverview`. It cannot approve or release
// anything; a read of the view authorizes no action.

"use client";

import { useCallback, useEffect, useState } from "react";

import {
  RedOperationsApi,
  type EngagementProductionView,
} from "@/shared/api/client";
import { ClientWorkspaceOverview } from "./ClientWorkspaceOverview";

const PILOT_TENANT = process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";
const PILOT_ENGAGEMENT =
  process.env.NEXT_PUBLIC_RED_DEFAULT_ENGAGEMENT ?? "3fmindset";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function ClientWorkspaceOverviewScreen() {
  const [tenantId, setTenantId] = useState(PILOT_TENANT);
  const [engagement, setEngagement] = useState(PILOT_ENGAGEMENT);
  const [on, setOn] = useState(today());
  const [view, setView] = useState<EngagementProductionView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new RedOperationsApi();
      setView(await api.getProductionView(tenantId, engagement, on));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workspace");
    } finally {
      setLoading(false);
    }
  }, [tenantId, engagement, on]);

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
          Engagement
          <input
            value={engagement}
            onChange={(event) => setEngagement(event.target.value)}
          />
        </label>
        <label>
          On
          <input
            type="date"
            value={on}
            onChange={(event) => setOn(event.target.value)}
          />
        </label>
        <button type="submit">Refresh</button>
      </form>
      <ClientWorkspaceOverview view={view} loading={loading} error={error} />
    </div>
  );
}
