import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { landingRedirect } from "@/lib/redLanding";

// RED overlay (ADR 0011, ADR 0013). The single-shell cockpit's landing surface
// is the RED portfolio command center (SPEC.md section 14 condition 5): the
// bare root `/` redirects to the native command center page, while the
// chat-home deep links (`/?new=1`, `/?session=<id>`) pass through so the
// Executive chat stays reachable. The redirect (not a rewrite) is deliberate:
// `/` is an AppShell-exempt route, so a rewrite that kept the browser at `/`
// rendered the command center without the cockpit navigation; a redirect lands
// the browser on `/operations/command-center`, which AppShell wraps normally.
// The prototype is internal-only behind the 10.0.0.0/8 ingress allowlist, so the
// Auth.js gate stays disabled: only `/` is matched and the backend proxy treats
// every request as the principal (no x-caller-email), which the API accepts.
export const config = { matcher: ["/"] };

export default function middleware(request: NextRequest) {
  const target = landingRedirect(
    request.nextUrl.pathname,
    request.nextUrl.search,
  );
  if (target === null) return NextResponse.next();
  const url = request.nextUrl.clone();
  url.pathname = target;
  return NextResponse.redirect(url, 307);
}
