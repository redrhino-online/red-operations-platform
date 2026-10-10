import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { RedClientProvider } from "@/components/workspace/RedClientContext";
import { ApprovalInbox } from "@/components/operations/ApprovalInbox";
import { ApprovalInboxScreen } from "@/components/operations/ApprovalInboxScreen";
import type { ApprovalRecord, AwaitingApprovalRun } from "@/lib/redOperationsApi";

// K12 (SPEC.md section 14 condition 8): the approval inbox and the cockpit
// Review queue are one approval experience, so the inbox surfaces the pipeline
// gates waiting for their RED approval with the exact version each run pins.
// These tests render the additive cockpit components; they approve nothing,
// spend nothing and deploy nothing.

function approval(): ApprovalRecord {
  return {
    tenant_id: "3fmindset",
    stage_number: 0,
    asset_id: "client-record",
    version: 1,
    scope: "stage-0",
    outcome: "approved",
    approver: "client-authority",
    requested_by: "discovery",
    expires_on: "2027-10-03",
    decided_on: "2026-10-03",
  };
}

function waitingRun(overrides: Partial<AwaitingApprovalRun> = {}): AwaitingApprovalRun {
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

beforeEach(() => {
  window.localStorage.clear();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ApprovalInbox pending gate approvals", () => {
  it("surfaces the pending gates with the exact pinned version", () => {
    render(
      <ApprovalInbox
        approvals={[approval()]}
        awaiting={[waitingRun()]}
        tenantId="3fmindset"
      />,
    );
    expect(screen.getByTestId("pending-gate-count").textContent).toContain(
      "1 pipeline gate",
    );
    expect(screen.getByTestId("pending-gate-run-1").textContent).toContain(
      "gate-0",
    );
    expect(screen.getByTestId("pending-gate-run-1").textContent).toContain(
      "red-stage-0-10-pipeline@1.0",
    );
  });

  it("shows the empty state when no gate is waiting", () => {
    render(
      <ApprovalInbox approvals={[]} awaiting={[]} tenantId="3fmindset" />,
    );
    expect(screen.getByTestId("pending-gate-count").textContent).toContain(
      "0 pipeline gates",
    );
    expect(screen.getByText("No pipeline gate is waiting for an approval.")).toBeTruthy();
  });
});

describe("the approval inbox reads the pending gates with the context tenant", () => {
  it("fetches the awaiting-approval read and has no free-text tenant input", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 1,
          limit: 50,
          offset: 0,
          workspaces: [
            {
              workspace_id: "ws-3f",
              tenant_id: "3fmindset",
              lifecycle: "intake",
              authorities: [],
              children: [],
            },
          ],
        });
      }
      if (url.startsWith("/red/approvals?")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 0,
          limit: 50,
          offset: 0,
          approvals: [],
        });
      }
      if (url.includes("/workflows/awaiting-approval")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 1,
          runs: [waitingRun()],
        });
      }
      throw new Error(`unexpected fetch ${url}`);
    });

    render(
      <RedClientProvider>
        <ApprovalInboxScreen />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("pending-gate-count").textContent).toContain(
        "1 pipeline gate",
      ),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).includes(
          "/red/clients/3fmindset/workflows/awaiting-approval",
        ),
      ),
    ).toBe(true);
    expect(screen.queryByLabelText("Tenant")).toBeNull();
  });
});
