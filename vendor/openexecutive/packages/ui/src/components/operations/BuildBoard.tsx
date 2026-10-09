// Build board with dependency view, native cockpit page (K4; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). Pure presentational
// board over the tenant-scoped production work items the backend returns from
// `GET /red/builds`: it groups each BuildObject into its lifecycle state column
// in the SPEC.md section 4 order and renders, per build, the type, purpose,
// audience, owner, next action, the dependency refs it names and the blockers
// that stall it. An active build always shows an owner and a next action (SPEC.md
// section 3 invariant); a blocked build is surfaced in the dependency view. It
// holds no RED business logic: the backend owns the state machine, so the board
// shows the exact states and can transition no build.

import type { BuildObject } from "@/lib/redOperationsApi";

export interface BuildBoardProps {
  builds: BuildObject[];
  loading?: boolean;
  error?: string | null;
  tenantId?: string;
}

// The BuildObject lifecycle order from SPEC.md section 4. The board orders its
// columns by this sequence; an unknown state is shown last rather than dropped.
const BOARD_STATE_ORDER = [
  "identified",
  "source_required",
  "ready",
  "in_development",
  "internal_review",
  "client_review",
  "changes_requested",
  "approved",
  "production_ready",
  "deployed",
  "measuring",
  "optimizing",
  "superseded",
  "archived",
];

function stateRank(state: string): number {
  const index = BOARD_STATE_ORDER.indexOf(state);
  return index === -1 ? BOARD_STATE_ORDER.length : index;
}

// The lifecycle states present in the current builds, in canonical order, so the
// board renders a stable column set rather than a set ordered by arrival.
export function boardStates(builds: BuildObject[]): string[] {
  const states = new Set(builds.map((build) => build.state));
  return [...states].sort((a, b) => stateRank(a) - stateRank(b));
}

export function buildsInState(
  builds: BuildObject[],
  state: string,
): BuildObject[] {
  return builds
    .filter((build) => build.state === state)
    .sort((a, b) => a.build_id.localeCompare(b.build_id));
}

// The dependency refs a build names, sorted for stable display. A ref is the
// upstream asset or artifact the build depends on; the board does not resolve
// whether the ref is present, only what the build declares.
export function dependencyRefs(build: BuildObject): string[] {
  return [...build.refs].sort();
}

// The blocked builds in the current set, ordered by build id, for the dependency
// view that surfaces what stalls the active critical path.
export function blockedBuilds(builds: BuildObject[]): BuildObject[] {
  return builds
    .filter((build) => build.is_blocked)
    .sort((a, b) => a.build_id.localeCompare(b.build_id));
}

function stateLabel(state: string): string {
  return state.replace(/_/g, " ");
}

export function BuildBoard({
  builds,
  loading = false,
  error = null,
  tenantId,
}: BuildBoardProps) {
  const states = boardStates(builds);
  const blocked = blockedBuilds(builds);

  return (
    <section aria-labelledby="build-board-heading">
      <h1 id="build-board-heading" className="text-xl font-semibold text-fg">
        Build board
      </h1>
      <p className="mt-1 text-sm text-fg-muted">
        The production work items for {tenantId ?? "the active client"}, grouped
        by lifecycle state with each build&apos;s owner, next action and
        dependency refs.
      </p>

      {loading ? (
        <p role="status" className="mt-4 text-sm text-fg-muted">
          Loading builds…
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">
          {error}
        </p>
      ) : null}

      <p data-testid="build-count" className="mt-4 text-sm text-fg-muted">
        {builds.length} build{builds.length === 1 ? "" : "s"}
      </p>

      {!loading && builds.length === 0 ? (
        <p className="mt-2 text-sm text-fg-muted">No production builds.</p>
      ) : null}

      <section aria-labelledby="dependency-view-heading" className="mt-6">
        <h2 id="dependency-view-heading" className="text-sm font-medium text-fg">
          Dependency view
        </h2>
        <p data-testid="blocked-count" className="mt-1 text-sm text-fg-muted">
          {blocked.length} blocked build{blocked.length === 1 ? "" : "s"}
        </p>
        {blocked.length === 0 ? (
          <p className="mt-1 text-sm text-fg-muted">No blocked builds.</p>
        ) : (
          <ul className="mt-1 list-disc pl-5 text-sm text-fg">
            {blocked.map((build) => (
              <li key={build.build_id} data-testid={`blocked-${build.build_id}`}>
                {build.build_id}: {build.blockers.join(", ")}
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {states.map((state) => (
          <section
            key={state}
            aria-label={`${stateLabel(state)} column`}
            className="rounded-xl border border-line bg-surface-elevated p-4"
          >
            <h2 className="text-sm font-medium text-fg">{stateLabel(state)}</h2>
            {buildsInState(builds, state).map((build) => (
              <article
                key={build.build_id}
                aria-label={`Build ${build.build_id}`}
                className="mt-3 rounded-lg border border-line bg-surface p-3"
              >
                <h3 className="text-xs font-medium text-fg">
                  {build.build_id} <code>{build.build_type}</code>
                </h3>
                <p className="mt-1 text-xs text-fg-muted">{build.purpose}</p>
                <p className="text-xs text-fg-muted">Audience: {build.audience}</p>
                <p
                  data-testid={`build-owner-${build.build_id}`}
                  className="text-xs text-fg-muted"
                >
                  Owner: {build.owner}
                </p>
                <p
                  data-testid={`build-next-${build.build_id}`}
                  className="text-xs text-fg-muted"
                >
                  Next: {build.next_action}
                </p>
                <p
                  data-testid={`build-refs-${build.build_id}`}
                  className="text-xs text-fg-muted"
                >
                  Depends on: {dependencyRefs(build).join(", ") || "none"}
                </p>
                <p
                  data-testid={`build-blockers-${build.build_id}`}
                  className="text-xs text-fg-muted"
                >
                  Blocked by: {build.blockers.join(", ") || "none"}
                </p>
              </article>
            ))}
          </section>
        ))}
      </div>
    </section>
  );
}
