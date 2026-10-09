import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { RedClientProvider } from "@/components/workspace/RedClientContext";
import { BuildBoard } from "@/components/operations/BuildBoard";
import { BuildBoardScreen } from "@/components/operations/BuildBoardScreen";
import { WorkflowRunDetail } from "@/components/operations/WorkflowRunDetail";
import { WorkflowRunDetailScreen } from "@/components/operations/WorkflowRunDetailScreen";
import { LaunchReadiness } from "@/components/operations/LaunchReadiness";
import { LaunchReadinessScreen } from "@/components/operations/LaunchReadinessScreen";
import type {
  BuildObject,
  LaunchQA,
  WorkflowRunView,
} from "@/lib/redOperationsApi";

// K4 (SPEC.md section 14 conditions 2 and 3): the ported build board, workflow
// run detail and launch readiness render as native cockpit components, read the
// shared workspace context (no per-screen free-text tenant/engagement inputs)
// and surface real error and empty states. These tests render the additive
// cockpit components; they approve nothing, spend nothing and deploy nothing.

function build(overrides: Partial<BuildObject> = {}): BuildObject {
  return {
    build_id: "build-offer",
    tenant_id: "3fmindset",
    build_type: "offer",
    purpose: "Package the stage 5 offer",
    audience: "3F pilot",
    owner: "production",
    next_action: "Approve the offer",
    state: "in_development",
    is_active: true,
    is_blocked: false,
    blockers: [],
    refs: ["method@v1"],
    ...overrides,
  };
}

function workflowRun(overrides: Partial<WorkflowRunView> = {}): WorkflowRunView {
  return {
    run_id: "run-1",
    tenant_id: "3fmindset",
    definition_id: "signature-solution",
    definition_version: "1.0",
    status: "waiting_for_human",
    completed_steps: ["gather-sources"],
    in_progress_step: null,
    pending_approval: "stage-4-method",
    failure_reason: null,
    next_step: "register-version",
    event_id: "run-1:2",
    transitions: [
      {
        event_id: "run-1:1",
        actor: "system",
        reason: "started",
        occurred_at: "2026-10-01T00:00:00Z",
        old_status: "pending",
        new_status: "running",
        correlation_id: "corr-1",
      },
      {
        event_id: "run-1:2",
        actor: "governance",
        reason: "awaiting approval",
        occurred_at: "2026-10-02T00:00:00Z",
        old_status: "running",
        new_status: "waiting_for_human",
        correlation_id: "corr-2",
      },
    ],
    ...overrides,
  };
}

function launchQa(overrides: Partial<LaunchQA> = {}): LaunchQA {
  return {
    qa_id: "qa-9",
    tenant_id: "3fmindset",
    owner: "execution",
    designated_authority: "client-authority",
    state: "in_review",
    checks: [
      {
        kind: "customer-path",
        outcome: "failed",
        evidence: "dry run failed",
        owner: "execution",
        detail: "",
        is_critical_path: true,
      },
      {
        kind: "tracking",
        outcome: "excepted",
        evidence: "pixel pending",
        owner: "execution",
        detail: "",
        is_critical_path: false,
      },
      {
        kind: "forms",
        outcome: "passed",
        evidence: "all forms submit",
        owner: "execution",
        detail: "",
        is_critical_path: true,
      },
    ],
    authorization: null,
    review_reason: "critical path failure",
    is_ready_for_traffic: false,
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

describe("BuildBoard", () => {
  it("groups builds by lifecycle state and surfaces the dependency view", () => {
    render(
      <BuildBoard
        builds={[
          build(),
          build({
            build_id: "build-video",
            state: "approved",
            is_blocked: true,
            blockers: ["missing script"],
          }),
        ]}
        tenantId="3fmindset"
      />,
    );
    expect(screen.getByTestId("build-count").textContent).toContain("2 builds");
    expect(screen.getByTestId("blocked-count").textContent).toContain(
      "1 blocked build",
    );
    expect(screen.getByTestId("blocked-build-video").textContent).toContain(
      "missing script",
    );
    expect(screen.getByTestId("build-owner-build-offer").textContent).toContain(
      "production",
    );
    expect(screen.getByTestId("build-refs-build-offer").textContent).toContain(
      "method@v1",
    );
  });

  it("shows an empty state and an error state", () => {
    const { rerender } = render(<BuildBoard builds={[]} />);
    expect(screen.getByText("No production builds.")).toBeTruthy();
    rerender(<BuildBoard builds={[]} error="boom" />);
    expect(screen.getByRole("alert").textContent).toBe("boom");
  });
});

describe("WorkflowRunDetail", () => {
  it("renders the run state and the event log in event order", () => {
    render(<WorkflowRunDetail run={workflowRun()} />);
    expect(screen.getByTestId("run-id").textContent).toBe("run-1");
    expect(screen.getByTestId("run-status").textContent).toContain(
      "waiting_for_human",
    );
    expect(screen.getByTestId("run-definition").textContent).toContain(
      "signature-solution@1.0",
    );
    const log = screen.getByTestId("transition-log");
    expect(log.textContent).toContain("run-1:1");
    expect(log.textContent).toContain("run-1:2");
  });

  it("shows an empty state and an error state", () => {
    const { rerender } = render(<WorkflowRunDetail run={null} />);
    expect(
      screen.getByText("Enter a run id to load a workflow run."),
    ).toBeTruthy();
    rerender(<WorkflowRunDetail run={null} error="nope" />);
    expect(screen.getByRole("alert").textContent).toBe("nope");
  });
});

describe("LaunchReadiness", () => {
  it("surfaces critical failures, exceptions and the pinned authorization", () => {
    render(<LaunchReadiness launchQas={[launchQa()]} tenantId="3fmindset" />);
    expect(screen.getByTestId("launch-qa-count").textContent).toContain(
      "1 launch QA",
    );
    expect(screen.getByTestId("launch-state-qa-9").textContent).toContain(
      "Not authorized",
    );
    expect(screen.getByTestId("launch-failures-qa-9").textContent).toContain(
      "customer-path",
    );
    expect(screen.getByTestId("launch-exceptions-qa-9").textContent).toContain(
      "tracking",
    );
    expect(
      screen.getByTestId("launch-authorization-qa-9").textContent,
    ).toContain("No traffic authorization pinned.");
  });

  it("shows an empty state", () => {
    render(<LaunchReadiness launchQas={[]} />);
    expect(screen.getByText("No launch QAs.")).toBeTruthy();
  });
});

describe("ported cockpit screens read the shared workspace context", () => {
  it("build board fetches tenant-scoped builds and has no free-text tenant input", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) return jsonResponse(listing());
      if (url.startsWith("/red/builds?")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 1,
          limit: 50,
          offset: 0,
          builds: [build()],
        });
      }
      throw new Error(`unexpected fetch ${url}`);
    });

    render(
      <RedClientProvider>
        <BuildBoardScreen />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("build-count").textContent).toContain("1 build"),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/builds?tenant_id=3fmindset"),
      ),
    ).toBe(true);
    expect(screen.queryByLabelText("Tenant")).toBeNull();
    expect(screen.queryByLabelText("Engagement")).toBeNull();
  });

  it("workflow run detail fetches the run for the context tenant and a run id", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) return jsonResponse(listing());
      if (url.includes("/workflows/run-1")) return jsonResponse(workflowRun());
      throw new Error(`unexpected fetch ${url}`);
    });

    render(
      <RedClientProvider>
        <WorkflowRunDetailScreen />
      </RedClientProvider>,
    );

    fireEvent.change(screen.getByLabelText("Run id"), {
      target: { value: "run-1" },
    });

    await waitFor(() =>
      expect(screen.getByTestId("run-id").textContent).toBe("run-1"),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).includes("/red/clients/3fmindset/workflows/run-1"),
      ),
    ).toBe(true);
    expect(screen.queryByLabelText("Tenant")).toBeNull();
  });

  it("launch readiness fetches the tenant-scoped launch QAs", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.startsWith("/red/clients?")) return jsonResponse(listing());
      if (url.startsWith("/red/launch-qas?")) {
        return jsonResponse({
          tenant_id: "3fmindset",
          total: 1,
          limit: 50,
          offset: 0,
          launch_qas: [launchQa()],
        });
      }
      throw new Error(`unexpected fetch ${url}`);
    });

    render(
      <RedClientProvider>
        <LaunchReadinessScreen />
      </RedClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("launch-qa-count").textContent).toContain(
        "1 launch QA",
      ),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/launch-qas?tenant_id=3fmindset"),
      ),
    ).toBe(true);
  });
});
