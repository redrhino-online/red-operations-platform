import { describe, expect, it, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

import type { MethodVersion, SignatureSolution } from "@/shared/api/client";
import {
  transformationSteps,
  TransformationMap,
} from "./TransformationMap";
import { TransformationMapScreen } from "./TransformationMapScreen";

function solution(overrides: Partial<SignatureSolution> = {}): SignatureSolution {
  const names = [
    "Diagnose",
    "Position",
    "Model",
    "Package IP",
    "Productize",
    "Message",
    "Produce",
    "Integrate",
    "Launch",
  ];
  const steps = names.map((name, index) => ({
    step_id: `step-${index + 1}`,
    tenant_id: "3fmindset",
    name,
    starting_state: `state-${index}`,
    final_state: `state-${index + 1}`,
    inputs: [`${name} inputs`],
    actions: [`${name} actions`],
    outputs: [`${name} outputs`],
  }));
  return {
    solution_id: "solution-3f",
    tenant_id: "3fmindset",
    transformation_map: "from chaotic delivery to a launched campaign",
    process_inventory: ["diagnose", "position"],
    phases: [
      { phase_id: "phase-1", tenant_id: "3fmindset", name: "Diagnose and Position", steps: steps.slice(0, 3) },
      { phase_id: "phase-2", tenant_id: "3fmindset", name: "Package and Productize", steps: steps.slice(3, 6) },
      { phase_id: "phase-3", tenant_id: "3fmindset", name: "Produce and Launch", steps: steps.slice(6, 9) },
    ],
    starting_state: "state-0",
    final_state: "state-9",
    narrative: "the client moves to a repeatable growth system",
    visual: "asset://transformations/3f-map.png",
    ...overrides,
  };
}

function method(overrides: Partial<MethodVersion> = {}): MethodVersion {
  return {
    method_id: "method-3f",
    tenant_id: "3fmindset",
    parent_method: "signature-solution",
    semantic_version: "1.0.0",
    stages: ["diagnose", "position"],
    currency: "qualified-referrals",
    claims: ["claim-1"],
    is_approved: true,
    approved_by: "client-approver-1",
    intended_use: "3f pilot campaign",
    approved_on: "2026-10-02",
    primary_currency: "qualified referrals",
    diagnostic_model_id: "model-3f",
    signature_solution_id: "solution-3f",
    signature_solution: solution(),
    ...overrides,
  };
}

describe("transformationSteps", () => {
  it("flattens the phases into the nine named stages in order", () => {
    const steps = transformationSteps(solution());
    expect(steps).toHaveLength(9);
    expect(steps[0].name).toBe("Diagnose");
    expect(steps[8].name).toBe("Launch");
  });

  it("returns nothing for a method with no pinned solution", () => {
    expect(transformationSteps(null)).toEqual([]);
  });
});

describe("TransformationMap", () => {
  it("renders the pinned map, states and phase and step counts", () => {
    render(<TransformationMap methods={[method()]} tenantId="3fmindset" />);

    expect(
      screen.getByText("from chaotic delivery to a launched campaign"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("transformation-states-method-3f")).toHaveTextContent(
      "state-0 to state-9",
    );
    expect(screen.getByTestId("phase-step-count-method-3f")).toHaveTextContent(
      "3 phases, 9 steps",
    );
    expect(screen.getByText("Diagnose and Position")).toBeInTheDocument();
    expect(screen.getByText("Package and Productize")).toBeInTheDocument();
    expect(screen.getByText("Produce and Launch")).toBeInTheDocument();
  });

  it("renders each stage's start and end state and inputs, actions and outputs", () => {
    render(<TransformationMap methods={[method()]} />);

    expect(screen.getByText("state-0")).toBeInTheDocument();
    expect(screen.getAllByText("state-1").length).toBeGreaterThan(0);
    expect(screen.getByText("Diagnose inputs")).toBeInTheDocument();
    expect(screen.getByText("Diagnose actions")).toBeInTheDocument();
    expect(screen.getByText("Diagnose outputs")).toBeInTheDocument();
  });

  it("surfaces an error and a loading state honestly", () => {
    render(<TransformationMap methods={[]} error="boom" loading />);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
    expect(screen.getByRole("status")).toHaveTextContent("Loading methods");
  });

  it("shows no approved methods as an empty state", () => {
    render(<TransformationMap methods={[]} />);
    expect(screen.getByText("No approved methods.")).toBeInTheDocument();
  });
});

describe("TransformationMapScreen", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("reads the tenant-scoped methods and renders the transformation", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () =>
        JSON.stringify({
          tenant_id: "3fmindset",
          total: 1,
          limit: 50,
          offset: 0,
          methods: [method()],
        }),
    });
    vi.stubGlobal("fetch", fetcher);

    render(<TransformationMapScreen />);

    await waitFor(() =>
      expect(
        screen.getByText("from chaotic delivery to a launched campaign"),
      ).toBeInTheDocument(),
    );
    const urls = fetcher.mock.calls.map((call) => String(call[0]));
    expect(urls).toEqual(
      expect.arrayContaining([
        expect.stringContaining("/red/methods?tenant_id=3fmindset"),
      ]),
    );
  });
});
