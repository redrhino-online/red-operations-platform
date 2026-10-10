import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { RedClientProvider } from "@/components/workspace/RedClientContext";
import { ClientWorkspaceScreen } from "@/components/operations/ClientWorkspaceScreen";
import type {
  ApprovalRecord,
  DecisionRecord,
  EngagementProductionView,
  StageProductionView,
} from "@/lib/redOperationsApi";

// U1 (asset review and approval spec sections 3.1, 5 and 7): every approved
// asset pin in the client workspace opens the asset detail panel with that
// asset's approval records, gate decisions and, where the kind maps to one, its
// stored content. The API is mocked; the panel approves nothing.

function approval(overrides: Partial<ApprovalRecord> = {}): ApprovalRecord {
  return {
    asset_id: "story",
    version: 1,
    scope: "stage-6",
    requested_by: "production",
    approver: "client-authority",
    outcome: "approved",
    expires_on: null,
    stage_number: 6,
    decided_on: "2026-10-05",
    ...overrides,
  };
}

function decision(overrides: Partial<DecisionRecord> = {}): DecisionRecord {
  return {
    stage_number: 6,
    checkpoint: "Campaign Message Approved",
    disposition: "approved",
    reviewer: "client-authority",
    scope: "stage-6",
    rationale: "The story pins the approved campaign message.",
    checkpoint_evidence: "gate-6 transcript",
    decided_on: "2026-10-05",
    required_assets: [{ asset_id: "story", version: 1 }],
    ...overrides,
  };
}

function productionView(): EngagementProductionView {
  return {
    engagement: "ws-3f",
    tenant_id: "3fmindset",
    template_version: "1.0",
    current_stage_number: 6,
    next_approval_stage_number: 6,
    blocked_stage_numbers: [],
    progress: {
      approved_gates: 6,
      total_gates: 11,
      verified_post_launch_milestones: 0,
      activity_entries: 3,
      verified_progress: 6,
      gates_remaining: 5,
    },
    stages: [
      {
        stage_number: 0,
        name: "Intake",
        checkpoint: "Production Ready",
        status: "approved",
        required_asset_kinds: ["access-checklist"],
        approved_assets: [{ asset_id: "access-checklist", version: 1 }],
        missing_asset_kinds: [],
        accountable_role: "discovery",
        approver_role: "client-authority",
        dependencies: [],
        blocking_dependencies: [],
        assigned_owner: "discovery",
        recorded_approver: "client-authority",
        due_on: null,
        next_action: "",
        blockers: [],
        entered_at: "2026-10-01",
        is_approved: true,
      },
      {
        stage_number: 6,
        name: "Message",
        checkpoint: "Campaign Message Approved",
        status: "in_review",
        required_asset_kinds: ["story"],
        approved_assets: [{ asset_id: "story", version: 1 }],
        missing_asset_kinds: [],
        accountable_role: "message-design",
        approver_role: "client-authority",
        dependencies: [5],
        blocking_dependencies: [],
        assigned_owner: "production",
        recorded_approver: null,
        due_on: "2026-10-10",
        next_action: "Approve the message",
        blockers: [],
        entered_at: "2026-10-04",
        is_approved: false,
      },
    ],
  };
}

const fetchMock = vi.fn();

function jsonResponse(body: unknown) {
  return { ok: true, status: 200, json: async () => body };
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
        authorities: [],
        children: [],
      },
    ],
  };
}

function approvalsList() {
  return {
    tenant_id: "3fmindset",
    total: 2,
    limit: 50,
    offset: 0,
    approvals: [
      approval(),
      approval({
        asset_id: "access-checklist",
        stage_number: 0,
        scope: "stage-0",
        decided_on: "2026-10-01",
      }),
    ],
  };
}

function decisionsList() {
  return {
    tenant_id: "3fmindset",
    total: 2,
    limit: 50,
    offset: 0,
    decisions: [
      decision(),
      decision({
        stage_number: 0,
        checkpoint: "Production Ready",
        rationale: "The intake checklist is complete.",
        checkpoint_evidence: "gate-0 transcript",
        required_assets: [{ asset_id: "access-checklist", version: 1 }],
      }),
    ],
  };
}

function messageList() {
  return {
    tenant_id: "3fmindset",
    total: 1,
    limit: 50,
    offset: 0,
    messages: [
      {
        message_id: "msg-3f-1",
        owner: "production",
        avatar: "owner-operator",
        currency: "time",
        problem: "no predictable pipeline",
        promise: "a predictable pipeline in 90 days",
        cta: "book the diagnostic",
        problem_hierarchy: ["surface problem", "core problem"],
        desired_outcome: "a predictable pipeline",
        proof_objections: ["no proof yet"],
        story: "The owner is stuck trading time for leads.",
        method_explanation: "diagnose, then productize",
        lead_magnet: "the pipeline audit",
        hook: "Stop buying leads.",
        angles: ["time", "money"],
        landing_message: "Book a diagnostic call.",
        authority_amplifier_outline: "a weekly authority video",
        product_offer_id: "offer-1",
        is_approved: true,
      },
    ],
  };
}

function stage(
  stageNumber: number,
  name: string,
  checkpoint: string,
  approvedAssets: { asset_id: string; version: number }[],
): StageProductionView {
  return {
    stage_number: stageNumber,
    name,
    checkpoint,
    status: "approved",
    required_asset_kinds: approvedAssets.map((asset) => asset.asset_id),
    approved_assets: approvedAssets,
    missing_asset_kinds: [],
    accountable_role: "production",
    approver_role: "client-authority",
    dependencies: [],
    blocking_dependencies: [],
    assigned_owner: "production",
    recorded_approver: "client-authority",
    due_on: null,
    next_action: "",
    blockers: [],
    entered_at: "2026-10-04",
    is_approved: true,
  };
}

// A production view whose stage 2-5 gates pinned one asset kind each, so the
// stored-content tests can open a pin of every newly mapped kind.
function stagedProductionView(): EngagementProductionView {
  const base = productionView();
  return {
    ...base,
    stages: [
      ...base.stages,
      stage(2, "Position", "Currency Locked", [
        { asset_id: "primary-currency", version: 1 },
        { asset_id: "million-dollar-message", version: 1 },
      ]),
      stage(3, "Model", "Diagnostic Model Approved", [
        { asset_id: "diagnostic-model-name", version: 1 },
      ]),
      stage(4, "Package IP", "IP Architecture Locked", [
        { asset_id: "transformation-map", version: 1 },
      ]),
      stage(5, "Productize", "Offer Locked", [
        { asset_id: "delivery-model", version: 1 },
      ]),
    ],
  };
}

// One method carrying the full stored stage 2, 3 and 4 sections (asset review
// and approval spec section 6a, M1), plus a bare method with none of them.
function methodList() {
  return {
    tenant_id: "3fmindset",
    total: 2,
    limit: 50,
    offset: 0,
    methods: [
      {
        method_id: "method-3f-1",
        tenant_id: "3fmindset",
        parent_method: "",
        semantic_version: "1.0.0",
        stages: ["position", "model", "package-ip"],
        currency: "predictable pipeline",
        claims: ["90-day pipeline"],
        is_approved: true,
        approved_by: "client-authority",
        intended_use: "campaign production",
        approved_on: "2026-10-05",
        primary_currency: "predictable pipeline",
        diagnostic_model_id: "model-3f-1",
        signature_solution_id: "solution-3f-1",
        signature_solution: {
          solution_id: "solution-3f-1",
          tenant_id: "3fmindset",
          transformation_map: "Stuck operator to productized program",
          process_inventory: ["diagnose", "productize", "deliver"],
          phases: [
            {
              phase_id: "phase-1",
              tenant_id: "3fmindset",
              name: "Diagnose",
              steps: [
                {
                  step_id: "step-1",
                  tenant_id: "3fmindset",
                  name: "Audit the funnel",
                  starting_state: "unmeasured",
                  final_state: "measured",
                  inputs: ["funnel access"],
                  actions: ["audit the funnel"],
                  outputs: ["audit report"],
                },
              ],
            },
          ],
          starting_state: "stuck operator",
          final_state: "productized program",
          narrative: "The owner stops trading time for leads.",
          visual: "three-phase map",
        },
        primary_currency_detail: {
          currency: "predictable pipeline",
          version: "1",
          audience: "owner-operators",
          current_measure: "leads bought per month",
          desired_measure: "booked calls per week",
          mechanism: "one diagnostic funnel",
        },
        diagnostic_model: {
          model_id: "model-3f-1",
          version: "1",
          name: "Operator pyramid",
          levels: [
            {
              level_id: "level-1",
              name: "Stuck",
              observable_measures: ["no pipeline"],
              symptoms: ["erratic leads"],
              behaviors: ["buys leads"],
              problems: ["no system"],
            },
            {
              level_id: "level-2",
              name: "Scaling",
              observable_measures: ["steady calls"],
              symptoms: ["full calendar"],
              behaviors: ["hires help"],
              problems: ["no offer"],
            },
          ],
          progression: "stuck to scaling in 90 days",
          qualification_logic: "a booked call qualifies",
          visual: "pyramid diagram",
          explanatory_copy: "Four levels of operator maturity.",
        },
      },
      {
        method_id: "method-3f-2",
        tenant_id: "3fmindset",
        parent_method: "",
        semantic_version: "1.1.0",
        stages: [],
        currency: "time",
        claims: [],
        is_approved: false,
        approved_by: null,
        intended_use: null,
        approved_on: null,
        primary_currency: null,
        diagnostic_model_id: null,
        signature_solution_id: null,
        signature_solution: null,
      },
    ],
  };
}

// One offer carrying the full stored stage 5 delivery specification (asset
// review and approval spec section 6a, M2).
function offerList() {
  return {
    tenant_id: "3fmindset",
    total: 1,
    limit: 50,
    offset: 0,
    offers: [
      {
        offer_id: "offer-3f-1",
        tenant_id: "3fmindset",
        audience: "owner-operators",
        promise: "a predictable pipeline in 90 days",
        eligibility: "owner-operator with a delivery team",
        price_hypothesis: "$12k program",
        owner: "production",
        state: "production_ready",
        is_production_ready: true,
        method_refs: [],
        review_reason: null,
        delivery: {
          delivery_id: "delivery-3f-1",
          delivery_model: "group coaching program",
          duration: "12 weeks",
          modules: ["pipeline audit", "offer build", "funnel launch"],
          responsibilities: ["client does the work", "coach reviews"],
          support_cadence: "weekly group call",
          step_deliveries: [
            {
              step_id: "step-1",
              action: "audit the funnel",
              actor: "delivery lead",
              deliverable: "audit report",
              timing: "week 1",
              measure: "audit complete",
            },
          ],
          outcome_measures: ["booked calls per week"],
          pricing_payments: "$12k over three payments",
          scope: "one funnel, one offer",
          guarantee_decision: "refund if no calls in 90 days",
          eligibility: "owner-operator with a delivery team",
          offer_stack: ["core program", "audit intensive"],
        },
      },
    ],
  };
}

function installApi(
  approvals: unknown = approvalsList(),
  options: {
    view?: EngagementProductionView;
    methods?: unknown;
    offers?: unknown;
  } = {},
) {
  const view = options.view ?? productionView();
  const methods =
    options.methods ??
    ({ tenant_id: "3fmindset", total: 0, limit: 50, offset: 0, methods: [] });
  const offers =
    options.offers ??
    ({ tenant_id: "3fmindset", total: 0, limit: 50, offset: 0, offers: [] });
  fetchMock.mockImplementation(async (url: string) => {
    if (url.startsWith("/red/clients?")) return jsonResponse(listing());
    if (url.includes("/production-view?")) return jsonResponse(view);
    if (url.startsWith("/red/approvals?")) return jsonResponse(approvals);
    if (url.startsWith("/red/decisions?")) return jsonResponse(decisionsList());
    if (url.startsWith("/red/messages?")) return jsonResponse(messageList());
    if (url.startsWith("/red/methods?")) return jsonResponse(methods);
    if (url.startsWith("/red/offers?")) return jsonResponse(offers);
    throw new Error(`unexpected fetch ${url}`);
  });
}

function renderScreen() {
  return render(
    <RedClientProvider>
      <ClientWorkspaceScreen />
    </RedClientProvider>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the client workspace asset detail panel (U1)", () => {
  it("opens the panel from a pin with that asset's approvals and gate decisions", async () => {
    installApi();
    renderScreen();

    await waitFor(() => expect(screen.getByText("Message")).toBeTruthy());

    // Lazy: nothing beyond the production view is fetched before a pin opens.
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/approvals?"),
      ),
    ).toBe(false);

    fireEvent.click(screen.getByTestId("asset-pin-story@v1"));

    await waitFor(() =>
      expect(screen.getByTestId("asset-detail-panel")).toBeTruthy(),
    );

    const approvals = screen.getByTestId("asset-detail-approvals");
    expect(approvals.textContent).toContain("Version 1");
    expect(approvals.textContent).toContain("client-authority");
    expect(approvals.textContent).toContain("stage-6");
    expect(approvals.textContent).not.toContain("stage-0");

    const decisions = screen.getByTestId("asset-detail-decisions");
    expect(decisions.textContent).toContain("Campaign Message Approved");
    expect(decisions.textContent).toContain(
      "The story pins the approved campaign message.",
    );
    expect(decisions.textContent).toContain("gate-6 transcript");
    expect(decisions.textContent).not.toContain(
      "The intake checklist is complete.",
    );

    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/approvals?tenant_id=3fmindset"),
      ),
    ).toBe(true);
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/decisions?tenant_id=3fmindset"),
      ),
    ).toBe(true);
  });

  it("renders the mapped message content for a stage-6 kind", async () => {
    installApi();
    renderScreen();

    await waitFor(() => expect(screen.getByText("Message")).toBeTruthy());
    fireEvent.click(screen.getByTestId("asset-pin-story@v1"));

    await waitFor(() =>
      expect(
        screen.getByTestId("asset-detail-content").textContent,
      ).toContain("msg-3f-1"),
    );

    const content = screen.getByTestId("asset-detail-content");
    expect(content.textContent).toContain(
      "The owner is stuck trading time for leads.",
    );
    expect(content.textContent).toContain("Stop buying leads.");
    expect(content.textContent).toContain("Angles: time, money");
    expect(content.textContent).toContain("Book a diagnostic call.");
    expect(content.textContent).toContain("(approved)");
  });

  it("renders the provenance-only note for a kind with no content source", async () => {
    installApi();
    renderScreen();

    await waitFor(() => expect(screen.getByText("Intake")).toBeTruthy());
    fireEvent.click(screen.getByTestId("asset-pin-access-checklist@v1"));

    await waitFor(() =>
      expect(screen.getByTestId("asset-detail-no-content")).toBeTruthy(),
    );
    expect(screen.getByTestId("asset-detail-no-content").textContent).toBe(
      "No stored content for this asset kind — the approval records above are the record of what was approved.",
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/messages?"),
      ),
    ).toBe(false);

    const approvals = screen.getByTestId("asset-detail-approvals");
    expect(approvals.textContent).toContain("stage-0");
    const decisions = screen.getByTestId("asset-detail-decisions");
    expect(decisions.textContent).toContain(
      "The intake checklist is complete.",
    );
  });

  it("renders the explicit empty state when the asset has no approval records", async () => {
    installApi({
      tenant_id: "3fmindset",
      total: 0,
      limit: 50,
      offset: 0,
      approvals: [],
    });
    renderScreen();

    await waitFor(() => expect(screen.getByText("Message")).toBeTruthy());
    fireEvent.click(screen.getByTestId("asset-pin-story@v1"));

    await waitFor(() =>
      expect(screen.getByTestId("asset-detail-approvals-empty")).toBeTruthy(),
    );
    expect(
      screen.getByTestId("asset-detail-approvals-empty").textContent,
    ).toContain("No approval records found");
  });
});

// The stored content sections of the addendum (asset review and approval spec
// section 6a, M1-M3): stage 4 kinds read the method's signature solution,
// stage 3 kinds its diagnostic model, stage 2 `primary-currency` its primary
// currency, and stage 5 kinds the offer's delivery specification.
describe("the client workspace asset detail panel stored sections (6a)", () => {
  it("renders the signature solution content for a stage-4 kind pin", async () => {
    installApi(approvalsList(), {
      view: stagedProductionView(),
      methods: methodList(),
    });
    renderScreen();

    await waitFor(() => expect(screen.getByText("Package IP")).toBeTruthy());
    fireEvent.click(screen.getByTestId("asset-pin-transformation-map@v1"));

    await waitFor(() =>
      expect(
        screen.getByTestId("asset-detail-content").textContent,
      ).toContain("method-3f-1"),
    );

    const content = screen.getByTestId("asset-detail-content");
    expect(content.textContent).toContain("Signature solution");
    expect(content.textContent).toContain(
      "Narrative: The owner stops trading time for leads.",
    );
    expect(content.textContent).toContain("Starting state: stuck operator");
    expect(content.textContent).toContain("Final state: productized program");
    expect(screen.getByTestId("method-no-content-sections").textContent).toBe(
      "No stored content sections for this method.",
    );
  });

  it("renders the diagnostic model with its levels for a stage-3 kind pin", async () => {
    installApi(approvalsList(), {
      view: stagedProductionView(),
      methods: methodList(),
    });
    renderScreen();

    await waitFor(() => expect(screen.getByText("Model")).toBeTruthy());
    fireEvent.click(screen.getByTestId("asset-pin-diagnostic-model-name@v1"));

    await waitFor(() =>
      expect(
        screen.getByTestId("asset-detail-content").textContent,
      ).toContain("Operator pyramid"),
    );

    const content = screen.getByTestId("asset-detail-content");
    expect(content.textContent).toContain("Diagnostic model");
    expect(content.textContent).toContain("Observable measures: no pipeline");
    expect(content.textContent).toContain("Symptoms: erratic leads");
    expect(content.textContent).toContain("Behaviors: buys leads");
    expect(content.textContent).toContain("Problems: no system");
    expect(content.textContent).toContain("Observable measures: steady calls");
    expect(content.textContent).toContain(
      "Progression: stuck to scaling in 90 days",
    );
    expect(content.textContent).toContain(
      "Qualification logic: a booked call qualifies",
    );
    expect(content.textContent).toContain("Visual: pyramid diagram");
    expect(content.textContent).toContain(
      "Explanatory copy: Four levels of operator maturity.",
    );
  });

  it("renders the primary currency detail for primary-currency and provenance only for its stage-2 sibling", async () => {
    installApi(approvalsList(), {
      view: stagedProductionView(),
      methods: methodList(),
    });
    renderScreen();

    await waitFor(() => expect(screen.getByText("Position")).toBeTruthy());
    fireEvent.click(screen.getByTestId("asset-pin-primary-currency@v1"));

    await waitFor(() =>
      expect(
        screen.getByTestId("asset-detail-content").textContent,
      ).toContain("Primary currency"),
    );

    const content = screen.getByTestId("asset-detail-content");
    expect(content.textContent).toContain("Currency: predictable pipeline");
    expect(content.textContent).toContain("Audience: owner-operators");
    expect(content.textContent).toContain(
      "Current measure: leads bought per month",
    );
    expect(content.textContent).toContain(
      "Desired measure: booked calls per week",
    );
    expect(content.textContent).toContain("Mechanism: one diagnostic funnel");

    fireEvent.click(screen.getByTestId("asset-pin-million-dollar-message@v1"));
    await waitFor(() =>
      expect(screen.getByTestId("asset-detail-no-content")).toBeTruthy(),
    );
    expect(screen.getByTestId("asset-detail-no-content").textContent).toBe(
      "No stored content for this asset kind — the approval records above are the record of what was approved.",
    );
  });

  it("renders the delivery specification fields for a stage-5 kind pin", async () => {
    installApi(approvalsList(), {
      view: stagedProductionView(),
      offers: offerList(),
    });
    renderScreen();

    await waitFor(() => expect(screen.getByText("Productize")).toBeTruthy());
    fireEvent.click(screen.getByTestId("asset-pin-delivery-model@v1"));

    await waitFor(() =>
      expect(
        screen.getByTestId("asset-detail-content").textContent,
      ).toContain("offer-3f-1"),
    );

    const content = screen.getByTestId("asset-detail-content");
    expect(content.textContent).toContain("Delivery specification");
    expect(content.textContent).toContain(
      "Delivery model: group coaching program",
    );
    expect(content.textContent).toContain("Duration: 12 weeks");
    expect(content.textContent).toContain(
      "Modules: pipeline audit, offer build, funnel launch",
    );
    expect(content.textContent).toContain(
      "Responsibilities: client does the work, coach reviews",
    );
    expect(content.textContent).toContain("Support cadence: weekly group call");
    expect(content.textContent).toContain("step-1");
    expect(content.textContent).toContain("Action: audit the funnel");
    expect(content.textContent).toContain("Actor: delivery lead");
    expect(content.textContent).toContain("Deliverable: audit report");
    expect(content.textContent).toContain("Timing: week 1");
    expect(content.textContent).toContain("Measure: audit complete");
    expect(content.textContent).toContain(
      "Outcome measures: booked calls per week",
    );
    expect(content.textContent).toContain(
      "Pricing and payments: $12k over three payments",
    );
    expect(content.textContent).toContain("Scope: one funnel, one offer");
    expect(content.textContent).toContain(
      "Guarantee decision: refund if no calls in 90 days",
    );
    expect(content.textContent).toContain(
      "Offer stack: core program, audit intensive",
    );
  });
});
