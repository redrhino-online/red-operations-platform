// Portfolio command center, native cockpit page (K3; SPEC.md section 14
// conditions 2 and 3, section 8). Additive file (ADR 0014). Pure presentational
// view over the ranked intervention cards the backend returns from
// `GET /red/interventions`: it renders the blockers the backend already ranked,
// their owner, next action, due date and affected builds, and it can dismiss no
// gate. The server decides what is surfaced (SPEC.md section 7); the UI only
// shows it and explains why.

import type { InterventionCard } from "@/lib/redOperationsApi";

export interface CommandCenterProps {
  interventions: InterventionCard[];
  loading?: boolean;
  error?: string | null;
  engagement?: string;
  on?: string;
}

export function activeInterventions(
  interventions: InterventionCard[],
): InterventionCard[] {
  return interventions.filter((card) => card.state !== "dismissed");
}

export function CommandCenter({
  interventions,
  loading = false,
  error = null,
  engagement,
  on,
}: CommandCenterProps) {
  const active = activeInterventions(interventions);
  const owners = Array.from(new Set(active.map((card) => card.owner))).sort();

  return (
    <section aria-labelledby="command-center-heading">
      <h1 id="command-center-heading" className="text-xl font-semibold text-fg">
        Portfolio command center
      </h1>
      <p className="mt-1 text-sm text-fg-muted">
        Ranked blockers and owners for {engagement ?? "the active engagement"}
        {on ? ` on ${on}` : ""}. The platform surfaces why each card is here; a
        card never grants approval.
      </p>

      {loading ? (
        <p role="status" className="mt-4 text-sm text-fg-muted">
          Loading interventions…
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-400">
          {error}
        </p>
      ) : null}

      <p data-testid="active-count" className="mt-4 text-sm text-fg-muted">
        {active.length} active intervention{active.length === 1 ? "" : "s"}
        {owners.length > 0 ? ` across ${owners.length} owner(s)` : ""}
      </p>

      {!loading && active.length === 0 ? (
        <p className="mt-2 text-sm text-fg-muted">No active interventions.</p>
      ) : null}

      {active.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-xl border border-line bg-surface-elevated">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-fg-muted">
              <tr className="border-b border-line">
                <th scope="col" className="px-3 py-2 font-medium">Severity</th>
                <th scope="col" className="px-3 py-2 font-medium">Blocked by</th>
                <th scope="col" className="px-3 py-2 font-medium">Owner</th>
                <th scope="col" className="px-3 py-2 font-medium">Next action</th>
                <th scope="col" className="px-3 py-2 font-medium">Due</th>
                <th scope="col" className="px-3 py-2 font-medium">Affected builds</th>
              </tr>
            </thead>
            <tbody>
              {active.map((card) => (
                <tr
                  key={`${card.client}/${card.reason}/${card.subject}`}
                  className="border-b border-line last:border-0 align-top"
                >
                  <td className="px-3 py-2 text-fg">{card.severity}</td>
                  <td className="px-3 py-2 text-fg">
                    <strong>{card.reason}</strong>
                    <br />
                    <span>{card.subject}</span>
                    <br />
                    <span className="text-fg-muted">{card.explanation}</span>
                  </td>
                  <td className="px-3 py-2 text-fg">{card.owner}</td>
                  <td className="px-3 py-2 text-fg">{card.next_action}</td>
                  <td className="px-3 py-2 text-fg">{card.due_on ?? "no due date"}</td>
                  <td className="px-3 py-2 text-fg">
                    {card.affected_builds.join(", ") || "none"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
