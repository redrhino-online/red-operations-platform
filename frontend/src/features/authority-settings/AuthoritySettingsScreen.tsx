// Authority settings container (Q44; SPEC.md sections 3, 4 and 8). It owns the
// two tenant-scoped reads: the client workspace authority registry and the
// engagement production view's per-stage gate scopes. It grants no authority
// and approves no gate; a read changes no state.

"use client";

import { useCallback, useEffect, useState } from "react";

import {
  RedOperationsApi,
  type ClientWorkspace,
  type EngagementProductionView,
} from "@/shared/api/client";
import { AuthoritySettings } from "./AuthoritySettings";

const PILOT_TENANT = process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";
const PILOT_ENGAGEMENT =
  process.env.NEXT_PUBLIC_RED_DEFAULT_ENGAGEMENT ?? "3fmindset";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function AuthoritySettingsScreen() {
  const [tenantId, setTenantId] = useState(PILOT_TENANT);
  const [engagement, setEngagement] = useState(PILOT_ENGAGEMENT);
  const [on, setOn] = useState(today());
  const [workspaces, setWorkspaces] = useState<ClientWorkspace[]>([]);
  const [view, setView] = useState<EngagementProductionView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new RedOperationsApi();
      const [registry, production] = await Promise.all([
        api.listClients(tenantId),
        api.getProductionView(tenantId, engagement, on),
      ]);
      setWorkspaces(registry.workspaces);
      setView(production);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load authority settings",
      );
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
      <AuthoritySettings
        workspaces={workspaces}
        stages={view?.stages ?? []}
        loading={loading}
        error={error}
        tenantId={tenantId}
      />
    </div>
  );
}
