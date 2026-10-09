"use client";

// Launch readiness container, native cockpit page (K4; SPEC.md section 14
// conditions 2 and 3). Additive file (ADR 0014). It reads the shared workspace
// selection from `useRedClient()` (K2) and owns the tenant-scoped read from
// `GET /red/launch-qas`; there is no per-screen free-text tenant input. It can
// authorize no traffic; a read grants no authority.

import { useCallback, useEffect, useState } from "react";

import { useRedClient } from "@/components/workspace/RedClientContext";
import { listLaunchQAs, type LaunchQA } from "@/lib/redOperationsApi";
import { LaunchReadiness } from "./LaunchReadiness";

export function LaunchReadinessScreen() {
  const { tenantId } = useRedClient();
  const [launchQas, setLaunchQas] = useState<LaunchQA[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await listLaunchQAs(tenantId);
      setLaunchQas(page.launch_qas);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load launch readiness",
      );
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
        <LaunchReadiness
          launchQas={launchQas}
          loading={loading}
          error={error}
          tenantId={tenantId}
        />
      </div>
    </main>
  );
}
