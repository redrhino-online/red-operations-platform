// Source and claim explorer container (Q35; SPEC.md section 8). It owns the
// tenant-scoped reads from `GET /red/clients/{id}/sources` and `GET /red/claims`
// and hands them to the presentational `SourceClaimExplorer`. It can approve or
// release nothing; a read of a source or claim authorizes no action.

"use client";

import { useCallback, useEffect, useState } from "react";

import {
  RedOperationsApi,
  type Claim,
  type SourceRecord,
} from "@/shared/api/client";
import { SourceClaimExplorer } from "./SourceClaimExplorer";

const PILOT_TENANT = process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";

export function SourceClaimExplorerScreen() {
  const [tenantId, setTenantId] = useState(PILOT_TENANT);
  const [sources, setSources] = useState<SourceRecord[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new RedOperationsApi();
      const [sourcePage, claimPage] = await Promise.all([
        api.listSources(tenantId),
        api.listClaims(tenantId),
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
      <SourceClaimExplorer
        sources={sources}
        claims={claims}
        loading={loading}
        error={error}
        tenantId={tenantId}
      />
    </div>
  );
}
