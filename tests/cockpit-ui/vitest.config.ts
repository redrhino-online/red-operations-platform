import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Repo-side component test runner for the ported RED cockpit pages (K2/K3;
// SPEC.md section 14 condition 3). It renders the additive cockpit components
// against the vendor source tree and asserts the rendered DOM. It is a test
// harness only: it approves nothing, spends nothing and deploys nothing.
const cockpitSrc = fileURLToPath(
  new URL("../../vendor/openexecutive/packages/ui/src", import.meta.url),
);

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": cockpitSrc,
    },
  },
  test: {
    environment: "jsdom",
    include: ["**/*.test.{ts,tsx}"],
    globals: true,
  },
});
