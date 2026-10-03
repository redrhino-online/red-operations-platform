// Approval inbox container (Q39; SPEC.md section 8). It owns the tenant-scoped
// read from `GET /red/approvals` and hands the version-specific approvals to the
// presentational `ApprovalInbox`. It can approve nothing; a read authorizes no
// action.

"use client";

import { useCallback, useEffect, useState } from "react";

import { RedOperationsApi, type ApprovalRecord } from "@/shared/api/client";
import { ApprovalInbox } from "./ApprovalInbox";

const PILOT_TENANT = process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";

export function ApprovalInboxScreen() {
  const [tenantId, setTenantId] = useState(PILOT_TENANT);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const api = new RedOperationsApi();
      const page = await api.listApprovals(tenantId);
      setApprovals(page.approvals);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load approvals",
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
      <ApprovalInbox
        approvals={approvals}
        loading={loading}
        error={error}
        tenantId={tenantId}
      />
    </div>
  );
}
