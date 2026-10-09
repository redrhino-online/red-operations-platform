"use client";

// Performance review container, native cockpit page (K6; SPEC.md section 14
// conditions 2 and 3). Additive file (ADR 0014). It reads the shared
// workspace/engagement selection from `useRedClient()` (K2) and owns the two
// tenant-scoped reads -- the engagement production view (for the stage 10
// baseline gate) and the stage 10 measurement registry (for the post-launch
// observations); there is no per-screen free-text tenant or engagement input. It
// can approve no baseline and start no optimization; a read grants no authority.

import { useCallback, useEffect, useState } from "react";

import { useRedClient } from "@/components/workspace/RedClientContext";
import {
  getProductionView,
  listMeasurements,
  type EngagementProductionView,
  type MeasurementRecord,
} from "@/lib/redOperationsApi";
import { PerformanceReview } from "./PerformanceReview";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function PerformanceReviewScreen() {
  const { tenantId, workspaceId } = useRedClient();
  const [on, setOn] = useState(today());
  const [view, setView] = useState<EngagementProductionView | null>(null);
  const [measurements, setMeasurements] = useState<MeasurementRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [productionView, measurementPage] = await Promise.all([
        workspaceId
          ? getProductionView(tenantId, workspaceId, on)
          : Promise.resolve(null),
        listMeasurements(tenantId),
      ]);
      setView(productionView);
      setMeasurements(measurementPage.records);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load performance review",
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
        <PerformanceReview
          view={view}
          measurements={measurements}
          loading={loading}
          error={error}
          tenantId={tenantId}
        />
      </div>
    </main>
  );
}
