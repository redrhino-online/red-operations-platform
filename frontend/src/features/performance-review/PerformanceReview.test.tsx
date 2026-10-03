import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import type {
  EngagementProductionView,
  MeasurementRecord,
} from "@/shared/api/client";
import {
  PerformanceReview,
  baselinePins,
  baselineStage,
  milestoneStates,
} from "./PerformanceReview";
import { PerformanceReviewScreen } from "./PerformanceReviewScreen";

function measurement(overrides: Partial<MeasurementRecord> = {}): MeasurementRecord {
  return {
    record_id: "rec-1",
    tenant_id: "3fmindset",
    metric: {
      metric_id: "m-1",
      tenant_id: "3fmindset",
      name: "Leads",
      funnel_step: "lead",
      unit: "count",
      direction: "up",
      version: 1,
    },
    value: 12,
    window_start: "2026-10-01",
    window_end: "2026-10-03",
    basis: "observed",
    source: "crm://3f/leads",
    sample_size: 12,
    recorded_on: "2026-10-03",
    is_observed: true,
    ...overrides,
  };
}

function productionView(
  overrides: Partial<EngagementProductionView> = {},
): EngagementProductionView {
  return {
    engagement: "3fmindset",
    tenant_id: "3fmindset",
    template_version: "0.1",
    current_stage_number: 10,
    next_approval_stage_number: null,
    blocked_stage_numbers: [],
    progress: {
      approved_gates: 11,
      total_gates: 11,
      verified_post_launch_milestones: 1,
      activity_entries: 0,
      verified_progress: 12,
      gates_remaining: 0,
    },
    stages: [
      {
        stage_number: 10,
        name: "Launch",
        checkpoint: "Performance Baseline Established",
        status: "approved",
        required_asset_kinds: ["live-campaign"],
        approved_assets: [{ asset_id: "baseline-3f", version: 2 }],
        missing_asset_kinds: [],
        accountable_role: "insight",
        approver_role: "client-authority",
        dependencies: [9],
        blocking_dependencies: [],
        assigned_owner: "perf-owner",
        recorded_approver: "client-authority",
        due_on: "2026-10-10",
        next_action: "watch baseline",
        blockers: [],
        entered_at: "2026-10-02",
        is_approved: true,
      },
    ],
    metric_reporting: [],
    ...overrides,
  };
}

describe("baselineStage", () => {
  it("returns the stage 10 row and null without a view", () => {
    expect(baselineStage(productionView())?.stage_number).toBe(10);
    expect(baselineStage(null)).toBeNull();
  });
});

describe("baselinePins", () => {
  it("shows each approved baseline asset at its exact pinned version", () => {
    expect(baselinePins(baselineStage(productionView()))).toEqual([
      "baseline-3f@v2",
    ]);
    expect(baselinePins(null)).toEqual([]);
  });
});

describe("milestoneStates", () => {
  it("marks a milestone observed from an observed record and leaves others pending", () => {
    const states = milestoneStates([measurement()]);
    const byKind = Object.fromEntries(states.map((s) => [s.kind, s]));
    expect(byKind.lead.status).toBe("observed");
    expect(byKind.lead.record?.value).toBe(12);
    expect(byKind.first_qualified_traffic.status).toBe("pending");
    expect(byKind.appointment.status).toBe("pending");
    expect(byKind.sale.status).toBe("pending");
  });

  it("picks the newest observed record per milestone", () => {
    const older = measurement({
      record_id: "rec-old",
      value: 3,
      recorded_on: "2026-10-01",
    });
    const newer = measurement({
      record_id: "rec-new",
      value: 9,
      recorded_on: "2026-10-03",
    });
    const byKind = Object.fromEntries(
      milestoneStates([older, newer]).map((s) => [s.kind, s]),
    );
    expect(byKind.lead.record?.record_id).toBe("rec-new");
  });

  it("leaves a milestone pending when only a placeholder record exists", () => {
    const placeholder = measurement({ is_observed: false, basis: "placeholder" });
    const byKind = Object.fromEntries(
      milestoneStates([placeholder]).map((s) => [s.kind, s]),
    );
    expect(byKind.lead.status).toBe("pending");
    expect(byKind.lead.record).toBeNull();
  });

  it("reads the sale milestone from the customer funnel step", () => {
    const sale = measurement({
      record_id: "rec-sale",
      metric: { ...measurement().metric, funnel_step: "customer" },
    });
    const byKind = Object.fromEntries(
      milestoneStates([sale]).map((s) => [s.kind, s]),
    );
    expect(byKind.sale.status).toBe("observed");
  });
});

describe("PerformanceReview", () => {
  it("renders the baseline gate state, pinned assets and milestones", () => {
    render(
      <PerformanceReview
        view={productionView()}
        measurements={[measurement()]}
        tenantId="3fmindset"
      />,
    );

    expect(screen.getByTestId("performance-baseline-state")).toHaveTextContent(
      "Launch (Performance Baseline Established): approved",
    );
    expect(screen.getByTestId("performance-baseline-assets")).toHaveTextContent(
      "baseline-3f@v2",
    );
    expect(screen.getByTestId("performance-baseline-owner")).toHaveTextContent(
      "Owner: perf-owner",
    );
    expect(
      screen.getByTestId("performance-milestone-lead"),
    ).toHaveTextContent("lead: observed");
    expect(
      screen.getByTestId("performance-milestone-sale"),
    ).toHaveTextContent("sale: pending");
  });

  it("shows an empty baseline and no observations honestly", () => {
    render(<PerformanceReview view={null} measurements={[]} />);
    expect(screen.getByText("No stage 10 baseline.")).toBeInTheDocument();
    expect(screen.getByTestId("performance-no-observations")).toHaveTextContent(
      "No post-launch observations recorded.",
    );
  });

  it("surfaces a loading state and error", () => {
    render(
      <PerformanceReview view={null} measurements={[]} loading error="boom" />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading performance review",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
  });
});

describe("PerformanceReviewScreen", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the tenant-scoped baseline and measurements", async () => {
    const fetcher = vi.fn().mockImplementation((url: string) => {
      const path = String(url);
      if (path.includes("/production-view")) {
        expect(path).toContain(
          "/red/clients/3fmindset/engagements/3fmindset/production-view",
        );
        return Promise.resolve({
          ok: true,
          status: 200,
          text: async () => JSON.stringify(productionView()),
        });
      }
      expect(path).toContain("/red/measurements?tenant_id=3fmindset");
      return Promise.resolve({
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({
            tenant_id: "3fmindset",
            total: 1,
            limit: 50,
            offset: 0,
            records: [measurement()],
          }),
      });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<PerformanceReviewScreen />);

    await waitFor(() =>
      expect(
        screen.getByTestId("performance-baseline-assets"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("performance-milestone-lead")).toHaveTextContent(
      "lead: observed",
    );
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
});
