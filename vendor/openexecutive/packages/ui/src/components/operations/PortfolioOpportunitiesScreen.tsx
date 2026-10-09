"use client";

// Portfolio opportunities container, native cockpit page (K6; SPEC.md section 14
// conditions 2 and 3). Additive file (ADR 0014). It reads the shared workspace
// selection from `useRedClient()` (K2) and owns the tenant-scoped read of the
// portfolio opportunity register; there is no per-screen free-text tenant input.
// The register holds proposals only; this screen can approve no investment and
// starts no spend or launch.

import { useCallback, useEffect, useState } from "react";

import { useRedClient } from "@/components/workspace/RedClientContext";
import {
  listOpportunities,
  type PortfolioOpportunity,
} from "@/lib/redOperationsApi";
import { PortfolioOpportunities } from "./PortfolioOpportunities";

export function PortfolioOpportunitiesScreen() {
  const { tenantId } = useRedClient();
  const [opportunities, setOpportunities] = useState<PortfolioOpportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const page = await listOpportunities(tenantId);
      setOpportunities(page.opportunities);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load portfolio opportunities",
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
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="mb-4">
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-lg border border-line bg-surface-overlay px-3 py-1.5 text-xs font-medium text-fg hover:border-line-strong"
          >
            Refresh
          </button>
        </div>
        <PortfolioOpportunities
          opportunities={opportunities}
          loading={loading}
          error={error}
          tenantId={tenantId}
        />
      </div>
    </main>
  );
}
