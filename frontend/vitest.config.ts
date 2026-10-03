import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Browser test runner for the RED frontend (Q33; SPEC.md section 13 condition
// 6). Vitest with a jsdom environment renders the screens under
// `src/features` and `src/app` and asserts the rendered DOM. It is a test
// harness only: it approves nothing, spends nothing and deploys nothing.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    globals: true,
  },
});
