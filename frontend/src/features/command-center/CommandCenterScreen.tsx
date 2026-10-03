// Command center container (Q33; SPEC.md sections 7 and 8). It owns the
// tenant-scoped read from `GET /red/interventions` and hands the ranked cards
// to the presentational `CommandCenter`. It cannot approve or release anything;
// a read of a card authorizes no action.

"use client";

import { useCallback, useEffect, useState } from "react";

import {
  RedOperationsApi,
  type InterventionCard,
} from "@/shared/api/client";
import { CommandCenter } from "./CommandCenter";

const PILOT_TENANT = process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";
const PILOT_ENGAGEMENT =
  process.env.NEXT_PUBLIC_RED_DEFAULT_ENGAGEMENT ?? "3fmindset";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function CommandCenterScreen() {
  const [tenantId, setTenantId] = useState(PILOT_TENANT);
  const [engagement, setEngagement] = useState(PILOT_ENGAGEMENT);
  const [on, setOn] = useState(today());
  const [interventions, setInterventions] = useState<InterventionCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new RedOperationsApi();
      const page = await api.listInterventions(tenantId, engagement, on);
      setInterventions(page.interventions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cards");
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
      <CommandCenter
        interventions={interventions}
        loading={loading}
        error={error}
        engagement={engagement}
        on={on}
      />
    </div>
  );
}
