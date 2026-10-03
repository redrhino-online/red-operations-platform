// Transformation map (SPEC.md section 8; DoD condition 6, Q36).
//
// Pure presentational view over the tenant-scoped approved method versions the
// backend returns from `GET /red/methods`. It renders the stage 4 Signature
// Solution an approved method pins: the transformation map, the declared
// starting and final states, the narrative, and the three phases with their
// nine named steps, each step's start and end state and its inputs, actions and
// outputs (SPEC.md section 4, stage 4). It holds no RED business logic: the
// backend owns the canonical three phase, nine step shape, so the screen shows
// the exact approved structure and can approve nothing.

import type {
  MethodVersion,
  SignatureSolution,
  SignatureStep,
} from "@/shared/api/client";

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
      <h1 id="transformation-map-heading">Transformation map</h1>
      <p style={{ color: "var(--red-muted)" }}>
        The stage 4 transformation each approved method pins for{" "}
        {tenantId ?? "the active client"}: three phases and nine named steps from
        a declared starting state to a declared final state.
      </p>

      {loading ? <p role="status">Loading methods...</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <p data-testid="method-count">
        {methods.length} approved method{methods.length === 1 ? "" : "s"}
      </p>

      {!loading && methods.length === 0 ? <p>No approved methods.</p> : null}

      {methods.map((method) => {
        const solution = method.signature_solution;
        const steps = transformationSteps(solution);
        return (
          <article
            key={method.method_id}
            aria-label={`Method ${method.method_id}`}
          >
            <h2>
              {method.method_id}{" "}
              <code>{method.semantic_version}</code>
            </h2>
            <p>
              {method.is_approved
                ? `approved by ${method.approved_by ?? "the designated authority"}`
                : "not approved"}
              {method.intended_use ? ` for ${method.intended_use}` : ""}
            </p>

            {solution === null ? (
              <p>No pinned transformation map.</p>
            ) : (
              <>
                <p data-testid={`transformation-map-${method.method_id}`}>
                  {solution.transformation_map}
                </p>
                <p data-testid={`transformation-states-${method.method_id}`}>
                  {solution.starting_state} to {solution.final_state}
                </p>
                <p>{solution.narrative}</p>
                <p data-testid={`phase-step-count-${method.method_id}`}>
                  {solution.phases.length} phases, {steps.length} steps
                </p>

                {solution.phases.map((phase) => (
                  <section key={phase.phase_id}>
                    <h3>{phase.name}</h3>
                    <table>
                      <thead>
                        <tr>
                          <th scope="col">Step</th>
                          <th scope="col">From</th>
                          <th scope="col">To</th>
                          <th scope="col">Inputs</th>
                          <th scope="col">Actions</th>
                          <th scope="col">Outputs</th>
                        </tr>
                      </thead>
                      <tbody>
                        {phase.steps.map((step) => (
                          <tr key={step.step_id}>
                            <td>{step.name}</td>
                            <td>{step.starting_state}</td>
                            <td>{step.final_state}</td>
                            <td>{listLabel(step.inputs)}</td>
                            <td>{listLabel(step.actions)}</td>
                            <td>{listLabel(step.outputs)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </section>
                ))}
              </>
            )}
          </article>
        );
      })}
    </section>
  );
}
