// Performance review container (Q42; SPEC.md sections 4 and 8). It owns the two
// tenant-scoped reads -- the engagement production view (for the stage 10
// baseline gate) and the stage 10 measurement registry (for the post-launch
// observations) -- and hands them to the presentational `PerformanceReview`. It
// can approve no baseline and start no optimization; a read grants no authority.

"use client";

import { useCallback, useEffect, useState } from "react";

import {
  RedOperationsApi,
  type EngagementProductionView,
  type MeasurementRecord,
} from "@/shared/api/client";
import { PerformanceReview } from "./PerformanceReview";

const PILOT_TENANT = process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";
const PILOT_ENGAGEMENT =
  process.env.NEXT_PUBLIC_RED_DEFAULT_ENGAGEMENT ?? "3fmindset";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function PerformanceReviewScreen() {
  const [tenantId, setTenantId] = useState(PILOT_TENANT);
  const [engagement, setEngagement] = useState(PILOT_ENGAGEMENT);
  const [on, setOn] = useState(today());
  const [view, setView] = useState<EngagementProductionView | null>(null);
  const [measurements, setMeasurements] = useState<MeasurementRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new RedOperationsApi();
      const [productionView, measurementPage] = await Promise.all([
        api.getProductionView(tenantId, engagement, on),
        api.listMeasurements(tenantId),
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
      <PerformanceReview
        view={view}
        measurements={measurements}
        loading={loading}
        error={error}
        tenantId={tenantId}
      />
    </div>
  );
}
