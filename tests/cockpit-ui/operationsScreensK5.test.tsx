import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { RedClientProvider } from "@/components/workspace/RedClientContext";
import { SourceClaimExplorer } from "@/components/operations/SourceClaimExplorer";
import { SourceClaimExplorerScreen } from "@/components/operations/SourceClaimExplorerScreen";
import { TransformationMap } from "@/components/operations/TransformationMap";
import { TransformationMapScreen } from "@/components/operations/TransformationMapScreen";
import { OfferJourneyEditor } from "@/components/operations/OfferJourneyEditor";
import { OfferJourneyEditorScreen } from "@/components/operations/OfferJourneyEditorScreen";
import type {
  Claim,
  JourneyRelease,
  MethodVersion,
  OfferVersion,
  SourceRecord,
} from "@/lib/redOperationsApi";

// K5 (SPEC.md section 14 conditions 2 and 3): the ported source and claim
// explorer, transformation map and offer and journey editor render as native
// cockpit components, read the shared workspace context (no per-screen free-text
// tenant inputs) and surface real error and empty states. These tests render the
// additive cockpit components; they approve nothing, spend nothing and deploy
// nothing.

function source(overrides: Partial<SourceRecord> = {}): SourceRecord {
  return {
    source_id: "src-1",
    tenant_id: "3fmindset",
    locator: "interview-2026-09-01",
    checksum: "abc123",
    captured_on: "2026-09-01",
    access_rule: "client-only",
    ...overrides,
  };
}

function claim(overrides: Partial<Claim> = {}): Claim {
  return {
    claim_id: "claim-1",
    tenant_id: "3fmindset",
    statement: "The avatar wants more qualified leads",
    provenance: "Known",
    confidence_note: "direct quote",
    is_directly_sourced: true,
    citations: [
      { source_id: "src-1", checksum: "abc123", location: "p.2" },
    ],
    ...overrides,
  };
}

function method(overrides: Partial<MethodVersion> = {}): MethodVersion {
  return {
    method_id: "method-1",
    tenant_id: "3fmindset",
    parent_method: "signature-solution",
    semantic_version: "1.0.0",
    stages: ["stage-4"],
    currency: "qualified leads",
    claims: ["claim-1"],
    is_approved: true,
    approved_by: "client-authority",
    intended_use: "stage-4",
    approved_on: "2026-10-01",
    primary_currency: "qualified leads",
    diagnostic_model_id: null,
    signature_solution_id: "sol-1",
    signature_solution: {
      solution_id: "sol-1",
      tenant_id: "3fmindset",
      transformation_map: "from stuck to booked",
      process_inventory: ["discover"],
      phases: [
        {
          phase_id: "phase-1",
          tenant_id: "3fmindset",
          name: "Refine",
          steps: [
            {
              step_id: "step-1",
              tenant_id: "3fmindset",
              name: "Diagnose",
              starting_state: "unclear",
              final_state: "clear",
              inputs: ["interview"],
              actions: ["analyze"],
              outputs: ["avatar"],
            },
          ],
        },
      ],
      starting_state: "stuck",
      final_state: "booked",
      narrative: "three phases",
      visual: "map.png",
    },
    ...overrides,
  };
}

function offer(overrides: Partial<OfferVersion> = {}): OfferVersion {
  return {
    offer_id: "offer-1",
    tenant_id: "3fmindset",
    audience: "3F pilot",
    promise: "booked calls",
    eligibility: "qualified",
    price_hypothesis: "5000",
    owner: "production",
    state: "approved",
    is_production_ready: true,
    method_refs: [
      { method_id: "method-1", version: "1.0.0", intended_use: "stage-4" },
    ],
    review_reason: null,
    ...overrides,
  };
}

function journey(overrides: Partial<JourneyRelease> = {}): JourneyRelease {
  return {
    release_id: "release-1",
    tenant_id: "3fmindset",
    qa_id: "qa-9",
    assets: [
      { asset_id: "offer-1", tenant_id: "3fmindset", kind: "offer", version: 1 },
    ],
    routing: "opt-in",
    configuration_digest: "digest-1",
    rollback_ref: "rollback-1",
    released_kinds: ["offer"],
    is_signed_ready: true,
    is_authorized: true,
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

describe("SourceClaimExplorer", () => {
  it("renders sources, grounded claims and the citation link", () => {
    render(
      <SourceClaimExplorer
        sources={[source()]}
        claims={[claim(), claim({ claim_id: "claim-2", provenance: "Proposed", is_directly_sourced: false, citations: [] })]}
        tenantId="3fmindset"
      />,
    );
    expect(screen.getByTestId("source-count").textContent).toContain("1 source");
    expect(screen.getByTestId("claim-count").textContent).toContain(
      "2 claims, 1 directly sourced",
    );
    expect(screen.getByText("interview-2026-09-01")).toBeTruthy();
    expect(screen.getByText("claim-1")).toBeTruthy();
  });

  it("shows an empty state and an error state", () => {
    const { rerender } = render(
      <SourceClaimExplorer sources={[]} claims={[]} />,
    );
    expect(screen.getByText("No sources.")).toBeTruthy();
    expect(screen.getByText("No claims.")).toBeTruthy();
    rerender(<SourceClaimExplorer sources={[]} claims={[]} error="boom" />);
    expect(screen.getByRole("alert").textContent).toBe("boom");
  });
});

describe("TransformationMap", () => {
  it("renders the pinned transformation and its phase/step count", () => {
    render(<TransformationMap methods={[method()]} tenantId="3fmindset" />);
    expect(screen.getByTestId("method-count").textContent).toContain(
      "1 approved method",
    );
    expect(
      screen.getByTestId("transformation-map-method-1").textContent,
    ).toContain("from stuck to booked");
    expect(
      screen.getByTestId("phase-step-count-method-1").textContent,
    ).toContain("1 phases, 1 steps");
    expect(screen.getByText("Diagnose")).toBeTruthy();
  });

  it("shows an empty state", () => {
    render(<TransformationMap methods={[]} />);
    expect(screen.getByText("No approved methods.")).toBeTruthy();
  });
});

describe("OfferJourneyEditor", () => {
  it("renders approved offers with pinned methods and journey routing", () => {
    render(
      <OfferJourneyEditor
        offers={[offer()]}
        journeys={[journey()]}
        tenantId="3fmindset"
      />,
    );
    expect(screen.getByTestId("offer-count").textContent).toContain(
      "1 approved offer",
    );
    expect(screen.getByTestId("offer-method-count-offer-1").textContent).toContain(
      "1 pinned method",
    );
    expect(screen.getByTestId("journey-count").textContent).toContain(
      "1 journey release",
    );
    expect(screen.getByTestId("journey-kinds-release-1").textContent).toContain(
      "offer",
    );
  });

  it("shows an empty state", () => {
    render(<OfferJourneyEditor offers={[]} journeys={[]} />);
    expect(screen.getByText("No approved offers.")).toBeTruthy();
    expect(screen.getByText("No authorized journey releases.")).toBeTruthy();
  });
});

describe("ported cockpit screens read the shared workspace context", () => {
  it("source explorer fetches tenant-scoped sources and claims with no free-text tenant input", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) return jsonResponse(listing());
      if (url.includes("/sources")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 1,
          limit: 50,
          offset: 0,
          sources: [source()],
        });
      }
      if (url.startsWith("/red/claims?")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 1,
          limit: 50,
          offset: 0,
          claims: [claim()],
        });
      }
      throw new Error(`unexpected fetch ${url}`);
    });

    render(
      <RedClientProvider>
        <SourceClaimExplorerScreen />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("source-count").textContent).toContain(
        "1 source",
      ),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).includes("/red/clients/3fmindset/sources"),
      ),
    ).toBe(true);
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/claims?tenant_id=3fmindset"),
      ),
    ).toBe(true);
    expect(screen.queryByLabelText("Tenant")).toBeNull();
  });

  it("transformation map fetches the tenant-scoped methods", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) return jsonResponse(listing());
      if (url.startsWith("/red/methods?")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 1,
          limit: 50,
          offset: 0,
          methods: [method()],
        });
      }
      throw new Error(`unexpected fetch ${url}`);
    });

    render(
      <RedClientProvider>
        <TransformationMapScreen />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("method-count").textContent).toContain(
        "1 approved method",
      ),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/methods?tenant_id=3fmindset"),
      ),
    ).toBe(true);
  });

  it("offer and journey editor fetches the tenant-scoped offers and journeys", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) return jsonResponse(listing());
      if (url.startsWith("/red/offers?")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 1,
          limit: 50,
          offset: 0,
          offers: [offer()],
        });
      }
      if (url.startsWith("/red/journeys?")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 1,
          limit: 50,
          offset: 0,
          releases: [journey()],
        });
      }
      throw new Error(`unexpected fetch ${url}`);
    });

    render(
      <RedClientProvider>
        <OfferJourneyEditorScreen />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("offer-count").textContent).toContain(
        "1 approved offer",
      ),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/offers?tenant_id=3fmindset"),
      ),
    ).toBe(true);
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/journeys?tenant_id=3fmindset"),
      ),
    ).toBe(true);
  });
});
