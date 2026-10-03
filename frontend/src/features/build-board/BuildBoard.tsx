// Build board with dependency view (SPEC.md sections 3, 4 and 8; DoD condition
// 6, Q38).
//
// Pure presentational board over the tenant-scoped production work items the
// backend returns from `GET /red/builds`. It groups each BuildObject into its
// lifecycle state column in the SPEC.md section 4 order and renders, per build,
// the type, purpose, audience, owner, next action, the dependency refs it names
// and the blockers that stall it. An active build always shows an owner and a
// next action (SPEC.md section 3 invariant); a blocked build is surfaced in the
// dependency view. It holds no RED business logic: the backend owns the state
// machine, so the board shows the exact states and can transition no build.

import type { BuildObject } from "@/shared/api/client";

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
      <h1 id="build-board-heading">Build board</h1>
      <p style={{ color: "var(--red-muted)" }}>
        The production work items for {tenantId ?? "the active client"}, grouped by
        lifecycle state with each build&apos;s owner, next action and dependency
        refs.
      </p>

      {loading ? <p role="status">Loading builds...</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <p data-testid="build-count">
        {builds.length} build{builds.length === 1 ? "" : "s"}
      </p>

      {!loading && builds.length === 0 ? <p>No production builds.</p> : null}

      <section aria-labelledby="dependency-view-heading">
        <h2 id="dependency-view-heading">Dependency view</h2>
        <p data-testid="blocked-count">
          {blocked.length} blocked build{blocked.length === 1 ? "" : "s"}
        </p>
        {blocked.length === 0 ? (
          <p>No blocked builds.</p>
        ) : (
          <ul>
            {blocked.map((build) => (
              <li key={build.build_id} data-testid={`blocked-${build.build_id}`}>
                {build.build_id}: {build.blockers.join(", ")}
              </li>
            ))}
          </ul>
        )}
      </section>

      {states.map((state) => (
        <section key={state} aria-label={`${stateLabel(state)} column`}>
          <h2>{stateLabel(state)}</h2>
          {buildsInState(builds, state).map((build) => (
            <article key={build.build_id} aria-label={`Build ${build.build_id}`}>
              <h3>
                {build.build_id} <code>{build.build_type}</code>
              </h3>
              <p>{build.purpose}</p>
              <p>Audience: {build.audience}</p>
              <p data-testid={`build-owner-${build.build_id}`}>
                Owner: {build.owner}
              </p>
              <p data-testid={`build-next-${build.build_id}`}>
                Next: {build.next_action}
              </p>
              <p data-testid={`build-refs-${build.build_id}`}>
                Depends on: {dependencyRefs(build).join(", ") || "none"}
              </p>
              <p data-testid={`build-blockers-${build.build_id}`}>
                Blocked by: {build.blockers.join(", ") || "none"}
              </p>
            </article>
          ))}
        </section>
      ))}
    </section>
  );
}
