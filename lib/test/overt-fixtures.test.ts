import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

import { verify } from "../src/verifier.js";

// Shared test vectors live at the repository root under test-vectors/.
// vitest runs with cwd == lib/, so the relative path is ../test-vectors/.
const VALID_DIR = resolve("../test-vectors/valid");
const INVALID_DIR = resolve("../test-vectors/invalid");

describe("OVERT .aep golden fixtures", () => {
  test("accepts the valid OVERT profile fixture", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "valid-overt-profile/package.aep"));

    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.overtReceipt?.scope).toBe("foundational:aep-response");
    expect(result.report.some((line) => line.includes("OVERT receipt verified"))).toBe(true);
  });

  test("rejects the tampered OVERT receipt fixture", async () => {
    const bytes = await readFile(resolve(INVALID_DIR, "tampered-overt-receipt/package.aep"));

    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(false);
    expect(result.failureReason).toContain("overt_receipt.json invalid");
  });

  test("accepts the MCP tools/call allow fixture", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "mcp-tools-call-valid/package.aep"));

    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.overtReceipt?.scope).toBe("agentic-extended:mcp-tools-call");
    expect((result.overtReceipt?.policy as Record<string, unknown>).decision).toBe("allow");
  });

  test("accepts the MCP tools/call denied-policy fixture", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "mcp-tools-call-denied-policy/package.aep"));

    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.overtReceipt?.scope).toBe("agentic-extended:mcp-tools-call");
    expect((result.overtReceipt?.policy as Record<string, unknown>).decision).toBe("deny");
  });
});
