import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import type {
  EngagementProductionView,
  StageProductionView,
} from "@/shared/api/client";
import {
  assetPins,
  ClientWorkspaceOverview,
} from "./ClientWorkspaceOverview";
import { ClientWorkspaceOverviewScreen } from "./ClientWorkspaceOverviewScreen";

function stage(overrides: Partial<StageProductionView> = {}): StageProductionView {
  return {
    stage_number: 1,
    name: "Diagnose",
    checkpoint: "Avatar Locked",
    status: "in_progress",
    required_asset_kinds: ["awareness-map"],
    approved_assets: [{ asset_id: "diagnosis-package", version: 2 }],
    missing_asset_kinds: ["audience-reach-estimate"],
    accountable_role: "market-lead",
    approver_role: "client-approver",
    dependencies: [0],
    blocking_dependencies: [0],
    assigned_owner: "market-lead",
    recorded_approver: null,
    due_on: "2026-10-10",
    next_action: "Submit the audience reach estimate",
    blockers: ["stage 0 gate not approved"],
    entered_at: "2026-10-01",
    is_approved: false,
    ...overrides,
  };
}

function view(
  overrides: Partial<EngagementProductionView> = {},
): EngagementProductionView {
  return {
    engagement: "3fmindset",
    tenant_id: "3fmindset",
    template_version: "stage-zero-to-ten@1",
    current_stage_number: 1,
    next_approval_stage_number: 1,
    blocked_stage_numbers: [1],
    progress: {
      approved_gates: 1,
      total_gates: 11,
      verified_post_launch_milestones: 0,
      activity_entries: 4,
      verified_progress: 1,
      gates_remaining: 10,
    },
    stages: [stage()],
    metric_reporting: [],
    ...overrides,
  };
}

describe("assetPins", () => {
  it("renders each exact asset version as provenance", () => {
    expect(
      assetPins([
        { asset_id: "diagnosis-package", version: 2 },
        { asset_id: "awareness-map", version: 1 },
      ]),
    ).toEqual(["diagnosis-package@v2", "awareness-map@v1"]);
  });
});

describe("ClientWorkspaceOverview", () => {
  it("shows state, exact pinned versions, dependency blockers and next action", () => {
    render(<ClientWorkspaceOverview view={view()} />);

    expect(screen.getByText("Diagnose")).toBeInTheDocument();
    expect(screen.getByText("Avatar Locked")).toBeInTheDocument();
    expect(screen.getByText("diagnosis-package@v2")).toBeInTheDocument();
    expect(
      screen.getByText("Submit the audience reach estimate"),
    ).toBeInTheDocument();
    expect(screen.getByText("market-lead")).toBeInTheDocument();
    expect(screen.getByText("audience-reach-estimate")).toBeInTheDocument();
  });

  it("keeps verified progress apart from activity entries", () => {
    render(<ClientWorkspaceOverview view={view()} />);

    const progress = screen.getByTestId("verified-progress");
    expect(progress).toHaveTextContent("1 of 11 gates approved");
    expect(progress).toHaveTextContent("4 activity entries");
    expect(progress).not.toHaveTextContent("5");
  });

  it("surfaces an error and a loading state honestly", () => {
    render(<ClientWorkspaceOverview view={null} error="boom" loading />);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading workspace overview",
    );
  });
});

describe("ClientWorkspaceOverviewScreen", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the tenant-scoped production view and renders it", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify(view()),
    });
    vi.stubGlobal("fetch", fetcher);

    render(<ClientWorkspaceOverviewScreen />);

    await waitFor(() =>
      expect(screen.getByText("Diagnose")).toBeInTheDocument(),
    );
    expect(fetcher).toHaveBeenCalledWith(
      expect.stringContaining(
        "/red/clients/3fmindset/engagements/3fmindset/production-view?on=",
      ),
      expect.objectContaining({ method: "GET" }),
    );
  });
});
