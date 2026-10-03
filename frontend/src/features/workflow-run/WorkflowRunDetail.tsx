// Workflow run detail (SPEC.md sections 4, 7 and 8; DoD condition 6, Q40).
//
// Pure presentational detail over one durable, tenant-scoped workflow run the
// backend returns from `GET /red/clients/{tenant_id}/workflows/{run_id}`. The
// run pins the exact definition version it started on (SPEC.md section 10) and
// exposes a stable `event_id` plus its append-only transition log (SPEC.md
// section 7), so this screen polls the run state and renders the event log in
// event order. It computes no transition rule, resumes nothing and advances no
// run; the backend owns the run state machine, so the detail can release
// nothing.

import type {
  WorkflowRunTransition,
  WorkflowRunView,
} from "@/shared/api/client";

export interface WorkflowRunDetailProps {
  run: WorkflowRunView | null;
  loading?: boolean;
  error?: string | null;
}

// The stable ordinal a transition event id carries. The backend builds each
// event id as `<run_id>:<n>`; parsing the trailing segment gives the append
// order the event log must preserve.
export function eventOrdinal(eventId: string): number {
  const segment = eventId.slice(eventId.lastIndexOf(":") + 1);
  return Number.parseInt(segment, 10);
}

// The run's transitions in ascending event order. The append-only log is the
// authority on order, so the screen never reorders by wall clock; an id with no
// numeric ordinal sorts last rather than being dropped.
export function orderedTransitions(
  run: WorkflowRunView,
): WorkflowRunTransition[] {
  return [...run.transitions].sort((a, b) => {
    const left = eventOrdinal(a.event_id);
    const right = eventOrdinal(b.event_id);
    if (Number.isNaN(left)) return 1;
    if (Number.isNaN(right)) return -1;
    return left - right;
  });
}

function display(value: string | null): string {
  return value === null || value === "" ? "none" : value;
}

export function WorkflowRunDetail({
  run,
  loading = false,
  error = null,
}: WorkflowRunDetailProps) {
  return (
    <section aria-labelledby="workflow-run-heading">
      <h1 id="workflow-run-heading">Workflow run detail</h1>
      <p style={{ color: "var(--red-muted)" }}>
        The durable run state and its stable append-only event log, polled by the
        run&apos;s event id.
      </p>

      {loading ? <p role="status">Loading workflow run...</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      {!loading && run === null && error === null ? (
        <p>Enter a run id to load a workflow run.</p>
      ) : null}

      {run !== null ? (
        <>
          <h2 data-testid="run-id">{run.run_id}</h2>
          <p data-testid="run-status">
            Status: {run.status} | Event: {run.event_id}
          </p>
          <p data-testid="run-definition">
            Definition: {run.definition_id}@{run.definition_version} | Tenant:{" "}
            {run.tenant_id}
          </p>
          <p data-testid="run-completed">
            Completed steps:{" "}
            {run.completed_steps.length === 0
              ? "none"
              : run.completed_steps.join(", ")}
          </p>
          <p data-testid="run-progress">
            In progress: {display(run.in_progress_step)} | Pending approval:{" "}
            {display(run.pending_approval)} | Next step: {display(run.next_step)}
          </p>
          {run.failure_reason !== null ? (
            <p data-testid="run-failure">Failure: {run.failure_reason}</p>
          ) : null}

          <h3>Event log</h3>
          <ol data-testid="transition-log">
            {orderedTransitions(run).length === 0 ? (
              <li>No transitions.</li>
            ) : (
              orderedTransitions(run).map((transition) => (
                <li
                  key={transition.event_id}
                  data-testid={`transition-${transition.event_id}`}
                >
                  <p>
                    <strong>{transition.event_id}</strong>:{" "}
                    {transition.old_status} &rarr; {transition.new_status}
                  </p>
                  <p>
                    Actor: {transition.actor} | Occurred:{" "}
                    {transition.occurred_at}
                  </p>
                  <p>Reason: {display(transition.reason)}</p>
                  <p>Correlation: {transition.correlation_id}</p>
                </li>
              ))
            )}
          </ol>
        </>
      ) : null}
    </section>
  );
}
