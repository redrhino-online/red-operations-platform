// RED overlay (ADR 0011). The prototype is internal-only behind the
// 10.0.0.0/8 ingress allowlist, so the Auth.js gate is disabled: no route is
// matched, the middleware never runs, and the backend proxy treats every
// request as the principal (no x-caller-email), which the API accepts.
export const config = { matcher: [] };

export default function middleware() {}
