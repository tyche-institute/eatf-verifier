import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { unzipSync, zipSync } from "fflate";
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

  test("accepts an explicitly pinned signer key", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "minimal-roundtrip/package.aep"));
    const signerKey = await readFile(resolve("../test-vectors/keys/dev-rsa-4096.pem"), "utf8");

    const result = await verify(bytes, {
      tsaTrustList: [],
      trustedSignerPems: [signerKey],
    });

    expect(result.valid).toBe(true);
    expect(result.report).toContain("Signer public key matched the caller-supplied trust set.");
  });

  test("rejects a signer outside an explicit trust set", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "minimal-roundtrip/package.aep"));
    const otherPem = await readFile(resolve("../test-vectors/keys/dev-tsa-rsa-3072.pem"), "utf8");

    const result = await verify(bytes, {
      tsaTrustList: [],
      trustedSignerPems: [otherPem],
    });

    expect(result.valid).toBe(false);
    expect(result.failureReason).toContain("caller-supplied trust set");
  });

  test("current signer output binds metadata even if receipt is changed with it", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "minimal-roundtrip/package.aep"));
    const entries = unzipSync(bytes);
    const metadata = JSON.parse(
      new TextDecoder().decode(entries["metadata.json"]),
    ) as Record<string, unknown>;
    const receipt = JSON.parse(
      new TextDecoder().decode(entries["overt_receipt.json"]),
    ) as Record<string, unknown>;
    metadata.policy_decision = "deny";
    (receipt.policy as Record<string, unknown>).decision = "deny";
    entries["metadata.json"] = new TextEncoder().encode(JSON.stringify(metadata) + "\n");
    entries["overt_receipt.json"] = new TextEncoder().encode(JSON.stringify(receipt) + "\n");

    const result = await verify(zipSync(entries, { level: 0 }), { tsaTrustList: [] });

    expect(result.valid).toBe(false);
    expect(result.failureReason).toContain("canonical.bin");
  });

  test("current signer output rejects changes to receipt-only fields", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "minimal-roundtrip/package.aep"));
    const entries = unzipSync(bytes);
    const receipt = JSON.parse(
      new TextDecoder().decode(entries["overt_receipt.json"]),
    ) as Record<string, unknown>;
    receipt.scope = "foundational:changed-after-signing";
    entries["overt_receipt.json"] = new TextEncoder().encode(JSON.stringify(receipt) + "\n");

    const result = await verify(zipSync(entries, { level: 0 }), { tsaTrustList: [] });

    expect(result.valid).toBe(false);
    expect(result.failureReason).toContain("receipt signature");
  });

  test("signed metadata prevents deleting the receipt signature", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "minimal-roundtrip/package.aep"));
    const entries = unzipSync(bytes);
    delete entries["overt_receipt.sig"];

    const result = await verify(zipSync(entries, { level: 0 }), { tsaTrustList: [] });

    expect(result.valid).toBe(false);
    expect(result.failureReason).toContain("overt_receipt.sig");
  });
});
