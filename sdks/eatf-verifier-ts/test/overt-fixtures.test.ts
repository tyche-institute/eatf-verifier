import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

import { verify } from "../src/verifier.js";

const FIXTURE_DIR = resolve("../../backend/src/test/resources/fixtures/overt");

describe("OVERT .aep golden fixtures", () => {
  test("accepts the Java-generated valid OVERT fixture", async () => {
    const bytes = await readFile(resolve(FIXTURE_DIR, "valid-overt-profile.aep"));

    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.overtReceipt?.scope).toBe("foundational:aep-response");
    expect(result.report.some((line) => line.includes("OVERT receipt verified"))).toBe(true);
  });

  test("rejects the tampered OVERT receipt fixture", async () => {
    const bytes = await readFile(resolve(FIXTURE_DIR, "tampered-overt-receipt.aep"));

    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(false);
    expect(result.failureReason).toContain("overt_receipt.json invalid");
  });

  test("accepts the MCP tools/call allow fixture", async () => {
    const bytes = await readFile(resolve(FIXTURE_DIR, "mcp-tools-call-valid.aep"));

    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.overtReceipt?.scope).toBe("agentic-extended:mcp-tools-call");
    expect((result.overtReceipt?.policy as Record<string, unknown>).decision).toBe("allow");
  });

  test("accepts the MCP tools/call denied-policy fixture", async () => {
    const bytes = await readFile(resolve(FIXTURE_DIR, "mcp-tools-call-denied-policy.aep"));

    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.overtReceipt?.scope).toBe("agentic-extended:mcp-tools-call");
    expect((result.overtReceipt?.policy as Record<string, unknown>).decision).toBe("deny");
  });
});
