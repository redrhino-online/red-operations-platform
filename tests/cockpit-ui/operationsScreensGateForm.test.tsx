import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { RedClientProvider } from "@/components/workspace/RedClientContext";
import { ClientWorkspaceScreen } from "@/components/operations/ClientWorkspaceScreen";
import {
  assembleGateBody,
  StageGateForm,
  type GateFormValues,
} from "@/components/operations/StageGateForm";
import type {
  EngagementProductionView,
  GateSchema,
} from "@/lib/redOperationsApi";
import payloads from "./fixtures/stage-gate-payloads.json";
import schemas from "./fixtures/stage-gate-schemas.json";

// U3 and U4 (asset review and approval spec sections 3.3, 3.4 and 7): the
// client workspace renders a Record gate action per stage, the form fetches the
// stage's gate schema and renders labeled inputs from it, and assembling the
// form with the equivalent of each stage's seed.py payload produces a POST body
// equal to it. A domain refusal renders the backend error inline and records
// nothing.

const STAGE_KEYS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"];

const AUTHORITIES = ["demo-red-principal", "demo-client-approver"];

function schemaFor(stage: string): GateSchema {
  return (schemas as Record<string, GateSchema>)[stage];
}

// The fixture payload expressed as the form values the DOM inputs would hold:
// number inputs yield strings, checkboxes yield booleans, and nested objects
// and array rows keep the payload's shape. The fixture fields map 1:1 to the
// schema properties, so the walk follows the schema to find the integer leaves.
type SchemaNode = {
  $ref?: string;
  anyOf?: { type?: string }[];
  type?: string;
  properties?: Record<string, SchemaNode>;
  items?: SchemaNode;
};

function resolveNode(
  node: SchemaNode,
  defs: Record<string, SchemaNode>,
): SchemaNode {
  let current = node;
  if (typeof current.$ref === "string") {
    current = defs[current.$ref.split("/").pop() ?? ""] ?? {};
  }
  if (Array.isArray(current.anyOf)) {
    const branch = current.anyOf.find(
      (candidate) => candidate.type !== "null",
    );
    return branch ? resolveNode(branch, defs) : {};
  }
  return current;
}

function toFormValues(
  schema: GateSchema,
  payload: Record<string, unknown>,
): GateFormValues {
  const defs = ((schema as SchemaNode).$defs ?? {}) as Record<
    string,
    SchemaNode
  >;
  const walk = (node: SchemaNode, value: unknown): unknown => {
    const resolved = resolveNode(node, defs);
    if (resolved.type === "object") {
      const out: Record<string, unknown> = {};
      for (const [name, nested] of Object.entries(
        value as Record<string, unknown>,
      )) {
        const prop = resolved.properties?.[name];
        if (prop) out[name] = walk(prop, nested);
      }
      return out;
    }
    if (resolved.type === "array") {
      const items = resolved.items ? resolveNode(resolved.items, defs) : {};
      return (value as unknown[]).map((item) => walk(items, item));
    }
    if (resolved.type === "integer") return String(value);
    return value;
  };
  return walk(schema as SchemaNode, payload) as GateFormValues;
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
    current_stage_number: 0,
    next_approval_stage_number: 0,
    blocked_stage_numbers: [],
    progress: {
      approved_gates: 0,
      total_gates: 11,
      verified_post_launch_milestones: 0,
      activity_entries: 0,
      verified_progress: 0,
      gates_remaining: 11,
    },
    stages: names.map((name, stage_number) => ({
      stage_number,
      name,
      checkpoint: `${name} checkpoint`,
      status: "pending",
      required_asset_kinds: [],
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
    })),
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
// the gate schema of one stage.
function installScreenApi(stage: number) {
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    const path = String(url);
    if (init?.method === "POST") return jsonResponse({});
    if (path.startsWith("/red/clients?")) return jsonResponse(listing());
    if (path.includes("/production-view?")) {
      return jsonResponse(productionView());
    }
    if (path.startsWith(`/red/stages/${stage}/gate-schema`)) {
      return jsonResponse(schemaFor(String(stage)));
    }
    throw new Error(`unexpected fetch ${path}`);
  });
}

// The component-level mock: the gate schema of one stage and the gate POST.
function installSchemaApi(
  stage: number,
  options: { post?: () => unknown } = {},
) {
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    const path = String(url);
    if (init?.method === "POST") {
      return options.post ? options.post() : jsonResponse({});
    }
    if (path.startsWith(`/red/stages/${stage}/gate-schema`)) {
      return jsonResponse(schemaFor(String(stage)));
    }
    throw new Error(`unexpected fetch ${path}`);
  });
}

function renderForm(stageNumber: number, onRecorded = vi.fn()) {
  return render(
    <StageGateForm
      tenantId="3fmindset"
      stageNumber={stageNumber}
      workspaceId="ws-3f"
      authorities={AUTHORITIES}
      onRecorded={onRecorded}
      onClose={() => {}}
    />,
  );
}

function postCalls(): Array<[string, RequestInit]> {
  return fetchMock.mock.calls.filter(
    ([, init]) => (init as RequestInit | undefined)?.method === "POST",
  ) as Array<[string, RequestInit]>;
}

beforeEach(() => {
  window.localStorage.clear();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the client workspace record-gate action (U3)", () => {
  it("renders a Record gate action for every stage 0-10 and opens the schema-driven form", async () => {
    installScreenApi(0);
    render(
      <RedClientProvider>
        <ClientWorkspaceScreen />
      </RedClientProvider>,
    );

    await waitFor(() => expect(screen.getByText("Intake")).toBeTruthy());
    for (const stage of STAGE_KEYS) {
      expect(screen.getByTestId(`record-gate-${stage}`)).toBeTruthy();
    }

    fireEvent.click(screen.getByTestId("record-gate-0"));

    await waitFor(() =>
      expect(screen.getByTestId("stage-gate-form")).toBeTruthy(),
    );
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).startsWith("/red/stages/0/gate-schema"),
      ),
    ).toBe(true);
    // Labeled inputs rendered from the mocked schema, with the workspace's
    // registered authorities as the actor options.
    expect(screen.getByLabelText("Intake package id")).toBeTruthy();
    expect(screen.getByLabelText("Workspace id")).toBeTruthy();
    const stageOwner = screen.getByLabelText("Stage owner") as HTMLSelectElement;
    const options = [...stageOwner.options].map((option) => option.value);
    expect(options).toEqual(AUTHORITIES);
  });
});

describe("StageGateForm stage 0 (U3)", () => {
  it("renders the schema's labeled inputs with the derivable defaults and submits the assembled body", async () => {
    installSchemaApi(0);
    const onRecorded = vi.fn();
    renderForm(0, onRecorded);

    await waitFor(() =>
      expect(screen.getByLabelText("Intake package id")).toBeTruthy(),
    );

    // Defaults prefilled where derivable: the current workspace, today's date,
    // version 1 on asset rows, and the authorities for the actor fields with
    // proposed_by on a different authority than the default approver.
    expect((screen.getByLabelText("Workspace id") as HTMLInputElement).value).toBe(
      "ws-3f",
    );
    expect((screen.getByLabelText("On") as HTMLInputElement).value).toBe(
      new Date().toISOString().slice(0, 10),
    );
    expect((screen.getByLabelText("Stage owner") as HTMLSelectElement).value).toBe(
      "demo-red-principal",
    );
    expect((screen.getByLabelText("Approver") as HTMLSelectElement).value).toBe(
      "demo-red-principal",
    );
    expect((screen.getByLabelText("Proposed by") as HTMLSelectElement).value).toBe(
      "demo-client-approver",
    );

    fireEvent.change(screen.getByLabelText("Intake package id"), {
      target: { value: "demo-intake-3f" },
    });
    fireEvent.change(screen.getByLabelText("Scope"), {
      target: { value: "stage-1-diagnosis" },
    });
    fireEvent.change(screen.getByLabelText("Checkpoint evidence"), {
      target: { value: "Demo: all stage 0 assets reviewed" },
    });
    fireEvent.change(screen.getByLabelText("Rationale"), {
      target: { value: "Demo: intake complete and owned" },
    });
    fireEvent.change(screen.getByLabelText("Due on"), {
      target: { value: "2026-10-02" },
    });
    fireEvent.change(screen.getByLabelText("Correlation id"), {
      target: { value: "demo-corr-stage-0" },
    });
    fireEvent.change(screen.getByLabelText("Approver"), {
      target: { value: "demo-client-approver" },
    });
    fireEvent.change(screen.getByLabelText("Proposed by"), {
      target: { value: "demo-red-principal" },
    });

    // One intake asset row: the asset_id follows the row's kind until edited.
    fireEvent.click(screen.getByLabelText("Add Assets row"));
    fireEvent.change(screen.getByLabelText("Assets row 1 Kind"), {
      target: { value: "client-record" },
    });
    expect(
      (screen.getByLabelText("Assets row 1 Asset id") as HTMLInputElement).value,
    ).toBe("client-record");
    fireEvent.change(screen.getByLabelText("Assets row 1 Asset id"), {
      target: { value: "demo-client-record-3f@1" },
    });
    expect(
      (screen.getByLabelText("Assets row 1 Version") as HTMLInputElement).value,
    ).toBe("1");
    fireEvent.change(screen.getByLabelText("Assets row 1 Owner"), {
      target: { value: "demo-red-principal" },
    });
    fireEvent.change(screen.getByLabelText("Assets row 1 Summary"), {
      target: { value: "Demo: recorded client-record" },
    });
    fireEvent.click(
      screen.getByLabelText("Add Assets row 1 Evidence claim ids item"),
    );
    fireEvent.change(
      screen.getByLabelText("Assets row 1 Evidence claim ids item 1"),
      { target: { value: "demo-claim-intake-1" } },
    );

    // One claim row with one citation.
    fireEvent.click(screen.getByLabelText("Add Claims row"));
    fireEvent.change(screen.getByLabelText("Claims row 1 Claim id"), {
      target: { value: "demo-claim-intake-1" },
    });
    fireEvent.change(screen.getByLabelText("Claims row 1 Statement"), {
      target: { value: "Demo: intake fact recorded with the client" },
    });
    fireEvent.change(screen.getByLabelText("Claims row 1 Provenance"), {
      target: { value: "known" },
    });
    fireEvent.click(screen.getByLabelText("Add Claims row 1 Citations row"));
    fireEvent.change(
      screen.getByLabelText("Claims row 1 Citations row 1 Source id"),
      { target: { value: "demo-source-intake" } },
    );
    fireEvent.change(
      screen.getByLabelText("Claims row 1 Citations row 1 Checksum"),
      { target: { value: "sha256:demo-intake" } },
    );
    fireEvent.change(
      screen.getByLabelText("Claims row 1 Citations row 1 Location"),
      { target: { value: "p.1" } },
    );

    fireEvent.click(screen.getByTestId("gate-submit"));

    await waitFor(() => expect(onRecorded).toHaveBeenCalled());
    const [url, init] = postCalls()[0];
    expect(String(url)).toBe("/red/clients/3fmindset/stages/0/gate");
    expect(JSON.parse(init.body as string)).toEqual({
      workspace_id: "ws-3f",
      intake_package_id: "demo-intake-3f",
      assets: [
        {
          asset_id: "demo-client-record-3f@1",
          kind: "client-record",
          version: 1,
          owner: "demo-red-principal",
          summary: "Demo: recorded client-record",
          evidence_claim_ids: ["demo-claim-intake-1"],
        },
      ],
      claims: [
        {
          claim_id: "demo-claim-intake-1",
          statement: "Demo: intake fact recorded with the client",
          provenance: "known",
          citations: [
            {
              source_id: "demo-source-intake",
              checksum: "sha256:demo-intake",
              location: "p.1",
            },
          ],
        },
      ],
      stage_owner: "demo-red-principal",
      approver: "demo-client-approver",
      scope: "stage-1-diagnosis",
      checkpoint_evidence: "Demo: all stage 0 assets reviewed",
      rationale: "Demo: intake complete and owned",
      assigned_owner: "demo-red-principal",
      due_on: "2026-10-02",
      on: new Date().toISOString().slice(0, 10),
      correlation_id: "demo-corr-stage-0",
      proposed_by: "demo-red-principal",
    });
  });

  it("warns when proposed_by matches the approver and clears when they differ", async () => {
    installSchemaApi(0);
    renderForm(0);

    await waitFor(() =>
      expect(screen.getByLabelText("Approver")).toBeTruthy(),
    );
    // Defaults differ, so no warning.
    expect(screen.queryByTestId("gate-self-approval-warning")).toBeNull();

    fireEvent.change(screen.getByLabelText("Approver"), {
      target: { value: "demo-client-approver" },
    });
    expect(
      screen.getByTestId("gate-self-approval-warning").textContent,
    ).toBe("the domain refuses self-approval");

    fireEvent.change(screen.getByLabelText("Proposed by"), {
      target: { value: "demo-red-principal" },
    });
    expect(screen.queryByTestId("gate-self-approval-warning")).toBeNull();
  });
});

describe("the stage gate refusal path (U4)", () => {
  it("renders the backend error verbatim inline and records nothing", async () => {
    installSchemaApi(0, {
      post: () =>
        refusal("stage 5 has not been approved; the dependency is unmet"),
    });
    const onRecorded = vi.fn();
    renderForm(0, onRecorded);

    await waitFor(() =>
      expect(screen.getByLabelText("Intake package id")).toBeTruthy(),
    );
    fireEvent.click(screen.getByTestId("gate-submit"));

    await waitFor(() =>
      expect(screen.getByTestId("gate-error").textContent).toBe(
        "stage 5 has not been approved; the dependency is unmet",
      ),
    );
    expect(onRecorded).not.toHaveBeenCalled();
    // The form stays open for a corrected submission; nothing was recorded.
    expect(screen.getByTestId("stage-gate-form")).toBeTruthy();
    expect(postCalls()).toHaveLength(1);
  });
});

describe("assembleGateBody round-trips every stage's seed payload (U3)", () => {
  it.each(STAGE_KEYS)(
    "assembles the stage %s fixture payload from its equivalent form values",
    (stage) => {
      const schema = schemaFor(stage);
      const payload = payloads[stage as keyof typeof payloads] as Record<
        string,
        unknown
      >;
      expect(assembleGateBody(schema, toFormValues(schema, payload))).toEqual(
        payload,
      );
    },
  );
});
