"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  DEFAULT_RED_TENANT,
  listRedWorkspaces,
  type RedWorkspace,
} from "@/lib/redClientApi";
import {
  readStoredSelection,
  resolveSelection,
  writeStoredSelection,
} from "@/components/workspace/redClientSelection";

// The shared RED client context (K2; SPEC.md section 14 condition 3). Additive
// file (ADR 0014). It loads the tenant-scoped RED workspaces listing once for
// the shell, persists the selected workspace/engagement, and exposes it to the
// ported `/operations/*` screens so they read one selection instead of
// per-screen free-text tenant/engagement defaults. It approves nothing, spends
// nothing and deploys nothing.
interface RedClientContextValue {
  tenantId: string;
  workspaceId: string | null;
  workspaces: RedWorkspace[];
  loading: boolean;
  error: string | null;
  setWorkspace: (workspaceId: string) => void;
  refresh: () => Promise<void>;
}

const RedClientContext = createContext<RedClientContextValue | null>(null);

function browserStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function RedClientProvider({
  children,
  tenantId = DEFAULT_RED_TENANT,
}: {
  children: React.ReactNode;
  tenantId?: string;
}) {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<RedWorkspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Only the latest request may write, so a slow first read cannot overwrite a
  // newer refresh.
  const seqRef = useRef(0);

  const refresh = useCallback(async () => {
    const seq = ++seqRef.current;
    setLoading(true);
    setError(null);
    try {
      const listing = await listRedWorkspaces(tenantId);
      if (seq !== seqRef.current) return;
      setWorkspaces(listing.workspaces);
      const resolved = resolveSelection(
        readStoredSelection(browserStorage()),
        tenantId,
        listing.workspaces,
      );
      setWorkspaceId(resolved?.workspaceId ?? null);
      if (resolved) writeStoredSelection(browserStorage(), resolved);
    } catch (err) {
      if (seq !== seqRef.current) return;
      setError(err instanceof Error ? err.message : "RED workspaces listing failed");
    } finally {
      if (seq === seqRef.current) setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setWorkspace = useCallback(
    (next: string) => {
      setWorkspaceId(next);
      writeStoredSelection(browserStorage(), { tenantId, workspaceId: next });
    },
    [tenantId],
  );

  const value = useMemo(
    () => ({ tenantId, workspaceId, workspaces, loading, error, setWorkspace, refresh }),
    [tenantId, workspaceId, workspaces, loading, error, setWorkspace, refresh],
  );
  return <RedClientContext.Provider value={value}>{children}</RedClientContext.Provider>;
}

export function useRedClient(): RedClientContextValue {
  const ctx = useContext(RedClientContext);
  if (!ctx) throw new Error("useRedClient must be used inside <RedClientProvider>");
  return ctx;
}
