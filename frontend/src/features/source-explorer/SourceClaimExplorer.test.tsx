import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import type { Claim, SourceRecord } from "@/shared/api/client";
import {
  claimsForSource,
  groundedClaims,
  SourceClaimExplorer,
} from "./SourceClaimExplorer";
import { SourceClaimExplorerScreen } from "./SourceClaimExplorerScreen";

function source(overrides: Partial<SourceRecord> = {}): SourceRecord {
  return {
    source_id: "src-1",
    tenant_id: "3fmindset",
    locator: "interviews/founder-call.txt",
    checksum: "abc123",
    captured_on: "2026-10-01",
    access_rule: "client-team",
    ...overrides,
  };
}

function claim(overrides: Partial<Claim> = {}): Claim {
  return {
    claim_id: "claim-1",
    tenant_id: "3fmindset",
    statement: "The founder sold a prior studio.",
    provenance: "known",
    confidence_note: "stated verbatim on the call",
    is_directly_sourced: true,
    citations: [{ source_id: "src-1", checksum: "abc123", location: "00:12:03" }],
    ...overrides,
  };
}

describe("claimsForSource", () => {
  it("returns only claims citing the given source", () => {
    const grounded = claim();
    const other = claim({
      claim_id: "claim-2",
      citations: [{ source_id: "src-2", checksum: "def456", location: "p.4" }],
    });
    expect(
      claimsForSource([grounded, other], "src-1").map((c) => c.claim_id),
    ).toEqual(["claim-1"]);
  });
});

describe("groundedClaims", () => {
  it("keeps only claims with a direct source", () => {
    const sourced = claim();
    const derived = claim({ claim_id: "claim-2", provenance: "derived", is_directly_sourced: false, citations: [] });
    expect(groundedClaims([sourced, derived]).map((c) => c.claim_id)).toEqual([
      "claim-1",
    ]);
  });
});

describe("SourceClaimExplorer", () => {
  it("shows source provenance and the claims it grounds", () => {
    render(
      <SourceClaimExplorer sources={[source()]} claims={[claim()]} tenantId="3fmindset" />,
    );

    expect(screen.getByText("interviews/founder-call.txt")).toBeInTheDocument();
    expect(screen.getByText("abc123")).toBeInTheDocument();
    expect(screen.getByText("client-team")).toBeInTheDocument();
    expect(
      screen.getByText("The founder sold a prior studio."),
    ).toBeInTheDocument();
    expect(screen.getByText("known")).toBeInTheDocument();
    expect(screen.getByText("claim-1")).toBeInTheDocument();
    expect(
      screen.getByText("src-1@abc123 (00:12:03)"),
    ).toBeInTheDocument();
  });

  it("separates directly sourced claims from unsourced ones", () => {
    render(
      <SourceClaimExplorer
        sources={[source()]}
        claims={[
          claim(),
          claim({ claim_id: "claim-2", provenance: "proposed", is_directly_sourced: false, citations: [] }),
        ]}
      />,
    );

    expect(screen.getByTestId("claim-count")).toHaveTextContent(
      "2 claims, 1 directly sourced",
    );
    expect(screen.getByText("no direct source")).toBeInTheDocument();
  });

  it("surfaces an error and a loading state honestly", () => {
    render(
      <SourceClaimExplorer sources={[]} claims={[]} error="boom" loading />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading sources and claims",
    );
  });
});

describe("SourceClaimExplorerScreen", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the tenant-scoped sources and claims and renders them", async () => {
    const fetcher = vi.fn().mockImplementation((url: string) => {
      const payload = url.includes("/sources")
        ? { tenant_id: "3fmindset", total: 1, limit: 50, offset: 0, sources: [source()] }
        : { tenant_id: "3fmindset", total: 1, limit: 50, offset: 0, claims: [claim()] };
      return Promise.resolve({
        ok: true,
        status: 200,
        text: async () => JSON.stringify(payload),
      });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<SourceClaimExplorerScreen />);

    await waitFor(() =>
      expect(
        screen.getByText("The founder sold a prior studio."),
      ).toBeInTheDocument(),
    );
    const urls = fetcher.mock.calls.map((call) => String(call[0]));
    expect(urls).toEqual(
      expect.arrayContaining([
        expect.stringContaining("/red/clients/3fmindset/sources"),
        expect.stringContaining("/red/claims?tenant_id=3fmindset"),
      ]),
    );
  });
});
