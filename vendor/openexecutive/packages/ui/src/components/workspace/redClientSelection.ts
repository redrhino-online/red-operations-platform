// Persisted RED client selection (K2; SPEC.md section 14 condition 3). Pure
// helpers so the persistence and resolution rules are unit-testable without a
// DOM. Additive file (ADR 0014).

import type { RedWorkspace } from "@/lib/redClientApi";

export const RED_CLIENT_STORAGE_KEY = "red.client.selection";

export interface RedClientSelection {
  tenantId: string;
  workspaceId: string;
}

// Parse a stored value defensively: a corrupt or partial entry is treated as
// absent rather than crashing the shell.
export function parseSelection(raw: string | null): RedClientSelection | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<RedClientSelection>;
    if (
      typeof parsed?.tenantId === "string" &&
      parsed.tenantId.length > 0 &&
      typeof parsed?.workspaceId === "string" &&
      parsed.workspaceId.length > 0
    ) {
      return { tenantId: parsed.tenantId, workspaceId: parsed.workspaceId };
    }
  } catch {
    // fall through to null
  }
  return null;
}

export function serializeSelection(selection: RedClientSelection): string {
  return JSON.stringify(selection);
}

export function readStoredSelection(storage: Storage | null): RedClientSelection | null {
  if (!storage) return null;
  try {
    return parseSelection(storage.getItem(RED_CLIENT_STORAGE_KEY));
  } catch {
    return null;
  }
}

export function writeStoredSelection(
  storage: Storage | null,
  selection: RedClientSelection,
): void {
  if (!storage) return;
  try {
    storage.setItem(RED_CLIENT_STORAGE_KEY, serializeSelection(selection));
  } catch {
    // Storage can be unavailable (private mode); the in-memory selection stands.
  }
}

// Resolve the selection to render: keep the stored workspace when it still
// exists for the tenant, otherwise fall back to the first listed workspace.
// Returns null when the tenant has no workspaces.
export function resolveSelection(
  stored: RedClientSelection | null,
  tenantId: string,
  workspaces: RedWorkspace[],
): RedClientSelection | null {
  if (stored && stored.tenantId === tenantId) {
    const match = workspaces.find((w) => w.workspace_id === stored.workspaceId);
    if (match) return { tenantId, workspaceId: match.workspace_id };
  }
  const first = workspaces[0];
  return first ? { tenantId, workspaceId: first.workspace_id } : null;
}
