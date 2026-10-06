import type { NextConfig } from "next";

// The UI is a thin client. It holds no RED business logic (ADR 0007) and calls
// the RED backend REST surface (SPEC.md section 7) under `/red`.
const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // ADR 0012: when the vendor cockpit owns the root, the RED screens are
  // served under a subpath (e.g. /screens). Empty in local dev and tests.
  basePath: process.env.NEXT_PUBLIC_RED_BASE_PATH || undefined,
};

export default nextConfig;
