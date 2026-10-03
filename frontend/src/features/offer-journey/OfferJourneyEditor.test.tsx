import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import type {
  JourneyRelease,
  OfferVersion,
} from "@/shared/api/client";
import {
  OfferJourneyEditor,
  pinnedMethodRefs,
  releasedAssetKinds,
} from "./OfferJourneyEditor";
import { OfferJourneyEditorScreen } from "./OfferJourneyEditorScreen";

function offer(overrides: Partial<OfferVersion> = {}): OfferVersion {
  return {
    offer_id: "offer-3f",
    tenant_id: "3fmindset",
    audience: "founders stuck at six figures",
    promise: "a repeatable referral engine",
    eligibility: "has a proven offer and at least one case study",
    price_hypothesis: "12k over twelve weeks",
    owner: "red-owner-1",
    state: "Production Ready",
    is_production_ready: true,
    method_refs: [
      {
        method_id: "method-b",
        version: "2.0.0",
        intended_use: "position the offer",
      },
      {
        method_id: "method-a",
        version: "1.0.0",
        intended_use: "deliver the method",
      },
    ],
    review_reason: null,
    ...overrides,
  };
}

function journey(overrides: Partial<JourneyRelease> = {}): JourneyRelease {
  return {
    release_id: "release-3f",
    tenant_id: "3fmindset",
    qa_id: "qa-3f",
    assets: [
      {
        asset_id: "asset-landing",
        tenant_id: "3fmindset",
        kind: "landing-page",
        version: 3,
      },
      {
        asset_id: "asset-sequence",
        tenant_id: "3fmindset",
        kind: "email-sequence",
        version: 1,
      },
    ],
    routing: "optin-to-booking",
    configuration_digest: "sha256:abc",
    rollback_ref: "release-3f-prev",
    released_kinds: ["email-sequence", "landing-page"],
    is_signed_ready: true,
    is_authorized: true,
    ...overrides,
  };
}

describe("pinnedMethodRefs", () => {
  it("sorts the pinned method references by intended use then id", () => {
    const refs = pinnedMethodRefs(offer());
    expect(refs.map((ref) => ref.intended_use)).toEqual([
      "deliver the method",
      "position the offer",
    ]);
  });

  it("returns nothing for an offer that pins no method", () => {
    expect(pinnedMethodRefs(offer({ method_refs: [] }))).toEqual([]);
  });
});

describe("releasedAssetKinds", () => {
  it("returns the released kinds sorted for stable display", () => {
    const reversed = journey({ released_kinds: ["landing-page", "email-sequence"] });
    expect(releasedAssetKinds(reversed)).toEqual([
      "email-sequence",
      "landing-page",
    ]);
  });
});

describe("OfferJourneyEditor", () => {
  it("renders each approved offer's fields and pinned methods", () => {
    render(
      <OfferJourneyEditor
        offers={[offer()]}
        journeys={[]}
        tenantId="3fmindset"
      />,
    );

    expect(
      screen.getByText("founders stuck at six figures"),
    ).toBeInTheDocument();
    expect(screen.getByText("a repeatable referral engine")).toBeInTheDocument();
    expect(screen.getByText("12k over twelve weeks")).toBeInTheDocument();
    expect(screen.getByText("red-owner-1")).toBeInTheDocument();
    expect(
      screen.getByTestId("offer-method-count-offer-3f"),
    ).toHaveTextContent("2 pinned methods");
    expect(screen.getByTestId("offer-methods-offer-3f")).toHaveTextContent(
      "method-a 1.0.0 for deliver the method",
    );
  });

  it("warns when an offer pins no approved method dependency", () => {
    render(
      <OfferJourneyEditor
        offers={[offer({ method_refs: [], is_production_ready: false })]}
        journeys={[]}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "No approved method dependency is pinned",
    );
  });

  it("renders each journey release's routing and exact asset versions", () => {
    render(<OfferJourneyEditor offers={[]} journeys={[journey()]} />);

    expect(screen.getByText("optin-to-booking")).toBeInTheDocument();
    expect(screen.getByText("sha256:abc")).toBeInTheDocument();
    expect(screen.getByText("release-3f-prev")).toBeInTheDocument();
    expect(screen.getByTestId("journey-kinds-release-3f")).toHaveTextContent(
      "email-sequence, landing-page",
    );
    expect(screen.getByText("asset-landing")).toBeInTheDocument();
    expect(screen.getByText("landing-page")).toBeInTheDocument();
    expect(screen.getByText("asset-sequence")).toBeInTheDocument();
  });

  it("surfaces an error and a loading state honestly", () => {
    render(<OfferJourneyEditor offers={[]} journeys={[]} error="boom" loading />);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading offers and journeys",
    );
  });

  it("shows empty states for offers and journeys", () => {
    render(<OfferJourneyEditor offers={[]} journeys={[]} />);
    expect(screen.getByText("No approved offers.")).toBeInTheDocument();
    expect(
      screen.getByText("No authorized journey releases."),
    ).toBeInTheDocument();
  });
});

describe("OfferJourneyEditorScreen", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the tenant-scoped offers and journeys in parallel", async () => {
    const fetcher = vi.fn().mockImplementation((url: string) => {
      const body = String(url).includes("/red/offers")
        ? {
            tenant_id: "3fmindset",
            total: 1,
            limit: 50,
            offset: 0,
            offers: [offer()],
          }
        : {
            tenant_id: "3fmindset",
            total: 1,
            limit: 50,
            offset: 0,
            releases: [journey()],
          };
      return Promise.resolve({
        ok: true,
        status: 200,
        text: async () => JSON.stringify(body),
      });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<OfferJourneyEditorScreen />);

    await waitFor(() =>
      expect(
        screen.getByText("a repeatable referral engine"),
      ).toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(screen.getByText("optin-to-booking")).toBeInTheDocument(),
    );
    const urls = fetcher.mock.calls.map((call) => String(call[0]));
    expect(urls).toEqual(
      expect.arrayContaining([
        expect.stringContaining("/red/offers?tenant_id=3fmindset"),
        expect.stringContaining("/red/journeys?tenant_id=3fmindset"),
      ]),
    );
  });
});
