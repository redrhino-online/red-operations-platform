// Launch readiness container (Q41; SPEC.md section 8). It owns the tenant-scoped
// read from `GET /red/launch-qas` and hands the authorized stage 9 launch QAs to
// the presentational `LaunchReadiness`. It can authorize no traffic; a read
// grants no authority.

"use client";

import { useCallback, useEffect, useState } from "react";

import { RedOperationsApi, type LaunchQA } from "@/shared/api/client";
import { LaunchReadiness } from "./LaunchReadiness";

const PILOT_TENANT = process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";

export function LaunchReadinessScreen() {
  const [tenantId, setTenantId] = useState(PILOT_TENANT);
  const [launchQas, setLaunchQas] = useState<LaunchQA[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new RedOperationsApi();
      const page = await api.listLaunchQAs(tenantId);
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
      <LaunchReadiness
        launchQas={launchQas}
        loading={loading}
        error={error}
        tenantId={tenantId}
      />
    </div>
  );
}
