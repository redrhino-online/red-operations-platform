// Build board container (Q38; SPEC.md section 8). It owns the tenant-scoped read
// from `GET /red/builds` and hands the production work items to the
// presentational `BuildBoard`. It can transition no build and approve nothing; a
// read authorizes no action.

"use client";

import { useCallback, useEffect, useState } from "react";

import { RedOperationsApi, type BuildObject } from "@/shared/api/client";
import { BuildBoard } from "./BuildBoard";

const PILOT_TENANT = process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";

export function BuildBoardScreen() {
  const [tenantId, setTenantId] = useState(PILOT_TENANT);
  const [builds, setBuilds] = useState<BuildObject[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new RedOperationsApi();
      const page = await api.listBuilds(tenantId);
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
      <BuildBoard
        builds={builds}
        loading={loading}
        error={error}
        tenantId={tenantId}
      />
    </div>
  );
}
