import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import type { BuildObject } from "@/shared/api/client";
import {
  BuildBoard,
  blockedBuilds,
  boardStates,
  buildsInState,
  dependencyRefs,
} from "./BuildBoard";
import { BuildBoardScreen } from "./BuildBoardScreen";

function build(overrides: Partial<BuildObject> = {}): BuildObject {
  return {
    build_id: "build-landing",
    tenant_id: "3fmindset",
    build_type: "landing-page",
    purpose: "capture the qualified lead",
    audience: "founders stuck at six figures",
    owner: "red-owner-1",
    next_action: "draft the headline",
    state: "in_development",
    is_active: true,
    is_blocked: false,
    blockers: [],
    refs: ["asset-copy", "asset-brand"],
    ...overrides,
  };
}

describe("boardStates", () => {
  it("orders the present states by the section 4 lifecycle", () => {
    const builds = [
      build({ build_id: "b", state: "approved" }),
      build({ build_id: "a", state: "identified" }),
      build({ build_id: "c", state: "internal_review" }),
    ];
    expect(boardStates(builds)).toEqual([
      "identified",
      "internal_review",
      "approved",
    ]);
  });

  it("places an unknown state after the known ones rather than dropping it", () => {
    const builds = [build({ state: "mystery" }), build({ state: "ready" })];
    expect(boardStates(builds)).toEqual(["ready", "mystery"]);
  });
});

describe("buildsInState", () => {
  it("returns only that state's builds, ordered by id", () => {
    const builds = [
      build({ build_id: "z", state: "ready" }),
      build({ build_id: "a", state: "ready" }),
      build({ build_id: "m", state: "approved" }),
    ];
    expect(buildsInState(builds, "ready").map((b) => b.build_id)).toEqual([
      "a",
      "z",
    ]);
  });
});

describe("dependencyRefs", () => {
  it("returns the declared refs sorted for stable display", () => {
    expect(dependencyRefs(build())).toEqual(["asset-brand", "asset-copy"]);
  });

  it("returns nothing for a build that declares no ref", () => {
    expect(dependencyRefs(build({ refs: [] }))).toEqual([]);
  });
});

describe("blockedBuilds", () => {
  it("keeps only the blocked builds, ordered by id", () => {
    const builds = [
      build({ build_id: "z", is_blocked: true, blockers: ["no source"] }),
      build({ build_id: "a", is_blocked: true, blockers: ["no owner"] }),
      build({ build_id: "m", is_blocked: false }),
    ];
    expect(blockedBuilds(builds).map((b) => b.build_id)).toEqual(["a", "z"]);
  });
});

describe("BuildBoard", () => {
  it("renders each build's owner, next action, dependencies and blockers", () => {
    render(
      <BuildBoard
        builds={[build()]}
        tenantId="3fmindset"
      />,
    );

    expect(screen.getByTestId("build-owner-build-landing")).toHaveTextContent(
      "Owner: red-owner-1",
    );
    expect(screen.getByTestId("build-next-build-landing")).toHaveTextContent(
      "Next: draft the headline",
    );
    expect(screen.getByTestId("build-refs-build-landing")).toHaveTextContent(
      "Depends on: asset-brand, asset-copy",
    );
    expect(screen.getByTestId("build-blockers-build-landing")).toHaveTextContent(
      "Blocked by: none",
    );
  });

  it("surfaces blocked builds in the dependency view", () => {
    render(
      <BuildBoard
        builds={[build({ is_blocked: true, blockers: ["missing approved method"] })]}
      />,
    );
    expect(screen.getByTestId("blocked-count")).toHaveTextContent(
      "1 blocked build",
    );
    expect(screen.getByTestId("blocked-build-landing")).toHaveTextContent(
      "missing approved method",
    );
  });

  it("surfaces an error and a loading state honestly", () => {
    render(<BuildBoard builds={[]} error="boom" loading />);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    expect(screen.getByRole("status")).toHaveTextContent("Loading builds");
  });

  it("shows an empty state when there are no builds", () => {
    render(<BuildBoard builds={[]} />);
    expect(screen.getByText("No production builds.")).toBeInTheDocument();
    expect(screen.getByText("No blocked builds.")).toBeInTheDocument();
  });
});

describe("BuildBoardScreen", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the tenant-scoped builds", async () => {
    const fetcher = vi.fn().mockImplementation((url: string) => {
      expect(String(url)).toContain("/red/builds?tenant_id=3fmindset");
      return Promise.resolve({
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({
            tenant_id: "3fmindset",
            total: 1,
            limit: 50,
            offset: 0,
            builds: [build()],
          }),
      });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<BuildBoardScreen />);

    await waitFor(() =>
      expect(screen.getByText("capture the qualified lead")).toBeInTheDocument(),
    );
    expect(fetcher).toHaveBeenCalled();
  });
});
