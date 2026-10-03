import type { NextConfig } from "next";

// The UI is a thin client. It holds no RED business logic (ADR 0007) and calls
// the RED backend REST surface (SPEC.md section 7) under `/red`.
const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
};

export default nextConfig;
