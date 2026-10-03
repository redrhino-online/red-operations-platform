// Transformation map container (Q36; SPEC.md section 8). It owns the
// tenant-scoped read from `GET /red/methods` and hands the approved methods to
// the presentational `TransformationMap`. It can approve or release nothing; a
// read of an approved method authorizes no action.

"use client";

import { useCallback, useEffect, useState } from "react";

import {
  RedOperationsApi,
  type MethodVersion,
} from "@/shared/api/client";
import { TransformationMap } from "./TransformationMap";

const PILOT_TENANT = process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";

export function TransformationMapScreen() {
  const [tenantId, setTenantId] = useState(PILOT_TENANT);
  const [methods, setMethods] = useState<MethodVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new RedOperationsApi();
      const page = await api.listMethods(tenantId);
      setMethods(page.methods);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load methods");
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
      <TransformationMap
        methods={methods}
        loading={loading}
        error={error}
        tenantId={tenantId}
      />
    </div>
  );
}
