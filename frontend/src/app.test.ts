import { describe, it, expect } from "vitest";

// Phase 0 — just confirm the test runner is wired up.
// Real component tests start in Phase 1.

describe("scaffold", () => {
  it("test runner is configured", () => {
    expect(true).toBe(true);
  });

  it("environment is defined", () => {
    expect(typeof process).toBe("object");
  });
});