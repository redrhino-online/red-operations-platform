// Transformation map, native cockpit page (K5; SPEC.md section 14 conditions 2
// and 3, section 8). Additive file (ADR 0014). Pure presentational view over the
// tenant-scoped approved method versions the backend returns from
// `GET /red/methods`. It renders the stage 4 Signature Solution an approved
// method pins: the transformation map, the declared starting and final states,
// the narrative, and the three phases with their nine named steps, each step's
// start and end state and its inputs, actions and outputs (SPEC.md section 4,
// stage 4). It holds no RED business logic: the backend owns the canonical three
// phase, nine step shape, so the screen shows the exact approved structure and
// can approve nothing.

import type {
  MethodVersion,
  SignatureSolution,
  SignatureStep,
} from "@/lib/redOperationsApi";

export interface TransformationMapProps {
  methods: MethodVersion[];
  loading?: boolean;
  error?: string | null;
  tenantId?: string;
}

// The nine named stages in phase order, flattened for counting and table
// rendering. This is the exact order the approved method pins; the UI does not
// re-order or re-derive it.
export function transformationSteps(
  solution: SignatureSolution | null,
): SignatureStep[] {
  if (!solution) {
    return [];
  }
  return solution.phases.flatMap((phase) => phase.steps);
}

function listLabel(entries: string[]): string {
  return entries.join(", ") || "none";
}

export function TransformationMap({
  methods,
  loading = false,
  error = null,
  tenantId,
}: TransformationMapProps) {
  return (
    <section aria-labelledby="transformation-map-heading">
      <h1 id="transformation-map-heading" className="text-xl font-semibold text-fg">
        Transformation map
      </h1>
      <p className="mt-1 text-sm text-fg-muted">
        The stage 4 transformation each approved method pins for{" "}
        {tenantId ?? "the active client"}: three phases and nine named steps from
        a declared starting state to a declared final state.
      </p>

      {loading ? (
        <p role="status" className="mt-4 text-sm text-fg-muted">
          Loading methods…
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">
          {error}
        </p>
      ) : null}

      <p data-testid="method-count" className="mt-4 text-sm text-fg-muted">
        {methods.length} approved method{methods.length === 1 ? "" : "s"}
      </p>

      {!loading && methods.length === 0 ? (
        <p className="mt-2 text-sm text-fg-muted">No approved methods.</p>
      ) : null}

      <div className="mt-4 space-y-4">
        {methods.map((method) => {
          const solution = method.signature_solution;
          const steps = transformationSteps(solution);
          return (
            <article
              key={method.method_id}
              aria-label={`Method ${method.method_id}`}
              className="rounded-xl border border-line bg-surface-elevated p-4"
            >
              <h2 className="text-sm font-medium text-fg">
                {method.method_id}{" "}
                <code>{method.semantic_version}</code>
              </h2>
              <p className="mt-1 text-sm text-fg-muted">
                {method.is_approved
                  ? `approved by ${method.approved_by ?? "the designated authority"}`
                  : "not approved"}
                {method.intended_use ? ` for ${method.intended_use}` : ""}
              </p>

              {solution === null ? (
                <p className="mt-2 text-sm text-fg-muted">
                  No pinned transformation map.
                </p>
              ) : (
                <div className="mt-2">
                  <p
                    data-testid={`transformation-map-${method.method_id}`}
                    className="text-sm text-fg"
                  >
                    {solution.transformation_map}
                  </p>
                  <p
                    data-testid={`transformation-states-${method.method_id}`}
                    className="text-sm text-fg-muted"
                  >
                    {solution.starting_state} to {solution.final_state}
                  </p>
                  <p className="text-sm text-fg-muted">{solution.narrative}</p>
                  <p
                    data-testid={`phase-step-count-${method.method_id}`}
                    className="text-sm text-fg-muted"
                  >
                    {solution.phases.length} phases, {steps.length} steps
                  </p>

                  {solution.phases.map((phase) => (
                    <section key={phase.phase_id} className="mt-3">
                      <h3 className="text-sm font-medium text-fg">{phase.name}</h3>
                      <div className="mt-1 overflow-x-auto rounded-lg border border-line bg-surface">
                        <table className="w-full text-left text-sm">
                          <thead className="text-xs text-fg-muted">
                            <tr className="border-b border-line">
                              <th scope="col" className="px-3 py-2 font-medium">Step</th>
                              <th scope="col" className="px-3 py-2 font-medium">From</th>
                              <th scope="col" className="px-3 py-2 font-medium">To</th>
                              <th scope="col" className="px-3 py-2 font-medium">Inputs</th>
                              <th scope="col" className="px-3 py-2 font-medium">Actions</th>
                              <th scope="col" className="px-3 py-2 font-medium">Outputs</th>
                            </tr>
                          </thead>
                          <tbody>
                            {phase.steps.map((step) => (
                              <tr
                                key={step.step_id}
                                className="border-b border-line last:border-0"
                              >
                                <td className="px-3 py-2 text-fg">{step.name}</td>
                                <td className="px-3 py-2 text-fg">{step.starting_state}</td>
                                <td className="px-3 py-2 text-fg">{step.final_state}</td>
                                <td className="px-3 py-2 text-fg">{listLabel(step.inputs)}</td>
                                <td className="px-3 py-2 text-fg">{listLabel(step.actions)}</td>
                                <td className="px-3 py-2 text-fg">{listLabel(step.outputs)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </section>
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
