import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("../src/middleware.ts", import.meta.url), "utf8");

test("the internal RED overlay matches only the root and disables the Auth.js route gate", () => {
  // The landing rewrite matches only `/`; every other route is untouched.
  assert.match(source, /config\s*=\s*\{\s*matcher:\s*\[\s*"\/"\s*\]\s*\}/);
  // The Auth.js gate stays disabled: the middleware never imports or calls it.
  assert.doesNotMatch(source, /from\s+["']@\/auth["']/);
  assert.doesNotMatch(source, /\bauth\s*\(/);
  // The root rewrite is the pure landing decision (K8).
  assert.match(source, /landingRewrite/);
});
