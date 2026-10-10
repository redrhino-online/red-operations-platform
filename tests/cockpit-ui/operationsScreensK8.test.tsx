import { describe, expect, it } from "vitest";

import { landingRedirect, RED_LANDING_PATH } from "@/lib/redLanding";
import { BRIEFING_DESCRIPTION, buildPrimaryNav } from "@/components/shell/navConfig";

// K8 (SPEC.md section 14 condition 5): the landing surface is the RED portfolio
// command center. The root `/` (with no query) redirects to the native command
// center page — a redirect, not a rewrite, so the browser lands on a route the
// AppShell wraps with navigation (a rewritten root stayed on exempt `/` and lost
// the nav) — the chat-home deep links pass through, and the RED Operations group
// leads the navigation. These tests exercise the pure landing decision and the
// nav order; they approve nothing, spend nothing and deploy nothing.

describe("landingRedirect", () => {
  it("redirects the bare root to the RED command center", () => {
    expect(landingRedirect("/", "")).toBe(RED_LANDING_PATH);
    expect(RED_LANDING_PATH).toBe("/operations/command-center");
  });

  it("passes the chat-home deep links through unchanged", () => {
    expect(landingRedirect("/", "?new=1")).toBeNull();
    expect(landingRedirect("/", "?session=abc")).toBeNull();
    expect(landingRedirect("/", "?new=1&draft=hi")).toBeNull();
  });

  it("leaves every other route alone", () => {
    expect(landingRedirect("/operations/command-center", "")).toBeNull();
    expect(landingRedirect("/jobs", "")).toBeNull();
    expect(landingRedirect("/operations/build-board", "")).toBeNull();
  });
});

describe("RED-first navigation", () => {
  it("leads with the RED Operations group", () => {
    const groups = buildPrimaryNav();
    expect(groups[0].key).toBe("red");
    expect(groups[0].label).toBe("RED Operations");
  });

  it("keeps the twelve native /operations routes in the RED group", () => {
    const red = buildPrimaryNav().find((group) => group.key === "red");
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
  });

  it("retargets the Briefing copy to RED's daily brief", () => {
    expect(BRIEFING_DESCRIPTION.toLowerCase()).toContain("red");
  });
});
