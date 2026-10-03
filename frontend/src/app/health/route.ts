// Liveness probe for the UI container (Q32). It reports only that the Next.js
// server is serving; the backend health is `/red/health` (SPEC.md section 10
// health probes on the Helm chart).
export function GET() {
  return Response.json({ status: "ok", service: "red-operations-ui" });
}
