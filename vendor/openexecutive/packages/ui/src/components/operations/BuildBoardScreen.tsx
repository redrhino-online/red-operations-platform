"use client";

// Build board container, native cockpit page (K4; SPEC.md section 14 conditions
// 2 and 3). Additive file (ADR 0014). It reads the shared workspace selection
// from `useRedClient()` (K2) and owns the tenant-scoped read from
// `GET /red/builds`; there is no per-screen free-text tenant input. It can
// transition no build and approve nothing; a read authorizes no action.

import { useCallback, useEffect, useState } from "react";

import { useRedClient } from "@/components/workspace/RedClientContext";
import { listBuilds, type BuildObject } from "@/lib/redOperationsApi";
import { BuildBoard } from "./BuildBoard";

export function BuildBoardScreen() {
  const { tenantId } = useRedClient();
  const [builds, setBuilds] = useState<BuildObject[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await listBuilds(tenantId);
      setBuilds(page.builds);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load builds");
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="flex-1 min-h-0 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="mb-4">
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-lg border border-line bg-surface-overlay px-3 py-1.5 text-xs font-medium text-fg hover:border-line-strong"
          >
            Refresh
          </button>
        </div>
        <BuildBoard
          builds={builds}
          loading={loading}
          error={error}
          tenantId={tenantId}
        />
      </div>
    </main>
  );
}
