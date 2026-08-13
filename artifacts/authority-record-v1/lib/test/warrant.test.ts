/**
 * Warrant sign-and-verify behaviour (spec §4.2).
 *
 * Builds packages in memory with sign() and a warrant accepted by the
 * committed test-accepting-authority keypair — a TEST principal; see
 * test-vectors/keys/README.md. Frozen byte-level vectors live under
 * test-vectors/warrant/ and are exercised by warrant-vectors.test.ts;
 * this suite pins the semantics: binding-family inconsistencies
 * reject, appraisal outcomes (applicability, freshness) report and
 * never reject, and response-only packages carry an unbound warrant.
 */

import { createSign } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { unzipSync, zipSync } from "fflate";
import { describe, expect, test } from "vitest";

import { verify } from "../src/verifier.js";
import { sign } from "../src/signer.js";
import { jcs } from "../src/canonical.js";

const KEYS_DIR = resolve("../test-vectors/keys");
const TSR_SOURCE = resolve("../test-vectors/valid/valid-overt-profile/package.aep");

const devPrivate = readFileSync(resolve(KEYS_DIR, "dev-rsa-4096.key"), "utf8");
const devPublic = readFileSync(resolve(KEYS_DIR, "dev-rsa-4096.pem"), "utf8");
const authorityPrivate = readFileSync(resolve(KEYS_DIR, "test-accepting-authority.key"), "utf8");
const authorityPublic = readFileSync(resolve(KEYS_DIR, "test-accepting-authority.pem"), "utf8");

// Reuse the RFC 3161 token from a committed vector (genTime 2026-01-01).
const timestampTsr = unzipSync(
  new Uint8Array(readFileSync(TSR_SOURCE)),
)["timestamp.tsr"]!;

const ZIP_ENTRY_MTIME = new Date(1980, 0, 2);

const metadata = {
  schema: "urn:eatf:spec:aep:metadata:1.0",
  attestation_id: "att_warrant_unit_01",
  created_at: "2026-08-05T00:00:00Z",
  agent_id: "urn:eatf:tenant:demo:agent:warrant-unit",
  action_type: "foundational:aep-response",
  policy_id: "atap-basic",
  policy_version: "1.0",
  policy_coverage: 1.0,
  policy_decision: "allow",
};

/** Author a warrant against the demo policy and sign its acceptance. */
function makeAcceptedWarrant(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  const warrant: Record<string, unknown> = {
    warrant_id: "urn:eatf:warrant:demo:atap-basic-allow-01",
    warrant_version: "1.0",
    policy_ref: { policy_id: "atap-basic", policy_version: "1.0" },
    inference_form: "policy-evaluation",
    statement:
      "Outputs that policy atap-basic 1.0 evaluates to allow are licensed for the action class foundational:aep-response.",
    applies_to: {
      action_types: ["foundational:aep-response"],
      policy_decisions: ["allow"],
    },
    valid_from: "2025-07-01T00:00:00Z",
    valid_until: "2026-07-01T00:00:00Z",
    ...overrides,
  };
  const acceptance: Record<string, unknown> = {
    authority_id: "test-accepting-authority",
    accepted_at: "2026-08-05T00:00:00Z",
    public_key: authorityPublic,
  };
  const signer = createSign("sha256");
  signer.update(jcs({ ...warrant, acceptance }));
  signer.end();
  acceptance.signature = signer.sign(authorityPrivate).toString("base64");
  return { ...warrant, acceptance };
}

async function signWith(
  warrant: Record<string, unknown> | undefined,
  canonicalForm: "profile" | "response-only" = "profile",
) {
  return sign({
    payload: "Warrant unit-test payload.\n",
    privateKeyPem: devPrivate,
    publicKeyPem: devPublic,
    metadata,
    overtScope: "foundational:aep-response",
    timestampTsr,
    canonicalForm,
    warrant,
  });
}

describe("warrant cross-check", () => {
  test("profile-form package with an accepted warrant verifies; appraisal fields populated", async () => {
    const { aep } = await signWith(makeAcceptedWarrant());
    const result = await verify(aep, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.warrant).toEqual({
      present: true,
      bound: true,
      policyLinked: true,
      applicable: true,
      acceptanceVerified: true,
      // genTime 2026-01-01 lies inside the window, but no shipped TSA
      // token chains to a trusted root, so freshness stays open.
      fresh: null,
    });
    expect(result.report).toContain(
      "Warrant verified (urn:eatf:warrant:demo:atap-basic-allow-01, accepted by test-accepting-authority).",
    );
    const row = result.boundary.checks.find((c) => c.id === "warrant-freshness");
    expect(row).toMatchObject({ verdict: "not_determinate", reason: "option_disabled" });
  });

  test("package without a warrant reports warrant: null and input_absent checks", async () => {
    const { aep } = await signWith(undefined);
    const result = await verify(aep, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.warrant).toBeNull();
    for (const id of [
      "warrant-digest",
      "warrant-parse",
      "warrant-bound",
      "warrant-policy-link",
      "warrant-applicability",
      "warrant-acceptance-signature",
      "warrant-freshness",
    ]) {
      expect(
        result.boundary.checks.find((c) => c.id === id),
        id,
      ).toMatchObject({ verdict: "not_assessed", enforced: false, reason: "input_absent" });
    }
  });

  test("response-only package carries the warrant unbound, and stays accepted", async () => {
    const { aep } = await signWith(makeAcceptedWarrant(), "response-only");
    const result = await verify(aep, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.canonicalForm).toBe("response-only");
    expect(result.warrant).toMatchObject({ present: true, bound: false, acceptanceVerified: true });
    expect(result.boundary.checks.find((c) => c.id === "warrant-bound")).toMatchObject({
      verdict: "fail",
      enforced: false,
    });
    expect(result.boundary.unsignedFields).toContain("metadata.warrant_digest");
  });

  test("tampering warrant.json after signing fails the digest binding", async () => {
    const { aep } = await signWith(makeAcceptedWarrant());
    const entries = unzipSync(aep);
    const warrant = JSON.parse(new TextDecoder().decode(entries["warrant.json"]!));
    warrant.statement = "Rewritten after signing.";
    entries["warrant.json"] = jcs(warrant);
    const result = await verify(zipSync(entries, { level: 0, mtime: ZIP_ENTRY_MTIME }), {
      tsaTrustList: [],
    });

    expect(result.valid).toBe(false);
    expect(result.failureReason).toBe("warrant.json invalid: digest does not match metadata.warrant_digest.");
    expect(result.warrant).toMatchObject({ present: true, bound: null });
    expect(result.boundary.checks.find((c) => c.id === "warrant-digest")).toMatchObject({
      verdict: "fail",
      enforced: true,
    });
    // Everything behind the failed binding is shadow, not assessment.
    expect(result.boundary.checks.find((c) => c.id === "warrant-acceptance-signature")).toMatchObject({
      verdict: "not_assessed",
      reason: "short_circuited",
    });
  });

  test("an inapplicable warrant reports may-inform-cannot-compel and does not reject", async () => {
    const warrant = makeAcceptedWarrant({
      applies_to: {
        action_types: ["agentic-extended:mcp-tools-call"],
        policy_decisions: ["allow"],
      },
    });
    const { aep } = await signWith(warrant);
    const result = await verify(aep, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.warrant).toMatchObject({ applicable: false, acceptanceVerified: true });
    expect(result.report).toContain(
      "Warrant does not apply to this action: the output may inform but carries no warrant to compel.",
    );
    expect(result.boundary.checks.find((c) => c.id === "warrant-applicability")).toMatchObject({
      verdict: "fail",
      enforced: false,
    });
  });

  test("a stale warrant reports fresh=false and does not reject", async () => {
    const warrant = makeAcceptedWarrant({
      valid_from: "2024-01-01T00:00:00Z",
      valid_until: "2025-12-31T23:59:59Z",
    });
    const { aep } = await signWith(warrant);
    const result = await verify(aep, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.warrant).toMatchObject({ fresh: false, acceptanceVerified: true });
    expect(result.boundary.checks.find((c) => c.id === "warrant-freshness")).toMatchObject({
      verdict: "fail",
      enforced: false,
    });
  });

  test("a forged acceptance signature rejects", async () => {
    const warrant = makeAcceptedWarrant();
    // Re-sign the acceptance with the WRONG key (the dev packaging key),
    // leaving the authority's public key in place.
    const acceptance = warrant.acceptance as Record<string, unknown>;
    const unsigned = { ...warrant, acceptance: { ...acceptance } };
    delete (unsigned.acceptance as Record<string, unknown>).signature;
    const signer = createSign("sha256");
    signer.update(jcs(unsigned));
    signer.end();
    acceptance.signature = signer.sign(devPrivate).toString("base64");

    const { aep } = await signWith(warrant);
    const result = await verify(aep, { tsaTrustList: [] });

    expect(result.valid).toBe(false);
    expect(result.failureReason).toBe(
      "warrant.json invalid: acceptance.signature does not verify against acceptance.public_key.",
    );
    expect(result.warrant).toMatchObject({ acceptanceVerified: false });
  });
});
