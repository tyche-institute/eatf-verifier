import { describe, expect, test } from "vitest";

import { parseAndValidateOvertReceipt } from "../src/overt.js";

const enc = new TextEncoder();

const HASH = "a".repeat(64);

const metadata = {
  created_at: "2026-05-14T12:00:00Z",
  agent_id: "urn:eatf:tenant:test:agent:mcp-gateway",
  action_type: "mcp.tools/call",
  policy_version: "1.0",
  policy_coverage: 1,
};

function entries(receipt: Record<string, unknown>) {
  return {
    "signature.sig": enc.encode("ZmFrZQ=="),
    "timestamp.tsr": enc.encode("ZmFrZQ=="),
    "overt_receipt.json": enc.encode(JSON.stringify(receipt)),
  };
}

function validReceipt(): Record<string, unknown> {
  return {
    overt: "1.0.0",
    profile: "urn:eatf:spec:aep:1.0",
    profile_revision: "1.0-draft",
    scope: "agentic-extended:mcp-tools-call",
    subject: {
      agent_id: metadata.agent_id,
      tenant_hash: null,
      system: "eatf-aep",
      revision: "1.0-draft",
    },
    event: {
      type: "eatf.response",
      timestamp: metadata.created_at,
      action_type: metadata.action_type,
    },
    policy: {
      id: null,
      version: metadata.policy_version,
      coverage: metadata.policy_coverage,
    },
    content_hash: `sha256:${HASH}`,
    prev: null,
    witness: {
      iap: "EATF.eu",
      signature_refs: ["signature.sig"],
      timestamp_refs: ["timestamp.tsr"],
    },
  };
}

describe("OVERT receipt validation", () => {
  test("accepts a receipt bound to package hash, metadata, and witness files", () => {
    const result = parseAndValidateOvertReceipt(entries(validReceipt()), metadata, HASH);

    expect(result.error).toBeNull();
    expect(result.receipt?.scope).toBe("agentic-extended:mcp-tools-call");
  });

  test("rejects content_hash tampering", () => {
    const receipt = validReceipt();
    receipt.content_hash = `sha256:${"0".repeat(64)}`;

    const result = parseAndValidateOvertReceipt(entries(receipt), metadata, HASH);

    expect(result.error).toContain("content_hash");
  });

  test("rejects missing witness references", () => {
    const missing = parseAndValidateOvertReceipt(
      {
        "timestamp.tsr": enc.encode("ZmFrZQ=="),
        "overt_receipt.json": enc.encode(JSON.stringify(validReceipt())),
      },
      metadata,
      HASH,
    );

    expect(missing.error).toContain("missing file signature.sig");
  });
});
