import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("../src/middleware.ts", import.meta.url), "utf8");

test("the internal RED overlay disables the Auth.js route gate", () => {
  assert.match(source, /config\s*=\s*\{\s*matcher:\s*\[\s*\]\s*\}/);
  assert.match(source, /export default function middleware\(\)\s*\{\s*\}/);
});
