import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import type { InterventionCard } from "@/shared/api/client";
import { activeInterventions, CommandCenter } from "./CommandCenter";
import { CommandCenterScreen } from "./CommandCenterScreen";

function card(overrides: Partial<InterventionCard> = {}): InterventionCard {
  return {
    client: "3fmindset",
    reason: "blocked-critical-path",
    severity: "high",
    subject: "Authority Amplifier",
    explanation: "Message must be approved before production starts.",
    evidence: ["stage-7:scripts"],
    owner: "production-manager",
    next_action: "Approve the stage 6 message",
    due_on: "2026-10-10",
    state: "working",
    affected_builds: ["authority-amplifier"],
    resolution_note: "",
    ...overrides,
  };
}

describe("activeInterventions", () => {
  it("keeps cards that are not dismissed", () => {
    const kept = card({ subject: "kept" });
    const dropped = card({ subject: "dropped", state: "dismissed" });
    expect(activeInterventions([kept, dropped])).toEqual([kept]);
  });
});

describe("CommandCenter", () => {
  it("shows blockers and owners from the ranked cards", () => {
    render(
      <CommandCenter
        interventions={[
          card({ subject: "Authority Amplifier", owner: "production-manager" }),
          card({
            subject: "Overdue approval",
            reason: "overdue-approval",
            owner: "client-approver",
          }),
        ]}
      />,
    );

    expect(screen.getByTestId("active-count")).toHaveTextContent(
      "2 active interventions",
    );
    expect(screen.getByText("blocked-critical-path")).toBeInTheDocument();
    expect(screen.getByText("overdue-approval")).toBeInTheDocument();
    expect(screen.getByText("production-manager")).toBeInTheDocument();
    expect(screen.getByText("client-approver")).toBeInTheDocument();
    expect(
      screen.getAllByText("Approve the stage 6 message").length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText("authority-amplifier").length).toBeGreaterThan(
      0,
    );
  });

  it("hides dismissed cards and reports no active interventions", () => {
    render(
      <CommandCenter interventions={[card({ state: "dismissed" })]} />,
    );
    expect(screen.getByTestId("active-count")).toHaveTextContent(
      "0 active interventions",
    );
    expect(screen.getByText("No active interventions.")).toBeInTheDocument();
    expect(screen.queryByText("production-manager")).not.toBeInTheDocument();
  });

  it("surfaces an error and a loading state honestly", () => {
    render(
      <CommandCenter interventions={[]} error="boom" loading />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading interventions",
    );
  });
});

describe("CommandCenterScreen", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the tenant-scoped interventions and renders them", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () =>
        JSON.stringify({
          tenant_id: "3fmindset",
          engagement: "3fmindset",
          on: "2026-10-03",
          total: 1,
          interventions: [
            card({ subject: "Authority Amplifier", owner: "production-manager" }),
          ],
        }),
    });
    vi.stubGlobal("fetch", fetcher);

    render(<CommandCenterScreen />);

    await waitFor(() =>
      expect(screen.getByText("production-manager")).toBeInTheDocument(),
    );
    expect(fetcher).toHaveBeenCalledWith(
      expect.stringContaining("/red/interventions?tenant_id=3fmindset"),
      expect.objectContaining({ method: "GET" }),
    );
  });
});
