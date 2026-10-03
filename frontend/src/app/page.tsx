// RED Operations Director app shell (Q32; SPEC.md section 8, section 13
// condition 6). This is the thin client over the RED backend REST surface
// (`/red`, SPEC.md section 7). It carries no RED business logic: a screen reads
// state and proposes actions, it cannot grant approval or bypass a gate.
//
// The section 8 surfaces land incrementally in Q33-Q45. Each implemented
// surface is declared in `frontend/dod-screens.txt` so the DoD condition 6 gate
// (`scripts/check_frontend_screens.sh`) verifies it by route.

const surfaces = [
  { id: "portfolio-command-center", label: "Portfolio command center" },
  { id: "client-workspace-overview", label: "Client workspace overview" },
  { id: "source-and-claim-explorer", label: "Source and claim explorer" },
  { id: "transformation-map", label: "Transformation map" },
  { id: "offer-and-journey-editor", label: "Offer and journey editor" },
  { id: "build-board", label: "Build board with dependency view" },
  { id: "approval-inbox", label: "Approval inbox with exact version diff" },
  { id: "workflow-run-detail", label: "Workflow run detail" },
  { id: "launch-readiness", label: "Launch readiness" },
  { id: "performance-review", label: "Performance review" },
  { id: "portfolio-opportunities", label: "Portfolio opportunities" },
  { id: "authority-settings", label: "Authority settings" },
] as const;

export default function Home() {
  return (
    <section>
      <h1>RED Operations Platform</h1>
      <p style={{ color: "var(--red-muted)" }}>
        App shell. The RED backend serves the stage 0 to 10 pipeline under{" "}
        <code>/red</code>. The section 8 screens below are not yet implemented.
      </p>
      <ul>
        {surfaces.map((surface) => (
          <li key={surface.id}>{surface.label}</li>
        ))}
      </ul>
    </section>
  );
}
