// RED client context API (K2; SPEC.md section 14 condition 3). Additive file
// (ADR 0014): reads the tenant-scoped RED workspaces listing the cockpit shell
// picker uses. Same-origin `/red` by default; override with
// NEXT_PUBLIC_RED_API_BASE for a local dev run. It approves nothing, spends
// nothing and deploys nothing.

export interface RedWorkspaceAuthority {
  actor: string;
  authority: string;
}

export interface RedWorkspace {
  workspace_id: string;
  tenant_id: string;
  lifecycle: string;
  authorities: RedWorkspaceAuthority[];
  children: string[];
}

export interface RedWorkspaceList {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  workspaces: RedWorkspace[];
}

// The pilot tenant the shell defaults to until a tenant picker exists. The
// seeded 3F workspace lives under this tenant (K1).
export const DEFAULT_RED_TENANT =
  process.env.NEXT_PUBLIC_RED_DEFAULT_TENANT ?? "3fmindset";

function redApiBase(): string {
  return process.env.NEXT_PUBLIC_RED_API_BASE ?? "";
}

// List the client workspaces for one tenant. The RED API scopes the read by
// the required `tenant_id` query parameter, so a different tenant's workspaces
// never appear here.
export async function listRedWorkspaces(
  tenantId: string,
  signal?: AbortSignal,
): Promise<RedWorkspaceList> {
  const url = `${redApiBase()}/red/clients?tenant_id=${encodeURIComponent(tenantId)}`;
  const res = await fetch(url, {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`RED workspaces listing failed (${res.status})`);
  }
  return (await res.json()) as RedWorkspaceList;
}
