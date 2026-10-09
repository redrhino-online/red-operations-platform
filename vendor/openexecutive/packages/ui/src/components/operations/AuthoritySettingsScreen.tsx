"use client";

// Authority settings container, native cockpit page (K6; SPEC.md section 14
// conditions 2 and 3). Additive file (ADR 0014). It reads the shared workspace
// selection and the tenant-scoped authority registry from `useRedClient()` (K2)
// and owns the engagement production view read for the per-stage gate scopes;
// there is no per-screen free-text tenant or engagement input. It grants no
// authority and approves no gate; a read changes no state.

import { useCallback, useEffect, useState } from "react";

import { useRedClient } from "@/components/workspace/RedClientContext";
import {
  getProductionView,
  type EngagementProductionView,
} from "@/lib/redOperationsApi";
import { AuthoritySettings } from "./AuthoritySettings";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function AuthoritySettingsScreen() {
  const { tenantId, workspaceId, workspaces } = useRedClient();
  const [on, setOn] = useState(today());
  const [view, setView] = useState<EngagementProductionView | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!workspaceId) {
      setView(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setView(await getProductionView(tenantId, workspaceId, on));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load authority settings",
      );
    } finally {
      setLoading(false);
    }
  }, [tenantId, workspaceId, on]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="flex-1 min-h-0 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <label className="text-xs text-fg-muted flex items-center gap-2">
            On
            <input
              type="date"
              value={on}
              onChange={(event) => setOn(event.target.value)}
              className="rounded-lg border border-line bg-surface px-2 py-1 text-xs text-fg focus:outline-none focus:border-line-strong"
            />
          </label>
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-lg border border-line bg-surface-overlay px-3 py-1.5 text-xs font-medium text-fg hover:border-line-strong"
          >
            Refresh
          </button>
        </div>
        <AuthoritySettings
          workspaces={workspaces}
          stages={view?.stages ?? []}
          loading={loading}
          error={error}
          tenantId={tenantId}
        />
      </div>
    </main>
  );
}
