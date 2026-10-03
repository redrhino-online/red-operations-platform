import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import type {
  ClientWorkspace,
  StageProductionView,
} from "@/shared/api/client";
import {
  AuthoritySettings,
  approvalScopes,
  approverLabel,
  authorityHolders,
} from "./AuthoritySettings";
import { AuthoritySettingsScreen } from "./AuthoritySettingsScreen";

function workspace(overrides: Partial<ClientWorkspace> = {}): ClientWorkspace {
  return {
    workspace_id: "ws-3f",
    tenant_id: "3fmindset",
    lifecycle: "intake",
    authorities: [
      { actor: "red-principal", authority: "client-designated-authority" },
    ],
    children: [],
    ...overrides,
  };
}

function stage(
  overrides: Partial<StageProductionView> = {},
): StageProductionView {
  return {
    stage_number: 0,
    name: "Intake",
    checkpoint: "Production Ready",
    status: "working",
    required_asset_kinds: [],
    approved_assets: [],
    missing_asset_kinds: [],
    accountable_role: "engagement-lead",
    approver_role: "client-designated-authority",
    dependencies: [],
    blocking_dependencies: [],
    assigned_owner: null,
    recorded_approver: null,
    due_on: null,
    next_action: "collect scope",
    blockers: [],
    entered_at: null,
    is_approved: false,
    ...overrides,
  };
}

describe("authorityHolders", () => {
  it("flattens each workspace's authority registry with its workspace id", () => {
    const holders = authorityHolders([
      workspace({
        authorities: [
          { actor: "red-principal", authority: "client-designated-authority" },
          { actor: "client-owner", authority: "billing-approver" },
        ],
      }),
    ]);
    expect(holders).toHaveLength(2);
    expect(holders[0]).toEqual({
      workspace_id: "ws-3f",
      actor: "red-principal",
      authority: "client-designated-authority",
    });
    expect(holders[1].actor).toBe("client-owner");
  });
});

describe("approvalScopes", () => {
  it("maps each stage to its approver scope", () => {
    const scopes = approvalScopes([
      stage({ recorded_approver: "client-owner", is_approved: true }),
    ]);
    expect(scopes[0]).toEqual({
      stage_number: 0,
      name: "Intake",
      checkpoint: "Production Ready",
      accountable_role: "engagement-lead",
      approver_role: "client-designated-authority",
      recorded_approver: "client-owner",
      is_approved: true,
    });
  });
});

describe("approverLabel", () => {
  it("shows an unrecorded approver honestly", () => {
    expect(approverLabel(approvalScopes([stage()])[0])).toBe("not recorded");
    expect(
      approverLabel(approvalScopes([stage({ recorded_approver: "c" })])[0]),
    ).toBe("c");
  });
});

describe("AuthoritySettings", () => {
  it("renders the authorities and the per-stage gate scopes", () => {
    render(
      <AuthoritySettings
        workspaces={[workspace()]}
        stages={[
          stage({ stage_number: 0 }),
          stage({
            stage_number: 1,
            name: "Diagnose",
            checkpoint: "Avatar Locked",
            recorded_approver: "client-owner",
            is_approved: true,
          }),
        ]}
        tenantId="3fmindset"
      />,
    );

    expect(screen.getByTestId("authority-holder-red-principal")).toHaveTextContent(
      "client-designated-authority",
    );
    expect(screen.getByTestId("approval-scope-0")).toHaveTextContent(
      "approver client-designated-authority, recorded by not recorded",
    );
    expect(screen.getByTestId("approval-scope-1")).toHaveTextContent(
      "recorded by client-owner (approved)",
    );
  });

  it("shows an empty registry honestly", () => {
    render(<AuthoritySettings workspaces={[]} stages={[]} />);
    expect(screen.getByTestId("authority-settings-empty")).toHaveTextContent(
      "No designated authorities recorded.",
    );
  });

  it("surfaces a loading state and error", () => {
    render(
      <AuthoritySettings workspaces={[]} stages={[]} loading error="boom" />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading authority settings",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
  });
});

describe("AuthoritySettingsScreen", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the tenant-scoped workspace registry and gate scopes", async () => {
    const paths: string[] = [];
    const fetcher = vi.fn().mockImplementation((url: string) => {
      const path = String(url);
      paths.push(path);
      if (path.includes("/red/clients?")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({
              tenant_id: "3fmindset",
              total: 1,
              limit: 50,
              offset: 0,
              workspaces: [workspace()],
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({
            engagement: "3fmindset",
            tenant_id: "3fmindset",
            template_version: "1",
            current_stage_number: 0,
            next_approval_stage_number: 1,
            blocked_stage_numbers: [],
            progress: {
              approved_gates: 0,
              total_gates: 11,
              verified_post_launch_milestones: 0,
              activity_entries: 0,
              verified_progress: 0,
              gates_remaining: 11,
            },
            stages: [stage()],
            metric_reporting: [],
          }),
      });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<AuthoritySettingsScreen />);

    await waitFor(() =>
      expect(
        screen.getByTestId("authority-holder-red-principal"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("approval-scope-0")).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(
      paths.some((p) => p.includes("/red/clients?tenant_id=3fmindset")),
    ).toBe(true);
    expect(
      paths.some((p) =>
        p.includes(
          "/red/clients/3fmindset/engagements/3fmindset/production-view",
        ),
      ),
    ).toBe(true);
  });
});
