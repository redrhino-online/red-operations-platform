"use client";

import { useRedClient } from "@/components/workspace/RedClientContext";

// The shell's persisted workspace/engagement picker (K2; SPEC.md section 14
// condition 3). Additive file (ADR 0014). It selects among the tenant-scoped
// RED workspaces the context loaded; the ported `/operations/*` screens read
// the selection from useRedClient() instead of per-screen free-text defaults.
export default function RedClientPicker() {
  const { tenantId, workspaceId, workspaces, loading, error, setWorkspace } =
    useRedClient();

  if (loading) {
    return <span className="text-xs text-fg-muted">Loading workspaces…</span>;
  }
  if (error) {
    return (
      <span className="text-xs text-red-300" title={error}>
        Workspaces unavailable
      </span>
    );
  }
  if (workspaces.length === 0) {
    return <span className="text-xs text-fg-muted">No workspaces</span>;
  }

  return (
    <label className="flex items-center gap-1.5 text-xs text-fg-muted">
      <span className="hidden sm:inline">Workspace</span>
      <select
        aria-label="RED workspace"
        value={workspaceId ?? ""}
        onChange={(event) => setWorkspace(event.target.value)}
        className="bg-surface-overlay border border-line rounded-lg px-2 py-1 text-xs text-fg"
      >
        {workspaces.map((workspace) => (
          <option key={workspace.workspace_id} value={workspace.workspace_id}>
            {workspace.workspace_id} · {tenantId}
          </option>
        ))}
      </select>
    </label>
  );
}
