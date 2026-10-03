import { describe, expect, it, vi, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import type { WorkflowRunTransition, WorkflowRunView } from "@/shared/api/client";
import {
  WorkflowRunDetail,
  eventOrdinal,
  orderedTransitions,
} from "./WorkflowRunDetail";
import { WorkflowRunDetailScreen } from "./WorkflowRunDetailScreen";

function transition(
  overrides: Partial<WorkflowRunTransition> = {},
): WorkflowRunTransition {
  return {
    event_id: "run-1:1",
    actor: "worker",
    reason: "started",
    occurred_at: "2026-10-02T10:00:00+00:00",
    old_status: "PENDING",
    new_status: "RUNNING",
    correlation_id: "corr-1",
    ...overrides,
  };
}

function run(overrides: Partial<WorkflowRunView> = {}): WorkflowRunView {
  return {
    run_id: "run-1",
    tenant_id: "3fmindset",
    definition_id: "authority-amplifier",
    definition_version: "1.0.0",
    status: "AWAITING_APPROVAL",
    completed_steps: ["gather-sources", "extract-claims"],
    in_progress_step: null,
    pending_approval: "human-approve",
    failure_reason: null,
    next_step: "human-approve",
    event_id: "run-1:2",
    transitions: [
      transition(),
      transition({
        event_id: "run-1:2",
        actor: "worker",
        reason: "waiting for client approval",
        old_status: "RUNNING",
        new_status: "AWAITING_APPROVAL",
        correlation_id: "corr-2",
      }),
    ],
    ...overrides,
  };
}

describe("eventOrdinal", () => {
  it("parses the trailing event number", () => {
    expect(eventOrdinal("run-1:7")).toBe(7);
  });

  it("returns NaN when there is no ordinal segment", () => {
    expect(Number.isNaN(eventOrdinal("run-1"))).toBe(true);
  });
});

describe("orderedTransitions", () => {
  it("orders by event ordinal ascending", () => {
    const value = run({
      transitions: [
        transition({ event_id: "run-1:3", new_status: "COMPLETED" }),
        transition({ event_id: "run-1:1" }),
        transition({ event_id: "run-1:2" }),
      ],
    });
    expect(orderedTransitions(value).map((t) => t.event_id)).toEqual([
      "run-1:1",
      "run-1:2",
      "run-1:3",
    ]);
  });

  it("sorts an id with no ordinal last rather than dropping it", () => {
    const value = run({
      transitions: [
        transition({ event_id: "no-ordinal" }),
        transition({ event_id: "run-1:1" }),
      ],
    });
    expect(orderedTransitions(value).map((t) => t.event_id)).toEqual([
      "run-1:1",
      "no-ordinal",
    ]);
  });
});

describe("WorkflowRunDetail", () => {
  it("renders the run state, pinned definition and stable event id", () => {
    render(<WorkflowRunDetail run={run()} />);
    expect(screen.getByTestId("run-id")).toHaveTextContent("run-1");
    expect(screen.getByTestId("run-status")).toHaveTextContent(
      "Status: AWAITING_APPROVAL | Event: run-1:2",
    );
    expect(screen.getByTestId("run-definition")).toHaveTextContent(
      "Definition: authority-amplifier@1.0.0 | Tenant: 3fmindset",
    );
    expect(screen.getByTestId("run-completed")).toHaveTextContent(
      "Completed steps: gather-sources, extract-claims",
    );
    expect(screen.getByTestId("run-progress")).toHaveTextContent(
      "In progress: none | Pending approval: human-approve | Next step: human-approve",
    );
  });

  it("renders the append-only event log with each transition's exact fields", () => {
    render(<WorkflowRunDetail run={run()} />);
    const first = screen.getByTestId("transition-run-1:1");
    expect(first).toHaveTextContent("run-1:1");
    expect(first).toHaveTextContent("PENDING → RUNNING");
    expect(first).toHaveTextContent("Actor: worker | Occurred: 2026-10-02T10:00:00+00:00");
    expect(first).toHaveTextContent("Reason: started");
    expect(first).toHaveTextContent("Correlation: corr-1");
    const items = screen.getAllByTestId(/^transition-.*:/);
    expect(items.map((item) => item.getAttribute("data-testid"))).toEqual([
      "transition-run-1:1",
      "transition-run-1:2",
    ]);
  });

  it("surfaces a failure reason only when the run failed", () => {
    const { rerender } = render(<WorkflowRunDetail run={run()} />);
    expect(screen.queryByTestId("run-failure")).not.toBeInTheDocument();
    rerender(
      <WorkflowRunDetail run={run({ status: "FAILED", failure_reason: "boom" })} />,
    );
    expect(screen.getByTestId("run-failure")).toHaveTextContent("Failure: boom");
  });

  it("shows a prompt, a loading state and an error honestly", () => {
    const { rerender } = render(<WorkflowRunDetail run={null} />);
    expect(
      screen.getByText("Enter a run id to load a workflow run."),
    ).toBeInTheDocument();
    rerender(<WorkflowRunDetail run={null} error="boom" />);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    rerender(<WorkflowRunDetail run={null} loading />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading workflow run");
  });

  it("shows an empty event log when the run has no transitions", () => {
    render(<WorkflowRunDetail run={run({ transitions: [] })} />);
    expect(screen.getByTestId("transition-log")).toHaveTextContent(
      "No transitions.",
    );
  });
});

describe("WorkflowRunDetailScreen", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the tenant-scoped workflow run", async () => {
    const fetcher = vi.fn().mockImplementation((url: string) => {
      expect(String(url)).toContain(
        "/red/clients/3fmindset/workflows/run-1",
      );
      return Promise.resolve({
        ok: true,
        status: 200,
        text: async () => JSON.stringify(run()),
      });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<WorkflowRunDetailScreen />);

    fireEvent.change(screen.getByLabelText("Run id"), {
      target: { value: "run-1" },
    });

    await waitFor(() =>
      expect(screen.getByTestId("run-id")).toHaveTextContent("run-1"),
    );
    expect(fetcher).toHaveBeenCalled();
  });
});
