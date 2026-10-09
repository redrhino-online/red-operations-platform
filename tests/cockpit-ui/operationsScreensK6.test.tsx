import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { RedClientProvider } from "@/components/workspace/RedClientContext";
import { PerformanceReview } from "@/components/operations/PerformanceReview";
import { PerformanceReviewScreen } from "@/components/operations/PerformanceReviewScreen";
import { PortfolioOpportunities } from "@/components/operations/PortfolioOpportunities";
import { PortfolioOpportunitiesScreen } from "@/components/operations/PortfolioOpportunitiesScreen";
import { AuthoritySettings } from "@/components/operations/AuthoritySettings";
import { AuthoritySettingsScreen } from "@/components/operations/AuthoritySettingsScreen";
import { buildPrimaryNav } from "@/components/shell/navConfig";
import type {
  ClientWorkspace,
  EngagementProductionView,
  MeasurementRecord,
  PortfolioOpportunity,
  StageProductionView,
} from "@/lib/redOperationsApi";

// K6 (SPEC.md section 14 conditions 2 and 3): the ported performance review,
// portfolio opportunities and authority settings render as native cockpit
// components, read the shared workspace context (no per-screen free-text
// tenant/engagement inputs) and surface real error and empty states. The RED
// Operations nav group points at the native /operations routes. These tests
// render the additive cockpit components; they approve nothing, spend nothing
// and deploy nothing.

function stage(overrides: Partial<StageProductionView> = {}): StageProductionView {
  return {
    stage_number: 10,
    name: "Launch",
    checkpoint: "Performance Baseline Established",
    status: "in_review",
    required_asset_kinds: ["baseline"],
    approved_assets: [{ asset_id: "baseline", version: 1 }],
    missing_asset_kinds: [],
    accountable_role: "insight",
    approver_role: "client-authority",
    dependencies: [9],
    blocking_dependencies: [],
    assigned_owner: "insight",
    recorded_approver: null,
    due_on: "2026-10-20",
    next_action: "Record the first qualified traffic",
    blockers: [],
    entered_at: "2026-10-10",
    is_approved: false,
    ...overrides,
  };
}

function productionView(): EngagementProductionView {
  return {
    engagement: "ws-3f",
    tenant_id: "3fmindset",
    template_version: "1.0",
    current_stage_number: 10,
    next_approval_stage_number: 10,
    blocked_stage_numbers: [],
    progress: {
      approved_gates: 10,
      total_gates: 11,
      verified_post_launch_milestones: 0,
      activity_entries: 3,
      verified_progress: 10,
      gates_remaining: 1,
    },
    stages: [stage()],
  };
}

function measurement(overrides: Partial<MeasurementRecord> = {}): MeasurementRecord {
  return {
    record_id: "rec-1",
    tenant_id: "3fmindset",
    metric: {
      metric_id: "metric-1",
      tenant_id: "3fmindset",
      name: "Qualified traffic",
      funnel_step: "audience",
      unit: "visits",
      direction: "up",
      version: 1,
    },
    value: 120,
    window_start: "2026-10-01",
    window_end: "2026-10-07",
    basis: "observed",
    source: "analytics",
    sample_size: 120,
    recorded_on: "2026-10-08",
    is_observed: true,
    ...overrides,
  };
}

function opportunity(
  overrides: Partial<PortfolioOpportunity> = {},
): PortfolioOpportunity {
  return {
    tenant_id: "3fmindset",
    opportunity_id: "opp-1",
    title: "Mini offer",
    kind: "entry_point",
    source_asset_id: "offer-1",
    source_kind: "offer",
    source_version: 1,
    investment_case: "low cost entry",
    expected_outcome: "more leads",
    owner: "portfolio",
    next_action: "Review the case",
    captured_on: "2026-10-08",
    state: "proposed",
    ...overrides,
  };
}

function workspace(overrides: Partial<ClientWorkspace> = {}): ClientWorkspace {
  return {
    workspace_id: "ws-3f",
    tenant_id: "3fmindset",
    lifecycle: "intake",
    authorities: [{ actor: "client-authority", authority: "stage-approver" }],
    children: [],
    ...overrides,
  };
}

const fetchMock = vi.fn();

function listing() {
  return {
    tenant_id: "3fmindset",
    total: 1,
    limit: 50,
    offset: 0,
    workspaces: [workspace()],
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

describe("PerformanceReview", () => {
  it("renders the stage 10 baseline and marks observed and pending milestones", () => {
    render(
      <PerformanceReview
        view={productionView()}
        measurements={[measurement()]}
        tenantId="3fmindset"
      />,
    );
    expect(screen.getByTestId("performance-baseline-state").textContent).toContain(
      "Performance Baseline Established",
    );
    expect(screen.getByTestId("performance-baseline-assets").textContent).toContain(
      "baseline@v1",
    );
    expect(
      screen.getByTestId("performance-milestone-first_qualified_traffic").textContent,
    ).toContain("observed");
    expect(
      screen.getByTestId("performance-milestone-sale").textContent,
    ).toContain("pending");
  });

  it("shows an empty state and an error state", () => {
    const { rerender } = render(
      <PerformanceReview view={null} measurements={[]} />,
    );
    expect(screen.getByText("No stage 10 baseline.")).toBeTruthy();
    expect(
      screen.getByTestId("performance-no-observations").textContent,
    ).toContain("No post-launch observations recorded.");
    rerender(<PerformanceReview view={null} measurements={[]} error="boom" />);
    expect(screen.getByRole("alert").textContent).toBe("boom");
  });
});

describe("PortfolioOpportunities", () => {
  it("groups proposals by Grow effect and pins the grounding version", () => {
    render(
      <PortfolioOpportunities
        opportunities={[
          opportunity(),
          opportunity({
            opportunity_id: "opp-2",
            title: "Ascension",
            kind: "lifetime_value",
          }),
        ]}
        tenantId="3fmindset"
      />,
    );
    expect(screen.getByTestId("portfolio-entry-points").textContent).toContain(
      "Mini offer",
    );
    expect(screen.getByTestId("portfolio-lifetime-value").textContent).toContain(
      "Ascension",
    );
    expect(
      screen.getByTestId("portfolio-opportunity-opp-1").textContent,
    ).toContain("offer-1@v1");
  });

  it("shows an empty state", () => {
    render(<PortfolioOpportunities opportunities={[]} />);
    expect(
      screen.getByTestId("portfolio-opportunities-empty").textContent,
    ).toContain("No portfolio opportunities recorded.");
  });
});

describe("AuthoritySettings", () => {
  it("renders designated authorities and the gate approval scopes", () => {
    render(
      <AuthoritySettings
        workspaces={[workspace()]}
        stages={[stage()]}
        tenantId="3fmindset"
      />,
    );
    expect(screen.getByTestId("authority-holder-client-authority").textContent).toContain(
      "stage-approver",
    );
    expect(screen.getByTestId("approval-scope-10").textContent).toContain(
      "Performance Baseline Established",
    );
  });

  it("shows an empty state", () => {
    render(<AuthoritySettings workspaces={[]} stages={[]} />);
    expect(
      screen.getByTestId("authority-settings-empty").textContent,
    ).toContain("No designated authorities recorded.");
  });
});

describe("ported cockpit screens read the shared workspace context", () => {
  it("performance review fetches the production view and measurements with no free-text tenant input", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) return jsonResponse(listing());
      if (url.includes("/production-view?")) return jsonResponse(productionView());
      if (url.startsWith("/red/measurements?")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 1,
          limit: 50,
          offset: 0,
          records: [measurement()],
        });
      }
      throw new Error(`unexpected fetch ${url}`);
    });

    render(
      <RedClientProvider>
        <PerformanceReviewScreen />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("performance-baseline-state")).toBeTruthy(),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).includes("/red/clients/3fmindset/engagements/ws-3f/production-view"),
      ),
    ).toBe(true);
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/measurements?tenant_id=3fmindset"),
      ),
    ).toBe(true);
    expect(screen.queryByLabelText("Tenant")).toBeNull();
    expect(screen.queryByLabelText("Engagement")).toBeNull();
  });

  it("portfolio opportunities fetches the tenant-scoped register", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) return jsonResponse(listing());
      if (url.startsWith("/red/opportunities?")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 1,
          limit: 50,
          offset: 0,
          opportunities: [opportunity()],
        });
      }
      throw new Error(`unexpected fetch ${url}`);
    });

    render(
      <RedClientProvider>
        <PortfolioOpportunitiesScreen />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("portfolio-entry-points").textContent).toContain(
        "Mini offer",
      ),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/opportunities?tenant_id=3fmindset"),
      ),
    ).toBe(true);
  });

  it("authority settings reads the context registry and the production view", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) return jsonResponse(listing());
      if (url.includes("/production-view?")) return jsonResponse(productionView());
      throw new Error(`unexpected fetch ${url}`);
    });

    render(
      <RedClientProvider>
        <AuthoritySettingsScreen />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(
        screen.getByTestId("authority-holder-client-authority"),
      ).toBeTruthy(),
    );
    await waitFor(() =>
      expect(screen.getByTestId("approval-scope-10")).toBeTruthy(),
    );
    expect(screen.queryByLabelText("Tenant")).toBeNull();
    expect(screen.queryByLabelText("Engagement")).toBeNull();
  });
});

describe("RED Operations navigation points at the native routes", () => {
  it("links one /operations route per section 8 screen and no /screens link", () => {
    const red = buildPrimaryNav().find((group) => group.key === "red");
    expect(red?.label).toBe("RED Operations");
    const hrefs = red?.items.map((item) => item.href) ?? [];
    expect(hrefs).toEqual([
      "/operations/command-center",
      "/operations/client-workspace",
      "/operations/source-explorer",
      "/operations/transformation-map",
      "/operations/offer-and-journey",
      "/operations/build-board",
      "/operations/approval-inbox",
      "/operations/workflow-run-detail",
      "/operations/launch-readiness",
      "/operations/performance-review",
      "/operations/portfolio-opportunities",
      "/operations/authority-settings",
    ]);
    expect(hrefs.some((href) => href.startsWith("/screens"))).toBe(false);
  });
});
