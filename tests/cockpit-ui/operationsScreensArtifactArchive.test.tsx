import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { RedClientProvider } from "@/components/workspace/RedClientContext";
import { AuthoritySettingsScreen } from "@/components/operations/AuthoritySettingsScreen";
import { ClientWorkspaceScreen } from "@/components/operations/ClientWorkspaceScreen";
import { CommandCenterScreen } from "@/components/operations/CommandCenterScreen";
import { PerformanceReviewScreen } from "@/components/operations/PerformanceReviewScreen";
import type {
  EngagementProductionView,
  InterventionCard,
} from "@/lib/redOperationsApi";

// U1 and U3 (stage artifact archive spec sections 2 and 3): every stage row in
// the client workspace gains an Add artifact action whose form posts the
// expected body to the archive, refreshes on success and renders a backend
// refusal verbatim while recording nothing; a custom kind entry collects kinds
// outside the stage template. The four review surfaces render no date picker
// and fetch their data with no `on` parameter.

const STAGE_KEYS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"];

const AUTHORITIES = ["demo-red-principal", "demo-client-approver"];

function intervention(): InterventionCard {
  return {
    client: "3fmindset",
    reason: "overdue approval",
    severity: "high",
    subject: "offer@v2",
    explanation: "Stage 5 offer approval is overdue",
    evidence: ["gate:5"],
    owner: "governance",
    next_action: "Approve the offer",
    due_on: "2026-10-01",
    state: "open",
    affected_builds: ["build-offer"],
    resolution_note: "",
  };
}

function stage(
  stageNumber: number,
  name: string,
  requiredKinds: string[],
): EngagementProductionView["stages"][number] {
  return {
    stage_number: stageNumber,
    name,
    checkpoint: `${name} checkpoint`,
    status: "pending",
    required_asset_kinds: requiredKinds,
    approved_assets: [],
    missing_asset_kinds: [],
    accountable_role: "role",
    approver_role: "client-authority",
    dependencies: [],
    blocking_dependencies: [],
    assigned_owner: null,
    recorded_approver: null,
    due_on: null,
    next_action: "",
    blockers: [],
    entered_at: null,
    is_approved: false,
  };
}

function productionView(): EngagementProductionView {
  const names = [
    "Intake",
    "Diagnose",
    "Position",
    "Model",
    "Productize Service",
    "Productize",
    "Message",
    "Produce",
    "Integrate",
    "Assure",
    "Launch",
  ];
  return {
    engagement: "ws-3f",
    tenant_id: "3fmindset",
    template_version: "1.0",
    current_stage_number: 6,
    next_approval_stage_number: 6,
    blocked_stage_numbers: [],
    progress: {
      approved_gates: 0,
      total_gates: 11,
      verified_post_launch_milestones: 0,
      activity_entries: 0,
      verified_progress: 0,
      gates_remaining: 11,
    },
    stages: names.map((name, stageNumber) =>
      stage(
        stageNumber,
        name,
        stageNumber === 6 ? ["story", "hook"] : [],
      ),
    ),
  };
}

const fetchMock = vi.fn();

function jsonResponse(body: unknown) {
  return { ok: true, status: 200, json: async () => body };
}

function refusal(detail: string) {
  return { ok: false, status: 422, json: async () => ({ detail }) };
}

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
        authorities: AUTHORITIES.map((actor) => ({
          actor,
          authority: "approver",
        })),
        children: [],
      },
    ],
  };
}

// The screen-level mock: the shared context listing, the production view and
// the archive POST.
function installScreenApi(options: { post?: () => unknown } = {}) {
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    if (init?.method === "POST") {
      return options.post ? options.post() : jsonResponse({});
    }
    const path = String(url);
    if (path.startsWith("/red/clients?")) return jsonResponse(listing());
    if (path.includes("/production-view?")) {
      return jsonResponse(productionView());
    }
    if (path.startsWith("/red/interventions?")) {
      return jsonResponse({
        tenant_id: "3fmindset",
        engagement: "ws-3f",
        on: new Date().toISOString().slice(0, 10),
        total: 1,
        interventions: [intervention()],
      });
    }
    if (path.startsWith("/red/measurements?")) {
      return jsonResponse({
        tenant_id: "3fmindset",
        total: 0,
        limit: 50,
        offset: 0,
        records: [],
      });
    }
    throw new Error(`unexpected fetch ${path}`);
  });
}

function renderScreen(screenComponent: React.ReactElement) {
  return render(
    <RedClientProvider>{screenComponent}</RedClientProvider>,
  );
}

function postCalls(): Array<[string, RequestInit]> {
  return fetchMock.mock.calls.filter(
    ([, init]) => (init as RequestInit | undefined)?.method === "POST",
  ) as Array<[string, RequestInit]>;
}

function productionViewCalls(): Array<[string, unknown]> {
  return fetchMock.mock.calls.filter(([url]) =>
    String(url).includes("/production-view"),
  ) as Array<[string, unknown]>;
}

beforeEach(() => {
  window.localStorage.clear();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the client workspace Add artifact action (U1)", () => {
  it("renders an Add artifact action for every stage and the form posts the expected body, then refreshes", async () => {
    installScreenApi();
    renderScreen(<ClientWorkspaceScreen />);

    await waitFor(() => expect(screen.getByText("Message")).toBeTruthy());
    for (const stageKey of STAGE_KEYS) {
      expect(screen.getByTestId(`add-artifact-${stageKey}`)).toBeTruthy();
    }

    fireEvent.click(screen.getByTestId("add-artifact-6"));

    await waitFor(() =>
      expect(screen.getByTestId("artifact-drop-form")).toBeTruthy(),
    );

    // The kind select offers the stage's required kinds plus the custom entry,
    // and the asset id follows the kind until it is edited by hand.
    const kindSelect = screen.getByLabelText("Kind") as HTMLSelectElement;
    expect([...kindSelect.options].map((option) => option.value)).toEqual([
      "story",
      "hook",
      "__custom__",
    ]);
    expect((screen.getByLabelText("Asset id") as HTMLInputElement).value).toBe(
      "story",
    );
    fireEvent.change(kindSelect, { target: { value: "hook" } });
    expect((screen.getByLabelText("Asset id") as HTMLInputElement).value).toBe(
      "hook",
    );
    fireEvent.change(screen.getByLabelText("Asset id"), {
      target: { value: "hook-v2-draft" },
    });

    // Version stays blank: the backend takes the next free version.
    expect((screen.getByLabelText("Version") as HTMLInputElement).value).toBe(
      "",
    );
    fireEvent.change(screen.getByLabelText("Markdown"), {
      target: { value: "# Hook\n\n- line one" },
    });
    fireEvent.change(screen.getByLabelText("Owner"), {
      target: { value: "demo-client-approver" },
    });
    fireEvent.change(screen.getByLabelText("Note"), {
      target: { value: "Demo: hook draft" },
    });

    fireEvent.click(screen.getByTestId("artifact-submit"));

    // Success closes the form and refreshes the workspace data.
    await waitFor(() =>
      expect(screen.queryByTestId("artifact-drop-form")).toBeNull(),
    );
    const [url, init] = postCalls()[0];
    expect(String(url)).toBe("/red/clients/3fmindset/artifacts");
    expect(JSON.parse(init.body as string)).toEqual({
      workspace_id: "ws-3f",
      stage_number: 6,
      kind: "hook",
      asset_id: "hook-v2-draft",
      markdown: "# Hook\n\n- line one",
      owner: "demo-client-approver",
      note: "Demo: hook draft",
    });
    expect(productionViewCalls().length).toBeGreaterThan(1);
  });

  it("renders a backend refusal verbatim inline and records nothing", async () => {
    installScreenApi({
      post: () =>
        refusal("version 2 of story already exists with different content"),
    });
    renderScreen(<ClientWorkspaceScreen />);

    await waitFor(() => expect(screen.getByText("Message")).toBeTruthy());
    fireEvent.click(screen.getByTestId("add-artifact-6"));

    await waitFor(() =>
      expect(screen.getByTestId("artifact-drop-form")).toBeTruthy(),
    );
    fireEvent.change(screen.getByLabelText("Markdown"), {
      target: { value: "# Story\n\n- revised" },
    });
    fireEvent.click(screen.getByTestId("artifact-submit"));

    await waitFor(() =>
      expect(screen.getByTestId("artifact-error").textContent).toBe(
        "version 2 of story already exists with different content",
      ),
    );
    // The form stays open for a corrected submission; nothing was recorded and
    // the workspace did not refresh.
    expect(screen.getByTestId("artifact-drop-form")).toBeTruthy();
    expect(postCalls()).toHaveLength(1);
    expect(productionViewCalls()).toHaveLength(1);
  });

  it("collects a custom kind through the free-text entry", async () => {
    installScreenApi();
    renderScreen(<ClientWorkspaceScreen />);

    await waitFor(() => expect(screen.getByText("Message")).toBeTruthy());
    fireEvent.click(screen.getByTestId("add-artifact-6"));

    await waitFor(() =>
      expect(screen.getByTestId("artifact-drop-form")).toBeTruthy(),
    );
    fireEvent.change(screen.getByLabelText("Kind"), {
      target: { value: "__custom__" },
    });
    expect(screen.getByLabelText("Custom kind")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Custom kind"), {
      target: { value: "launch-postmortem" },
    });
    // The asset id follows the typed custom kind.
    expect((screen.getByLabelText("Asset id") as HTMLInputElement).value).toBe(
      "launch-postmortem",
    );
    fireEvent.change(screen.getByLabelText("Markdown"), {
      target: { value: "# Postmortem\n\n- what happened" },
    });

    fireEvent.click(screen.getByTestId("artifact-submit"));

    await waitFor(() =>
      expect(screen.queryByTestId("artifact-drop-form")).toBeNull(),
    );
    expect(JSON.parse(postCalls()[0][1].body as string)).toEqual({
      workspace_id: "ws-3f",
      stage_number: 6,
      kind: "launch-postmortem",
      asset_id: "launch-postmortem",
      markdown: "# Postmortem\n\n- what happened",
      owner: "demo-red-principal",
    });
  });
});

describe("the four review surfaces have no date picker (U3)", () => {
  it("command center renders no date input and fetches interventions with no on param", async () => {
    installScreenApi();
    renderScreen(<CommandCenterScreen />);

    await waitFor(() =>
      expect(screen.getByTestId("active-count").textContent).toContain(
        "1 active intervention",
      ),
    );
    expect(document.querySelector('input[type="date"]')).toBeNull();
    const calls = fetchMock.mock.calls.filter(([url]) =>
      String(url).startsWith("/red/interventions"),
    );
    expect(calls.length).toBeGreaterThan(0);
    for (const [url] of calls) {
      expect(String(url)).toBe(
        "/red/interventions?tenant_id=3fmindset&engagement=ws-3f",
      );
    }
  });

  it("client workspace renders no date input and fetches the production view with no on param", async () => {
    installScreenApi();
    renderScreen(<ClientWorkspaceScreen />);

    await waitFor(() => expect(screen.getByText("Message")).toBeTruthy());
    expect(document.querySelector('input[type="date"]')).toBeNull();
    const calls = productionViewCalls();
    expect(calls.length).toBeGreaterThan(0);
    for (const [url] of calls) {
      expect(String(url)).toBe(
        "/red/clients/3fmindset/engagements/ws-3f/production-view?",
      );
    }
  });

  it("performance review renders no date input and fetches the production view with no on param", async () => {
    installScreenApi();
    renderScreen(<PerformanceReviewScreen />);

    await waitFor(() =>
      expect(screen.getByTestId("performance-baseline-state")).toBeTruthy(),
    );
    expect(document.querySelector('input[type="date"]')).toBeNull();
    const calls = productionViewCalls();
    expect(calls.length).toBeGreaterThan(0);
    for (const [url] of calls) {
      expect(String(url)).toBe(
        "/red/clients/3fmindset/engagements/ws-3f/production-view?",
      );
    }
  });

  it("authority settings renders no date input and fetches the production view with no on param", async () => {
    installScreenApi();
    renderScreen(<AuthoritySettingsScreen />);

    await waitFor(() =>
      expect(screen.getByTestId("authority-holders")).toBeTruthy(),
    );
    // The production view read lands: the stage 10 approval scope renders from
    // it, so the fetch has happened before the URL assertions run.
    await waitFor(() =>
      expect(screen.getByTestId("approval-scope-10")).toBeTruthy(),
    );
    expect(document.querySelector('input[type="date"]')).toBeNull();
    const calls = productionViewCalls();
    expect(calls.length).toBeGreaterThan(0);
    for (const [url] of calls) {
      expect(String(url)).toBe(
        "/red/clients/3fmindset/engagements/ws-3f/production-view?",
      );
    }
  });
});
