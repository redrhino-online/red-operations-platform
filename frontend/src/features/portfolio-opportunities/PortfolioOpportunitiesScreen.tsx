// Portfolio opportunities container (Q43; SPEC.md sections 3 and 8). It owns the
// tenant-scoped read of the portfolio opportunity register and hands it to the
// presentational `PortfolioOpportunities`. The register holds proposals only;
// this screen can approve no investment and starts no spend or launch.

"use client";

import { useCallback, useEffect, useState } from "react";

import {
  RedOperationsApi,
  type PortfolioOpportunity,
} from "@/shared/api/client";
import { PortfolioOpportunities } from "./PortfolioOpportunities";

const PILOT_TENANT = process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";

export function PortfolioOpportunitiesScreen() {
  const [tenantId, setTenantId] = useState(PILOT_TENANT);
  const [opportunities, setOpportunities] = useState<PortfolioOpportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new RedOperationsApi();
      const page = await api.listOpportunities(tenantId);
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
        <button type="submit">Refresh</button>
      </form>
      <PortfolioOpportunities
        opportunities={opportunities}
        loading={loading}
        error={error}
        tenantId={tenantId}
      />
    </div>
  );
}
