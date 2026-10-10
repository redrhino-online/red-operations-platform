// RED landing surface (K8; SPEC.md section 14 condition 5). Additive file
// (ADR 0014). The single-shell cockpit's landing surface is the RED portfolio
// command center: the bare root `/` redirects to the native command center page
// so the deployed root renders the ranked interventions inside the cockpit
// shell — navigation included. A redirect (not a rewrite) is required because
// the browser keeps `/` on a rewrite, and `/` is an AppShell-exempt route (the
// chat home draws its own shell), so a rewritten root rendered the command
// center with no navigation. The chat-home deep links (`/?new=1`,
// `/?session=<id>`) redirect nowhere: `/` is still the Executive chat home for
// them. This is a pure decision, so it is testable without the edge runtime; the
// middleware applies it. It approves nothing, spends nothing and deploys nothing.

export const RED_LANDING_PATH = "/operations/command-center";

// The path to redirect to, or null to leave the request alone. Only the bare
// root (no query) lands on the command center; a query means a chat-home deep
// link, and every other path is a normal route.
export function landingRedirect(pathname: string, search: string): string | null {
  if (pathname !== "/") return null;
  if (search !== "") return null;
  return RED_LANDING_PATH;
}
