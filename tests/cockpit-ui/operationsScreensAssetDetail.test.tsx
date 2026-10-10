import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { RedClientProvider } from "@/components/workspace/RedClientContext";
import { ClientWorkspaceScreen } from "@/components/operations/ClientWorkspaceScreen";
import type {
  ApprovalRecord,
  DecisionRecord,
  EngagementProductionView,
} from "@/lib/redOperationsApi";

// U1 (asset review and approval spec sections 3.1, 5 and 7): every approved
// asset pin in the client workspace opens the asset detail panel with that
// asset's approval records, gate decisions and, where the kind maps to one, its
// stored content. The API is mocked; the panel approves nothing.

function approval(overrides: Partial<ApprovalRecord> = {}): ApprovalRecord {
  return {
    asset_id: "story",
    version: 1,
    scope: "stage-6",
    requested_by: "production",
    approver: "client-authority",
    outcome: "approved",
    expires_on: null,
    stage_number: 6,
    decided_on: "2026-10-05",
    ...overrides,
  };
}

function decision(overrides: Partial<DecisionRecord> = {}): DecisionRecord {
  return {
    stage_number: 6,
    checkpoint: "Campaign Message Approved",
    disposition: "approved",
    reviewer: "client-authority",
    scope: "stage-6",
    rationale: "The story pins the approved campaign message.",
    checkpoint_evidence: "gate-6 transcript",
    decided_on: "2026-10-05",
    required_assets: [{ asset_id: "story", version: 1 }],
    ...overrides,
  };
}

function productionView(): EngagementProductionView {
  return {
    engagement: "ws-3f",
    tenant_id: "3fmindset",
    template_version: "1.0",
    current_stage_number: 6,
    next_approval_stage_number: 6,
    blocked_stage_numbers: [],
    progress: {
      approved_gates: 6,
      total_gates: 11,
      verified_post_launch_milestones: 0,
      activity_entries: 3,
      verified_progress: 6,
      gates_remaining: 5,
    },
    stages: [
      {
        stage_number: 0,
        name: "Intake",
        checkpoint: "Production Ready",
        status: "approved",
        required_asset_kinds: ["access-checklist"],
        approved_assets: [{ asset_id: "access-checklist", version: 1 }],
        missing_asset_kinds: [],
        accountable_role: "discovery",
        approver_role: "client-authority",
        dependencies: [],
        blocking_dependencies: [],
        assigned_owner: "discovery",
        recorded_approver: "client-authority",
        due_on: null,
        next_action: "",
        blockers: [],
        entered_at: "2026-10-01",
        is_approved: true,
      },
      {
        stage_number: 6,
        name: "Message",
        checkpoint: "Campaign Message Approved",
        status: "in_review",
        required_asset_kinds: ["story"],
        approved_assets: [{ asset_id: "story", version: 1 }],
        missing_asset_kinds: [],
        accountable_role: "message-design",
        approver_role: "client-authority",
        dependencies: [5],
        blocking_dependencies: [],
        assigned_owner: "production",
        recorded_approver: null,
        due_on: "2026-10-10",
        next_action: "Approve the message",
        blockers: [],
        entered_at: "2026-10-04",
        is_approved: false,
      },
    ],
  };
}

const fetchMock = vi.fn();

function jsonResponse(body: unknown) {
  return { ok: true, status: 200, json: async () => body };
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
        authorities: [],
        children: [],
      },
    ],
  };
}

function approvalsList() {
  return {
    tenant_id: "3fmindset",
    total: 2,
    limit: 50,
    offset: 0,
    approvals: [
      approval(),
      approval({
        asset_id: "access-checklist",
        stage_number: 0,
        scope: "stage-0",
        decided_on: "2026-10-01",
      }),
    ],
  };
}

function decisionsList() {
  return {
    tenant_id: "3fmindset",
    total: 2,
    limit: 50,
    offset: 0,
    decisions: [
      decision(),
      decision({
        stage_number: 0,
        checkpoint: "Production Ready",
        rationale: "The intake checklist is complete.",
        checkpoint_evidence: "gate-0 transcript",
        required_assets: [{ asset_id: "access-checklist", version: 1 }],
      }),
    ],
  };
}

function messageList() {
  return {
    tenant_id: "3fmindset",
    total: 1,
    limit: 50,
    offset: 0,
    messages: [
      {
        message_id: "msg-3f-1",
        owner: "production",
        avatar: "owner-operator",
        currency: "time",
        problem: "no predictable pipeline",
        promise: "a predictable pipeline in 90 days",
        cta: "book the diagnostic",
        problem_hierarchy: ["surface problem", "core problem"],
        desired_outcome: "a predictable pipeline",
        proof_objections: ["no proof yet"],
        story: "The owner is stuck trading time for leads.",
        method_explanation: "diagnose, then productize",
        lead_magnet: "the pipeline audit",
        hook: "Stop buying leads.",
        angles: ["time", "money"],
        landing_message: "Book a diagnostic call.",
        authority_amplifier_outline: "a weekly authority video",
        product_offer_id: "offer-1",
        is_approved: true,
      },
    ],
  };
}

function installApi(approvals: unknown = approvalsList()) {
  fetchMock.mockImplementation(async (url: string) => {
    if (url.startsWith("/red/clients?")) return jsonResponse(listing());
    if (url.includes("/production-view?")) return jsonResponse(productionView());
    if (url.startsWith("/red/approvals?")) return jsonResponse(approvals);
    if (url.startsWith("/red/decisions?")) return jsonResponse(decisionsList());
    if (url.startsWith("/red/messages?")) return jsonResponse(messageList());
    throw new Error(`unexpected fetch ${url}`);
  });
}

function renderScreen() {
  return render(
    <RedClientProvider>
      <ClientWorkspaceScreen />
    </RedClientProvider>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the client workspace asset detail panel (U1)", () => {
  it("opens the panel from a pin with that asset's approvals and gate decisions", async () => {
    installApi();
    renderScreen();

    await waitFor(() => expect(screen.getByText("Message")).toBeTruthy());

    // Lazy: nothing beyond the production view is fetched before a pin opens.
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/approvals?"),
      ),
    ).toBe(false);

    fireEvent.click(screen.getByTestId("asset-pin-story@v1"));

    await waitFor(() =>
      expect(screen.getByTestId("asset-detail-panel")).toBeTruthy(),
    );

    const approvals = screen.getByTestId("asset-detail-approvals");
    expect(approvals.textContent).toContain("Version 1");
    expect(approvals.textContent).toContain("client-authority");
    expect(approvals.textContent).toContain("stage-6");
    expect(approvals.textContent).not.toContain("stage-0");

    const decisions = screen.getByTestId("asset-detail-decisions");
    expect(decisions.textContent).toContain("Campaign Message Approved");
    expect(decisions.textContent).toContain(
      "The story pins the approved campaign message.",
    );
    expect(decisions.textContent).toContain("gate-6 transcript");
    expect(decisions.textContent).not.toContain(
      "The intake checklist is complete.",
    );

    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/approvals?tenant_id=3fmindset"),
      ),
    ).toBe(true);
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/decisions?tenant_id=3fmindset"),
      ),
    ).toBe(true);
  });

  it("renders the mapped message content for a stage-6 kind", async () => {
    installApi();
    renderScreen();

    await waitFor(() => expect(screen.getByText("Message")).toBeTruthy());
    fireEvent.click(screen.getByTestId("asset-pin-story@v1"));

    await waitFor(() =>
      expect(
        screen.getByTestId("asset-detail-content").textContent,
      ).toContain("msg-3f-1"),
    );

    const content = screen.getByTestId("asset-detail-content");
    expect(content.textContent).toContain(
      "The owner is stuck trading time for leads.",
    );
    expect(content.textContent).toContain("Stop buying leads.");
    expect(content.textContent).toContain("Angles: time, money");
    expect(content.textContent).toContain("Book a diagnostic call.");
    expect(content.textContent).toContain("(approved)");
  });

  it("renders the provenance-only note for a kind with no content source", async () => {
    installApi();
    renderScreen();

    await waitFor(() => expect(screen.getByText("Intake")).toBeTruthy());
    fireEvent.click(screen.getByTestId("asset-pin-access-checklist@v1"));

    await waitFor(() =>
      expect(screen.getByTestId("asset-detail-no-content")).toBeTruthy(),
    );
    expect(screen.getByTestId("asset-detail-no-content").textContent).toBe(
      "No stored content for this asset kind — the approval records above are the record of what was approved.",
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/messages?"),
      ),
    ).toBe(false);

    const approvals = screen.getByTestId("asset-detail-approvals");
    expect(approvals.textContent).toContain("stage-0");
    const decisions = screen.getByTestId("asset-detail-decisions");
    expect(decisions.textContent).toContain(
      "The intake checklist is complete.",
    );
  });

  it("renders the explicit empty state when the asset has no approval records", async () => {
    installApi({
      tenant_id: "3fmindset",
      total: 0,
      limit: 50,
      offset: 0,
      approvals: [],
    });
    renderScreen();

    await waitFor(() => expect(screen.getByText("Message")).toBeTruthy());
    fireEvent.click(screen.getByTestId("asset-pin-story@v1"));

    await waitFor(() =>
      expect(screen.getByTestId("asset-detail-approvals-empty")).toBeTruthy(),
    );
    expect(
      screen.getByTestId("asset-detail-approvals-empty").textContent,
    ).toContain("No approval records found");
  });
});
