import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import type { PortfolioOpportunity } from "@/shared/api/client";
import {
  ENTRY_POINT,
  LIFETIME_VALUE,
  PortfolioOpportunities,
  byKind,
  groundingVersion,
  isProposal,
} from "./PortfolioOpportunities";
import { PortfolioOpportunitiesScreen } from "./PortfolioOpportunitiesScreen";

function opportunity(
  overrides: Partial<PortfolioOpportunity> = {},
): PortfolioOpportunity {
  return {
    tenant_id: "3fmindset",
    opportunity_id: "opp-entry",
    title: "Foundations offer",
    kind: ENTRY_POINT,
    source_asset_id: "offer-3f",
    source_kind: "offer",
    source_version: 3,
    investment_case: "low cost launch",
    expected_outcome: "new low-barrier entry point",
    owner: "portfolio-owner",
    next_action: "size the build",
    captured_on: "2026-10-03",
    state: "proposed",
    ...overrides,
  };
}

describe("groundingVersion", () => {
  it("shows the exact pinned source asset version", () => {
    expect(groundingVersion(opportunity())).toBe("offer-3f@v3");
  });
});

describe("byKind", () => {
  it("groups proposals by the canon Grow effect", () => {
    const ltv = opportunity({
      opportunity_id: "opp-ltv",
      kind: LIFETIME_VALUE,
    });
    expect(byKind([opportunity(), ltv], ENTRY_POINT)).toHaveLength(1);
    expect(byKind([opportunity(), ltv], LIFETIME_VALUE)).toHaveLength(1);
  });
});

describe("isProposal", () => {
  it("is true only for a proposed state", () => {
    expect(isProposal(opportunity())).toBe(true);
    expect(isProposal(opportunity({ state: "approved" }))).toBe(false);
  });
});

describe("PortfolioOpportunities", () => {
  it("renders each proposal with its pinned grounding and owner", () => {
    const ltv = opportunity({
      opportunity_id: "opp-ltv",
      title: "Retainer tier",
      kind: LIFETIME_VALUE,
      source_version: 1,
    });
    render(
      <PortfolioOpportunities
        opportunities={[opportunity(), ltv]}
        tenantId="3fmindset"
      />,
    );

    const row = screen.getByTestId("portfolio-opportunity-opp-entry");
    expect(row).toHaveTextContent("Foundations offer (proposed)");
    expect(row).toHaveTextContent("offer-3f@v3");
    expect(row).toHaveTextContent("Owner: portfolio-owner");
    expect(
      screen.getByTestId("portfolio-opportunity-opp-ltv"),
    ).toHaveTextContent("Retainer tier (proposed)");
  });

  it("shows an empty register honestly", () => {
    render(<PortfolioOpportunities opportunities={[]} />);
    expect(
      screen.getByTestId("portfolio-opportunities-empty"),
    ).toHaveTextContent("No portfolio opportunities recorded.");
  });

  it("surfaces a loading state and error", () => {
    render(
      <PortfolioOpportunities
        opportunities={[]}
        loading
        error="boom"
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading portfolio opportunities",
    );
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
  });
});

describe("PortfolioOpportunitiesScreen", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the tenant-scoped opportunity register", async () => {
    const fetcher = vi.fn().mockImplementation((url: string) => {
      const path = String(url);
      expect(path).toContain("/red/opportunities?tenant_id=3fmindset");
      return Promise.resolve({
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({
            tenant_id: "3fmindset",
            total: 1,
            limit: 50,
            offset: 0,
            opportunities: [opportunity()],
          }),
      });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<PortfolioOpportunitiesScreen />);

    await waitFor(() =>
      expect(
        screen.getByTestId("portfolio-opportunity-opp-entry"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByTestId("portfolio-opportunity-opp-entry")).toHaveTextContent(
      "offer-3f@v3",
    );
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
});
