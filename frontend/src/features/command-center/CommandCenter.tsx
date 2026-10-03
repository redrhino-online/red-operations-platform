// Portfolio command center (SPEC.md sections 7 and 8; DoD condition 6, Q33).
//
// Pure presentational view over the ranked intervention cards the backend
// returns from `GET /red/interventions`. It holds no RED business logic: it
// renders the blockers the backend already ranked, their owner, next action,
// due date and affected builds, and it can dismiss no gate. The server decides
// what is surfaced (SPEC.md section 7); the UI only shows it and explains why.

import type { InterventionCard } from "@/shared/api/client";

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
      <h1 id="command-center-heading">Portfolio command center</h1>
      <p style={{ color: "var(--red-muted)" }}>
        Ranked blockers and owners for {engagement ?? "the active engagement"}
        {on ? ` on ${on}` : ""}. The platform surfaces why each card is here; a
        card never grants approval.
      </p>

      {loading ? <p role="status">Loading interventions...</p> : null}
      {error ? <p role="alert">{error}</p> : null}

      <p data-testid="active-count">
        {active.length} active intervention{active.length === 1 ? "" : "s"}
        {owners.length > 0 ? ` across ${owners.length} owner(s)` : ""}
      </p>

      {!loading && active.length === 0 ? (
        <p>No active interventions.</p>
      ) : null}

      {active.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th scope="col">Severity</th>
              <th scope="col">Blocked by</th>
              <th scope="col">Owner</th>
              <th scope="col">Next action</th>
              <th scope="col">Due</th>
              <th scope="col">Affected builds</th>
            </tr>
          </thead>
          <tbody>
            {active.map((card) => (
              <tr key={`${card.client}/${card.reason}/${card.subject}`}>
                <td>{card.severity}</td>
                <td>
                  <strong>{card.reason}</strong>
                  <br />
                  <span>{card.subject}</span>
                  <br />
                  <span style={{ color: "var(--red-muted)" }}>
                    {card.explanation}
                  </span>
                </td>
                <td>{card.owner}</td>
                <td>{card.next_action}</td>
                <td>{card.due_on ?? "no due date"}</td>
                <td>{card.affected_builds.join(", ") || "none"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
