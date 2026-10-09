// Workflow run detail, native cockpit page (K4; SPEC.md section 14 conditions 2
// and 3, section 8). Additive file (ADR 0014). Pure presentational detail over
// one durable, tenant-scoped workflow run the backend returns from
// `GET /red/clients/{tenant_id}/workflows/{run_id}`. The run pins the exact
// definition version it started on (SPEC.md section 10) and exposes a stable
// `event_id` plus its append-only transition log (SPEC.md section 7), so this
// screen renders the run state and the event log in event order. It computes no
// transition rule, resumes nothing and advances no run; the backend owns the run
// state machine, so the detail can release nothing.

import type {
  WorkflowRunTransition,
  WorkflowRunView,
} from "@/lib/redOperationsApi";

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
      <h1 id="workflow-run-heading" className="text-xl font-semibold text-fg">
        Workflow run detail
      </h1>
      <p className="mt-1 text-sm text-fg-muted">
        The durable run state and its stable append-only event log, polled by the
        run&apos;s event id.
      </p>

      {loading ? (
        <p role="status" className="mt-4 text-sm text-fg-muted">
          Loading workflow run…
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">
          {error}
        </p>
      ) : null}

      {!loading && run === null && error === null ? (
        <p className="mt-4 text-sm text-fg-muted">
          Enter a run id to load a workflow run.
        </p>
      ) : null}

      {run !== null ? (
        <div className="mt-4">
          <h2 data-testid="run-id" className="text-sm font-medium text-fg">
            {run.run_id}
          </h2>
          <p data-testid="run-status" className="mt-1 text-sm text-fg-muted">
            Status: {run.status} | Event: {run.event_id}
          </p>
          <p data-testid="run-definition" className="text-sm text-fg-muted">
            Definition: {run.definition_id}@{run.definition_version} | Tenant:{" "}
            {run.tenant_id}
          </p>
          <p data-testid="run-completed" className="text-sm text-fg-muted">
            Completed steps:{" "}
            {run.completed_steps.length === 0
              ? "none"
              : run.completed_steps.join(", ")}
          </p>
          <p data-testid="run-progress" className="text-sm text-fg-muted">
            In progress: {display(run.in_progress_step)} | Pending approval:{" "}
            {display(run.pending_approval)} | Next step: {display(run.next_step)}
          </p>
          {run.failure_reason !== null ? (
            <p data-testid="run-failure" className="text-sm text-red-400">
              Failure: {run.failure_reason}
            </p>
          ) : null}

          <h3 className="mt-4 text-sm font-medium text-fg">Event log</h3>
          <ol
            data-testid="transition-log"
            className="mt-2 space-y-3 text-sm text-fg"
          >
            {orderedTransitions(run).length === 0 ? (
              <li className="text-fg-muted">No transitions.</li>
            ) : (
              orderedTransitions(run).map((transition) => (
                <li
                  key={transition.event_id}
                  data-testid={`transition-${transition.event_id}`}
                  className="rounded-lg border border-line bg-surface-elevated p-3"
                >
                  <p>
                    <strong>{transition.event_id}</strong>:{" "}
                    {transition.old_status} &rarr; {transition.new_status}
                  </p>
                  <p className="text-xs text-fg-muted">
                    Actor: {transition.actor} | Occurred:{" "}
                    {transition.occurred_at}
                  </p>
                  <p className="text-xs text-fg-muted">
                    Reason: {display(transition.reason)}
                  </p>
                  <p className="text-xs text-fg-muted">
                    Correlation: {transition.correlation_id}
                  </p>
                </li>
              ))
            )}
          </ol>
        </div>
      ) : null}
    </section>
  );
}
