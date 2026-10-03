import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import type { ApprovalRecord } from "@/shared/api/client";
import {
  ApprovalInbox,
  approvalDiff,
  approvalHistories,
  exactVersion,
  priorApproval,
} from "./ApprovalInbox";
import { ApprovalInboxScreen } from "./ApprovalInboxScreen";

function approval(overrides: Partial<ApprovalRecord> = {}): ApprovalRecord {
  return {
    asset_id: "avatar",
    version: 1,
    scope: "downstream production use",
    requested_by: "red-owner-1",
    approver: "client-approver-1",
    outcome: "approved",
    expires_on: null,
    stage_number: 1,
    decided_on: "2026-10-02",
    ...overrides,
  };
}

const AVATAR_V1 = approval();
const AVATAR_V2 = approval({
  version: 2,
  scope: "stage 6 campaign use",
  approver: "client-approver-2",
  stage_number: 6,
  decided_on: "2026-10-05",
});
const INTAKE = approval({
  asset_id: "intake-package",
  version: 1,
  stage_number: 0,
  decided_on: "2026-10-01",
});

describe("exactVersion", () => {
  it("pins the asset kind and version", () => {
    expect(exactVersion(AVATAR_V1)).toBe("avatar@1");
  });
});

describe("approvalHistories", () => {
  it("groups by asset kind, orders each history ascending and surfaces latest", () => {
    const histories = approvalHistories([AVATAR_V2, INTAKE, AVATAR_V1]);
    expect(histories.map((h) => h.asset_id)).toEqual(["avatar", "intake-package"]);
    const avatar = histories[0];
    expect(avatar.history.map((a) => a.version)).toEqual([1, 2]);
    expect(avatar.latest.version).toBe(2);
  });

  it("returns nothing for no approvals", () => {
    expect(approvalHistories([])).toEqual([]);
  });
});

describe("priorApproval", () => {
  it("returns the previous version of the same asset", () => {
    const history = [AVATAR_V1, AVATAR_V2];
    expect(priorApproval(history, AVATAR_V2)).toEqual(AVATAR_V1);
  });

  it("returns null for the baseline approval", () => {
    expect(priorApproval([AVATAR_V1, AVATAR_V2], AVATAR_V1)).toBeNull();
  });
});

describe("approvalDiff", () => {
  it("reports each changed field with its exact prior and current value", () => {
    const diff = approvalDiff(AVATAR_V1, AVATAR_V2);
    expect(diff).toEqual([
      { field: "version", from: "1", to: "2" },
      { field: "scope", from: "downstream production use", to: "stage 6 campaign use" },
      { field: "approver", from: "client-approver-1", to: "client-approver-2" },
      { field: "stage_number", from: "1", to: "6" },
      { field: "decided_on", from: "2026-10-02", to: "2026-10-05" },
    ]);
  });

  it("returns nothing for a baseline approval", () => {
    expect(approvalDiff(null, AVATAR_V1)).toEqual([]);
  });

  it("returns nothing when nothing changed", () => {
    expect(approvalDiff(AVATAR_V1, { ...AVATAR_V1 })).toEqual([]);
  });
});

describe("ApprovalInbox", () => {
  it("renders the exact version and the diff against the prior version", () => {
    render(<ApprovalInbox approvals={[AVATAR_V1, AVATAR_V2]} tenantId="3fmindset" />);

    expect(screen.getByTestId("latest-version-avatar")).toHaveTextContent(
      "Latest exact version: avatar@2",
    );
    expect(screen.getByTestId("diff-avatar@2-6")).toHaveTextContent(
      "version: 1 → 2",
    );
    expect(screen.getByTestId("diff-avatar@2-6")).toHaveTextContent(
      "scope: downstream production use → stage 6 campaign use",
    );
    expect(screen.getByTestId("diff-avatar@1-1")).toHaveTextContent(
      "Baseline approval, no prior version to diff.",
    );
  });

  it("surfaces an error and a loading state honestly", () => {
    render(<ApprovalInbox approvals={[]} error="boom" loading />);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    expect(screen.getByRole("status")).toHaveTextContent("Loading approvals");
  });

  it("shows an empty state when there are no approvals", () => {
    render(<ApprovalInbox approvals={[]} />);
    expect(screen.getByText("No approvals.")).toBeInTheDocument();
  });
});

describe("ApprovalInboxScreen", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the tenant-scoped approvals", async () => {
    const fetcher = vi.fn().mockImplementation((url: string) => {
      expect(String(url)).toContain("/red/approvals?tenant_id=3fmindset");
      return Promise.resolve({
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({
            tenant_id: "3fmindset",
            total: 1,
            limit: 50,
            offset: 0,
            approvals: [AVATAR_V1],
          }),
      });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<ApprovalInboxScreen />);

    await waitFor(() =>
      expect(screen.getByText("Scope: downstream production use")).toBeInTheDocument(),
    );
    expect(fetcher).toHaveBeenCalled();
  });
});
