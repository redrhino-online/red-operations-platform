"use client";

// Source and claim explorer container, native cockpit page (K5; SPEC.md section
// 14 conditions 2 and 3). Additive file (ADR 0014). It reads the shared
// workspace selection from `useRedClient()` (K2) and owns the tenant-scoped
// reads from `GET /red/clients/{id}/sources` and `GET /red/claims`; there is no
// per-screen free-text tenant input. It can approve or release nothing; a read
// of a source or claim authorizes no action.

import { useCallback, useEffect, useState } from "react";

import { useRedClient } from "@/components/workspace/RedClientContext";
import {
  listClaims,
  listSources,
  type Claim,
  type SourceRecord,
} from "@/lib/redOperationsApi";
import { SourceClaimExplorer } from "./SourceClaimExplorer";

export function SourceClaimExplorerScreen() {
  const { tenantId } = useRedClient();
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sourcePage, claimPage] = await Promise.all([
        listSources(tenantId),
        listClaims(tenantId),
      ]);
      setSources(sourcePage.sources);
      setClaims(claimPage.claims);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sources");
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
        <SourceClaimExplorer
          sources={sources}
          claims={claims}
          loading={loading}
          error={error}
          tenantId={tenantId}
        />
      </div>
    </main>
  );
}
