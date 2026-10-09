import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import {
  RedClientProvider,
  useRedClient,
} from "@/components/workspace/RedClientContext";
import RedClientPicker from "@/components/workspace/RedClientPicker";
import {
  RED_CLIENT_STORAGE_KEY,
  parseSelection,
  resolveSelection,
  serializeSelection,
} from "@/components/workspace/redClientSelection";
import type { RedWorkspace } from "@/lib/redClientApi";

// K2 (SPEC.md section 14 condition 3): the shared client context loads the
// tenant-scoped RED workspaces listing, persists the selection, and the shell
// picker changes it. These tests render the additive cockpit components; they
// approve nothing, spend nothing and deploy nothing.

function workspace(id: string): RedWorkspace {
  return {
    workspace_id: id,
    tenant_id: "3fmindset",
    lifecycle: "intake",
    authorities: [],
    children: [],
  };
}

function listing(ids: string[]) {
  return {
    tenant_id: "3fmindset",
    total: ids.length,
    limit: 50,
    offset: 0,
    workspaces: ids.map(workspace),
  };
}

function Probe() {
  const { workspaceId, loading, error } = useRedClient();
  return (
    <span data-testid="probe">
      {loading ? "loading" : error ? `error:${error}` : workspaceId}
    </span>
  );
}

const fetchMock = vi.fn();

beforeEach(() => {
  window.localStorage.clear();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("redClientSelection", () => {
  it("round-trips a selection and rejects corrupt entries", () => {
    expect(parseSelection(serializeSelection({ tenantId: "t", workspaceId: "w" }))).toEqual({
      tenantId: "t",
      workspaceId: "w",
    });
    expect(parseSelection(null)).toBeNull();
    expect(parseSelection("not json")).toBeNull();
    expect(parseSelection('{"tenantId":"t"}')).toBeNull();
  });

  it("keeps a stored workspace that still exists, else falls back to the first", () => {
    const workspaces = [workspace("ws-3f"), workspace("ws-other")];
    expect(resolveSelection({ tenantId: "3fmindset", workspaceId: "ws-other" }, "3fmindset", workspaces)).toEqual(
      { tenantId: "3fmindset", workspaceId: "ws-other" },
    );
    expect(resolveSelection({ tenantId: "3fmindset", workspaceId: "gone" }, "3fmindset", workspaces)).toEqual(
      { tenantId: "3fmindset", workspaceId: "ws-3f" },
    );
    expect(resolveSelection(null, "3fmindset", [])).toBeNull();
  });
});

describe("RedClientProvider", () => {
  it("loads the tenant-scoped listing and defaults to the first workspace", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => listing(["ws-3f", "ws-other"]) });

    render(
      <RedClientProvider>
        <Probe />
      </RedClientProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("probe").textContent).toBe("ws-3f"));
    expect(fetchMock).toHaveBeenCalledWith(
      "/red/clients?tenant_id=3fmindset",
      expect.objectContaining({ headers: { Accept: "application/json" } }),
    );
    expect(JSON.parse(window.localStorage.getItem(RED_CLIENT_STORAGE_KEY) ?? "null")).toEqual({
      tenantId: "3fmindset",
      workspaceId: "ws-3f",
    });
  });

  it("restores a persisted selection when the workspace still exists", async () => {
    window.localStorage.setItem(
      RED_CLIENT_STORAGE_KEY,
      JSON.stringify({ tenantId: "3fmindset", workspaceId: "ws-other" }),
    );
    fetchMock.mockResolvedValue({ ok: true, json: async () => listing(["ws-3f", "ws-other"]) });

    render(
      <RedClientProvider>
        <Probe />
      </RedClientProvider>,
    );

    await waitFor(() => expect(screen.getByTestId("probe").textContent).toBe("ws-other"));
  });

  it("surfaces a listing failure instead of a silent empty state", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 422, json: async () => ({}) });

    render(
      <RedClientProvider>
        <Probe />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("probe").textContent).toBe(
        "error:RED workspaces listing failed (422)",
      ),
    );
  });
});

describe("RedClientPicker", () => {
  it("changes the selection and persists it", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => listing(["ws-3f", "ws-other"]) });

    render(
      <RedClientProvider>
        <RedClientPicker />
      </RedClientProvider>,
    );

    const select = await screen.findByLabelText("RED workspace");
    fireEvent.change(select, { target: { value: "ws-other" } });

    await waitFor(() =>
      expect(
        JSON.parse(window.localStorage.getItem(RED_CLIENT_STORAGE_KEY) ?? "null"),
      ).toEqual({ tenantId: "3fmindset", workspaceId: "ws-other" }),
    );
  });
});
