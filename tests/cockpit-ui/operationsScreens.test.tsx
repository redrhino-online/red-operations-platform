import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { RedClientProvider } from "@/components/workspace/RedClientContext";
import { CommandCenter } from "@/components/operations/CommandCenter";
import { CommandCenterScreen } from "@/components/operations/CommandCenterScreen";
import { ClientWorkspaceOverview } from "@/components/operations/ClientWorkspaceOverview";
import { ClientWorkspaceScreen } from "@/components/operations/ClientWorkspaceScreen";
import { ApprovalInbox } from "@/components/operations/ApprovalInbox";
import { ApprovalInboxScreen } from "@/components/operations/ApprovalInboxScreen";
import type {
  ApprovalRecord,
  EngagementProductionView,
  InterventionCard,
} from "@/lib/redOperationsApi";

// K3 (SPEC.md section 14 conditions 2 and 3): the ported command center, client
// workspace and approval inbox render as native cockpit components, read the
// shared workspace context (no per-screen free-text tenant/engagement inputs)
// and surface real error and empty states. These tests render the additive
// cockpit components; they approve nothing, spend nothing and deploy nothing.

function intervention(overrides: Partial<InterventionCard> = {}): InterventionCard {
  return {
    client: "3fmindset",
    reason: "overdue approval",
    severity: "high",
    subject: "offer@v2",
    explanation: "Stage 5 offer approval is overdue",
    evidence: ["gate:5"],
    owner: "governance",
    next_action: "Approve the offer",
    due_on: "2026-10-01",
    state: "open",
    affected_builds: ["build-offer"],
    resolution_note: "",
    ...overrides,
  };
}

function approval(overrides: Partial<ApprovalRecord> = {}): ApprovalRecord {
  return {
    asset_id: "offer",
    version: 1,
    scope: "stage-5",
    requested_by: "production",
    approver: "client-authority",
    outcome: "approved",
    expires_on: null,
    stage_number: 5,
    decided_on: "2026-10-01",
    ...overrides,
  };
}

function productionView(): EngagementProductionView {
  return {
    engagement: "ws-3f",
    tenant_id: "3fmindset",
    template_version: "1.0",
    current_stage_number: 5,
    next_approval_stage_number: 5,
    blocked_stage_numbers: [],
    progress: {
      approved_gates: 5,
      total_gates: 11,
      verified_post_launch_milestones: 0,
      activity_entries: 3,
      verified_progress: 5,
      gates_remaining: 6,
    },
    stages: [
      {
        stage_number: 5,
        name: "Productize",
        checkpoint: "Offer Locked",
        status: "in_review",
        required_asset_kinds: ["offer"],
        approved_assets: [{ asset_id: "offer", version: 2 }],
        missing_asset_kinds: [],
        accountable_role: "offer-design",
        approver_role: "client-authority",
        dependencies: [4],
        blocking_dependencies: [],
        assigned_owner: "production",
        recorded_approver: null,
        due_on: "2026-10-10",
        next_action: "Approve the offer",
        blockers: [],
        entered_at: "2026-10-01",
        is_approved: false,
      },
    ],
  };
}

const fetchMock = vi.fn();

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
        authorities: [],
        children: [],
      },
    ],
  };
}

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

describe("CommandCenter", () => {
  it("renders the ranked cards and counts active interventions", () => {
    render(
      <CommandCenter
        interventions={[
          intervention(),
          intervention({ subject: "dismissed@v1", state: "dismissed" }),
        ]}
        engagement="ws-3f"
        on="2026-10-08"
      />,
    );
    expect(screen.getByTestId("active-count").textContent).toContain(
      "1 active intervention",
    );
    expect(screen.getByText("overdue approval")).toBeTruthy();
    expect(screen.queryByText("dismissed@v1")).toBeNull();
  });

  it("shows an empty state and an error state", () => {
    const { rerender } = render(<CommandCenter interventions={[]} />);
    expect(screen.getByText("No active interventions.")).toBeTruthy();
    rerender(<CommandCenter interventions={[]} error="boom" />);
    expect(screen.getByRole("alert").textContent).toBe("boom");
  });
});

describe("ClientWorkspaceOverview", () => {
  it("renders verified progress apart from activity and the stage rows", () => {
    render(<ClientWorkspaceOverview view={productionView()} />);
    expect(screen.getByTestId("verified-progress").textContent).toContain(
      "5 of 11 gates approved",
    );
    expect(screen.getByText("Productize")).toBeTruthy();
    expect(screen.getByText("offer@v2")).toBeTruthy();
  });

  it("shows an error state", () => {
    render(<ClientWorkspaceOverview view={null} error="nope" />);
    expect(screen.getByRole("alert").textContent).toBe("nope");
  });
});

describe("ApprovalInbox", () => {
  it("groups by asset, pins the exact version and diffs the prior approval", () => {
    render(
      <ApprovalInbox
        approvals={[
          approval({ version: 1, decided_on: "2026-10-01" }),
          approval({ version: 2, decided_on: "2026-10-05", scope: "stage-6" }),
        ]}
        tenantId="3fmindset"
      />,
    );
    expect(screen.getByTestId("approval-count").textContent).toContain("2 approvals");
    expect(screen.getByTestId("latest-version-offer").textContent).toContain(
      "offer@2",
    );
    expect(screen.getByTestId("diff-offer@2-5").textContent).toContain(
      "scope: stage-5",
    );
  });

  it("shows an empty state", () => {
    render(<ApprovalInbox approvals={[]} />);
    expect(screen.getByText("No approvals.")).toBeTruthy();
  });
});

describe("ported cockpit screens read the shared workspace context", () => {
  it("command center fetches with the context tenant/workspace and has no free-text tenant input", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) return jsonResponse(listing());
      if (url.startsWith("/red/interventions?")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          engagement: "ws-3f",
          on: "2026-10-08",
          total: 1,
          interventions: [intervention()],
        });
      }
      throw new Error(`unexpected fetch ${url}`);
    });

    render(
      <RedClientProvider>
        <CommandCenterScreen />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByText("overdue approval")).toBeTruthy(),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/interventions?tenant_id=3fmindset&engagement=ws-3f"),
      ),
    ).toBe(true);
    expect(screen.queryByLabelText("Tenant")).toBeNull();
    expect(screen.queryByLabelText("Engagement")).toBeNull();
  });

  it("client workspace fetches the production view for the selected workspace", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) return jsonResponse(listing());
      if (url.includes("/production-view?")) return jsonResponse(productionView());
      throw new Error(`unexpected fetch ${url}`);
    });

    render(
      <RedClientProvider>
        <ClientWorkspaceScreen />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByText("Productize")).toBeTruthy(),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).includes("/red/clients/3fmindset/engagements/ws-3f/production-view"),
      ),
    ).toBe(true);
  });

  it("approval inbox fetches the tenant-scoped approvals", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) return jsonResponse(listing());
      if (url.startsWith("/red/approvals?")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 1,
          limit: 50,
          offset: 0,
          approvals: [approval()],
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
      expect(screen.getByTestId("approval-count").textContent).toContain("1 approval"),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/approvals?tenant_id=3fmindset"),
      ),
    ).toBe(true);
  });
});
