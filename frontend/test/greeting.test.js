import assert from "node:assert/strict";
import test from "node:test";

import { createGreeting } from "../src/greeting.js";

test("creates a greeting for a supplied name", () => {
  assert.equal(createGreeting("FDE"), "Hello, FDE!");
});

test("falls back to World for an empty name", () => {
  assert.equal(createGreeting("  "), "Hello, World!");
});
