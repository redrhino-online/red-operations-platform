"use client";

// Command center container, native cockpit page (K3; SPEC.md section 14
// conditions 2 and 3). Additive file (ADR 0014). It reads the shared
// workspace/engagement selection from `useRedClient()` (K2) and owns the
// tenant-scoped read from `GET /red/interventions`; there is no per-screen
// free-text tenant or engagement input. It cannot approve or release anything;
// a read of a card authorizes no action.

import { useCallback, useEffect, useState } from "react";

import { useRedClient } from "@/components/workspace/RedClientContext";
import {
  listInterventions,
  type InterventionCard,
} from "@/lib/redOperationsApi";
import { CommandCenter } from "./CommandCenter";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function CommandCenterScreen() {
  const { tenantId, workspaceId } = useRedClient();
  const [on, setOn] = useState(today());
  const [interventions, setInterventions] = useState<InterventionCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!workspaceId) {
      setInterventions([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const page = await listInterventions(tenantId, workspaceId, on);
      setInterventions(page.interventions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cards");
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
        {!workspaceId ? (
          <p className="text-sm text-fg-muted">
            Select a workspace to see its ranked interventions.
          </p>
        ) : (
          <CommandCenter
            interventions={interventions}
            loading={loading}
            error={error}
            engagement={workspaceId}
            on={on}
          />
        )}
      </div>
    </main>
  );
}
