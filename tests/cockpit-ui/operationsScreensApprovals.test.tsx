import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { RedClientProvider } from "@/components/workspace/RedClientContext";
import { ApprovalInbox } from "@/components/operations/ApprovalInbox";
import { ApprovalInboxScreen } from "@/components/operations/ApprovalInboxScreen";
import type {
  ApprovalRecord,
  AwaitingApprovalRun,
} from "@/lib/redOperationsApi";

// U2 (asset review and approval spec sections 3.2, 3.4 and 7): every pending
// pipeline gate in the approval inbox gains an Approve control whose form
// collects the actor and a required reason and posts exactly {actor, reason};
// a backend refusal renders its error verbatim with no optimistic change, and
// a success refreshes the pending list so the run leaves it.

function approval(): ApprovalRecord {
  return {
    asset_id: "client-record",
    version: 1,
    scope: "stage-0",
    requested_by: "discovery",
    approver: "client-authority",
    outcome: "approved",
    expires_on: null,
    stage_number: 0,
    decided_on: "2026-10-03",
  };
}

function waitingRun(
  overrides: Partial<AwaitingApprovalRun> = {},
): AwaitingApprovalRun {
  return {
    run_id: "run-1",
    tenant_id: "3fmindset",
    definition_id: "red-stage-0-10-pipeline",
    definition_version: "1.0",
    status: "awaiting_approval",
    completed_steps: ["stage-0"],
    in_progress_step: null,
    pending_approval: "gate-0",
    failure_reason: null,
    next_step: "gate-0",
    event_id: "run-1:3",
    transitions: [],
    ...overrides,
  };
}

const fetchMock = vi.fn();

function jsonResponse(body: unknown) {
  return { ok: true, status: 200, json: async () => body };
}

function refusal(detail: string) {
  return { ok: false, status: 422, json: async () => ({ detail }) };
}

function listing() {
  return {
    tenant_id: "3fmindset",
    total: 1,
    limit: 50,
    offset: 0,
    workspaces: [
      {
        workspace_id: "ws-3f",
        tenant_id: "3fmindset",
        lifecycle: "intake",
        authorities: [
          { actor: "client-authority", authority: "approver" },
          { actor: "demo-red-principal", authority: "stage-owner" },
        ],
        children: [],
      },
    ],
  };
}

function approvalsPage() {
  return {
    tenant_id: "3fmindset",
    total: 1,
    limit: 50,
    offset: 0,
    approvals: [approval()],
  };
}

function awaitingPage(runs: AwaitingApprovalRun[]) {
  return {
    tenant_id: "3fmindset",
    total: runs.length,
    limit: 50,
    offset: 0,
    runs,
  };
}

function openApproveForm() {
  fireEvent.click(screen.getByTestId("approve-run-1"));
  fireEvent.change(screen.getByLabelText("Actor"), {
    target: { value: "client-authority" },
  });
  fireEvent.change(screen.getByLabelText("Reason"), {
    target: { value: "the gate passed review" },
  });
}

beforeEach(() => {
  window.localStorage.clear();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ApprovalInbox approve control (U2)", () => {
  it("renders an Approve control per pending run", () => {
    render(
      <ApprovalInbox
        approvals={[approval()]}
        awaiting={[
          waitingRun(),
          waitingRun({ run_id: "run-2", pending_approval: "gate-1" }),
        ]}
        tenantId="3fmindset"
      />,
    );
    expect(screen.getByTestId("approve-run-1")).toBeTruthy();
    expect(screen.getByTestId("approve-run-2")).toBeTruthy();
  });

  it("opens a form that collects actor and reason and posts exactly {actor, reason}", async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));
    render(
      <ApprovalInbox
        approvals={[]}
        awaiting={[waitingRun()]}
        tenantId="3fmindset"
      />,
    );
    openApproveForm();
    fireEvent.click(screen.getByText("Confirm approval"));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe(
      "/red/clients/3fmindset/workflows/run-1/approval",
    );
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({
      actor: "client-authority",
      reason: "the gate passed review",
    });
  });

  it("suggests the workspace authorities as actor options with free-text fallback", () => {
    render(
      <ApprovalInbox
        approvals={[]}
        awaiting={[waitingRun()]}
        tenantId="3fmindset"
        authorities={["client-authority", "demo-red-principal"]}
      />,
    );
    fireEvent.click(screen.getByTestId("approve-run-1"));
    const input = screen.getByLabelText("Actor") as HTMLInputElement;
    expect(input.getAttribute("list")).toBe("approve-actor-options-run-1");
    const options = [
      ...document.getElementById("approve-actor-options-run-1")!.querySelectorAll("option"),
    ].map((option) => option.getAttribute("value"));
    expect(options).toEqual(["client-authority", "demo-red-principal"]);
  });

  it("renders a backend refusal verbatim next to the form and records nothing", async () => {
    fetchMock.mockResolvedValue(
      refusal("the run's stage has no passing gate decision"),
    );
    render(
      <ApprovalInbox
        approvals={[]}
        awaiting={[waitingRun()]}
        tenantId="3fmindset"
      />,
    );
    openApproveForm();
    fireEvent.click(screen.getByText("Confirm approval"));

    await waitFor(() =>
      expect(screen.getByTestId("approve-error-run-1").textContent).toBe(
        "the run's stage has no passing gate decision",
      ),
    );
    // No optimistic change: the form stays open for a corrected submission and
    // no refresh was triggered.
    expect(screen.getByTestId("approve-form-run-1")).toBeTruthy();
    expect(screen.queryByTestId("approve-confirmation")).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("ApprovalInboxScreen approval flow (U2)", () => {
  it("suggests the workspace authorities and refreshes the pending list on success", async () => {
    let awaitingReads = 0;
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      const path = String(url);
      if (init?.method === "POST") return jsonResponse({});
      if (path.startsWith("/red/clients?")) return jsonResponse(listing());
      if (path.startsWith("/red/approvals?")) return jsonResponse(approvalsPage());
      if (path.includes("/workflows/awaiting-approval")) {
        awaitingReads += 1;
        return jsonResponse(
          awaitingReads === 1 ? awaitingPage([waitingRun()]) : awaitingPage([]),
        );
      }
      throw new Error(`unexpected fetch ${path}`);
    });

    render(
      <RedClientProvider>
        <ApprovalInboxScreen />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("pending-gate-run-1")).toBeTruthy(),
    );
    // The actor suggestions come from the selected workspace's authority
    // registry the shared context already loaded.
    fireEvent.click(screen.getByTestId("approve-run-1"));
    const options = [
      ...document.getElementById("approve-actor-options-run-1")!.querySelectorAll("option"),
    ].map((option) => option.getAttribute("value"));
    expect(options).toEqual(["client-authority", "demo-red-principal"]);

    fireEvent.change(screen.getByLabelText("Actor"), {
      target: { value: "client-authority" },
    });
    fireEvent.change(screen.getByLabelText("Reason"), {
      target: { value: "the gate passed review" },
    });
    fireEvent.click(screen.getByText("Confirm approval"));

    await waitFor(() =>
      expect(screen.getByTestId("approve-confirmation").textContent).toContain(
        "Run run-1 approved",
      ),
    );
    await waitFor(() =>
      expect(screen.getByTestId("pending-gate-count").textContent).toContain(
        "0 pipeline gates",
      ),
    );
    expect(awaitingReads).toBe(2);
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).includes("/workflows/run-1/approval") &&
          init?.method === "POST",
      ),
    ).toBe(true);
  });
});
