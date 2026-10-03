import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import type { LaunchQA, LaunchQACheck } from "@/shared/api/client";
import {
  LaunchReadiness,
  checksWithOutcome,
  criticalFailures,
  exceptions,
  isAuthorized,
} from "./LaunchReadiness";
import { LaunchReadinessScreen } from "./LaunchReadinessScreen";

function check(overrides: Partial<LaunchQACheck> = {}): LaunchQACheck {
  return {
    kind: "recorded_message",
    outcome: "passed",
    evidence: "evidence://qa/message",
    owner: "",
    detail: "",
    is_critical_path: true,
    ...overrides,
  };
}

const PASSED = check();
const FAILED = check({
  kind: "crm",
  outcome: "failed",
  evidence: "evidence://qa/crm",
});
const EXCEPTED = check({
  kind: "payment",
  outcome: "excepted",
  evidence: "evidence://qa/payment",
  owner: "risk-owner",
  is_critical_path: false,
});

function launchQa(overrides: Partial<LaunchQA> = {}): LaunchQA {
  return {
    qa_id: "qa-3f",
    tenant_id: "3fmindset",
    owner: "qa-owner",
    designated_authority: "client-authority",
    state: "ready_for_traffic",
    checks: [PASSED, FAILED, EXCEPTED],
    authorization: {
      authorized_by: "client-authority",
      intended_use: "stage 9 traffic",
      authorized_on: "2026-10-02",
    },
    review_reason: null,
    is_ready_for_traffic: true,
    ...overrides,
  };
}

describe("checksWithOutcome", () => {
  it("groups checks by their exact recorded outcome", () => {
    expect(checksWithOutcome(launchQa(), "passed")).toEqual([PASSED]);
    expect(checksWithOutcome(launchQa(), "excepted")).toEqual([EXCEPTED]);
  });
});

describe("criticalFailures", () => {
  it("returns only failed critical-path checks", () => {
    expect(criticalFailures(launchQa())).toEqual([FAILED]);
  });

  it("ignores an off-critical failure", () => {
    const qa = launchQa({
      checks: [check({ kind: "payment", outcome: "failed", is_critical_path: false })],
    });
    expect(criticalFailures(qa)).toEqual([]);
  });
});

describe("exceptions", () => {
  it("returns the explicitly excepted checks", () => {
    expect(exceptions(launchQa())).toEqual([EXCEPTED]);
  });
});

describe("isAuthorized", () => {
  it("requires both a ready state and a pinned authorization", () => {
    expect(isAuthorized(launchQa())).toBe(true);
    expect(
      isAuthorized(launchQa({ is_ready_for_traffic: false })),
    ).toBe(false);
    expect(isAuthorized(launchQa({ authorization: null }))).toBe(false);
  });
});

describe("LaunchReadiness", () => {
  it("renders state, failures, exceptions and the pinned authorization", () => {
    render(<LaunchReadiness launchQas={[launchQa()]} tenantId="3fmindset" />);

    expect(screen.getByTestId("launch-state-qa-3f")).toHaveTextContent(
      "State: ready_for_traffic | Ready for traffic",
    );
    expect(screen.getByTestId("launch-failures-qa-3f")).toHaveTextContent(
      "crm: evidence://qa/crm",
    );
    expect(screen.getByTestId("launch-exceptions-qa-3f")).toHaveTextContent(
      "payment: excepted | owner: risk-owner",
    );
    expect(screen.getByTestId("launch-authorization-qa-3f")).toHaveTextContent(
      "Authorized by: client-authority",
    );
    expect(screen.getByTestId("launch-check-qa-3f-payment")).toHaveTextContent(
      "payment: excepted",
    );
  });

  it("surfaces an error and a loading state honestly", () => {
    render(<LaunchReadiness launchQas={[]} error="boom" loading />);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading launch readiness",
    );
  });

  it("shows an empty state when there are no launch QAs", () => {
    render(<LaunchReadiness launchQas={[]} />);
    expect(screen.getByText("No launch QAs.")).toBeInTheDocument();
  });
});

describe("LaunchReadinessScreen", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the tenant-scoped launch QAs", async () => {
    const fetcher = vi.fn().mockImplementation((url: string) => {
      expect(String(url)).toContain("/red/launch-qas?tenant_id=3fmindset");
      return Promise.resolve({
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({
            tenant_id: "3fmindset",
            total: 1,
            limit: 50,
            offset: 0,
            launch_qas: [launchQa()],
          }),
      });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<LaunchReadinessScreen />);

    await waitFor(() =>
      expect(
        screen.getByTestId("launch-owner-qa-3f"),
      ).toBeInTheDocument(),
    );
    expect(fetcher).toHaveBeenCalled();
  });
});
