// RED landing surface (K8; SPEC.md section 14 condition 5). Additive file
// (ADR 0014). The single-shell cockpit's landing surface is the RED portfolio
// command center: the bare root `/` rewrites to the native command center page
// so the deployed root renders the ranked interventions, while the chat-home
// deep links (`/?new=1`, `/?session=<id>`) pass through unchanged so the
// Executive chat stays reachable. This is a pure decision, so it is testable
// without the edge runtime; the middleware applies it. It approves nothing,
// spends nothing and deploys nothing.

export const RED_LANDING_PATH = "/operations/command-center";

// The path to rewrite to, or null to leave the request alone. Only the bare
// root (no query) lands on the command center; a query means a chat-home deep
// link, and every other path is a normal route.
export function landingRewrite(pathname: string, search: string): string | null {
  if (pathname !== "/") return null;
  if (search !== "") return null;
  return RED_LANDING_PATH;
}
