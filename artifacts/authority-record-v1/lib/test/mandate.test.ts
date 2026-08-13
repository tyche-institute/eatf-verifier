/**
 * Detached-mandate sign-and-verify behaviour (spec §4.5).
 *
 * Builds packages in memory with sign() and a mandate signed by the
 * committed test-granting-authority keypair — a TEST principal distinct
 * from both the package issuer and the epistemic accepting authority;
 * see test-vectors/keys/README.md. Frozen byte-level vectors live under
 * test-vectors/mandate/ and are exercised by mandate-vectors.test.ts;
 * this suite pins the semantics: the binding family rejects (including
 * the response-only form, deliberately unlike §4.2 and §4.3), scope and
 * temporal containment report without rejecting, and a named principal
 * with no signed mandate claims nothing.
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
const grantingPrivate = readFileSync(resolve(KEYS_DIR, "test-granting-authority.key"), "utf8");
const grantingPublic = readFileSync(resolve(KEYS_DIR, "test-granting-authority.pem"), "utf8");

// Reuse the RFC 3161 token from a committed vector (genTime 2026-01-01).
const timestampTsr = unzipSync(new Uint8Array(readFileSync(TSR_SOURCE)))["timestamp.tsr"]!;

const ZIP_ENTRY_MTIME = new Date(1980, 0, 2);

const AGENT_ID = "urn:eatf:tenant:demo:agent:mandate-unit";
const GRANTING_PRINCIPAL = "urn:eatf:mandate:demo:granting-authority";
const MANDATE_ID = "urn:eatf:mandate:demo:mandate:unit-0001";

const metadata = {
  schema: "urn:eatf:spec:aep:metadata:1.0",
  attestation_id: "att_mandate_unit_01",
  created_at: "2026-08-05T00:00:00Z",
  agent_id: AGENT_ID,
  action_type: "foundational:aep-response",
  policy_id: "atap-basic",
  policy_version: "1.0",
  policy_coverage: 1.0,
  policy_decision: "allow",
};

const authorizingPrincipal = { principal: GRANTING_PRINCIPAL, mandate_ref: MANDATE_ID };

/** Author a mandate and sign it with the granting authority's key. */
function makeMandate(
  overrides: Record<string, unknown> = {},
  signWithKey: string = grantingPrivate,
): { json: Record<string, unknown>; sig: string } {
  const record: Record<string, unknown> = {
    mandate_id: MANDATE_ID,
    mandate_version: "1.0",
    principal: GRANTING_PRINCIPAL,
    subject: AGENT_ID,
    granted_at: "2026-08-05T00:00:00Z",
    statement: "The granting authority authorises the subject agent to act under policy atap-basic.",
    scope: {
      action_types: ["foundational:aep-response"],
      policy_ids: ["atap-basic"],
    },
    valid_from: "2025-07-01T00:00:00Z",
    valid_until: "2026-07-01T00:00:00Z",
    public_key: grantingPublic,
    ...overrides,
  };
  const signer = createSign("sha256");
  signer.update(jcs(record));
  signer.end();
  return { json: record, sig: signer.sign(signWithKey).toString("base64") };
}

async function pack(
  input: {
    mandate?: { json: Record<string, unknown>; sig: string };
    authorizingPrincipal?: Record<string, unknown>;
    canonicalForm?: "profile" | "response-only";
    metadataOverrides?: Record<string, unknown>;
    omitAuthorizingPrincipal?: boolean;
  } = {},
): Promise<Uint8Array> {
  const result = await sign({
    payload: "EATF mandate unit test payload.\n",
    privateKeyPem: devPrivate,
    publicKeyPem: devPublic,
    metadata: { ...metadata, ...(input.metadataOverrides ?? {}) },
    overtScope: "foundational:aep-response",
    timestampTsr,
    canonicalForm: input.canonicalForm ?? "profile",
    mandate: input.mandate,
    authorizingPrincipal: input.omitAuthorizingPrincipal
      ? undefined
      : (input.authorizingPrincipal ?? authorizingPrincipal),
  });
  return result.aep;
}

describe("detached mandate (§4.5)", () => {
  test("a signed, bound, in-scope mandate verifies and every check passes", async () => {
    const result = await verify(await pack({ mandate: makeMandate() }));
    expect(result.valid).toBe(true);
    expect(result.mandate).toMatchObject({
      claimed: true,
      present: true,
      bound: true,
      signatureVerified: true,
      inScope: true,
      temporalContainment: true,
      principal: GRANTING_PRINCIPAL,
    });
    for (const id of ["mandate-digest", "mandate-parse", "mandate-bound", "mandate-signature"]) {
      const row = result.boundary.checks.find((c) => c.id === id)!;
      expect(row.verdict, id).toBe("pass");
      expect(row.enforced, id).toBe(true);
    }
  });

  test("the mandate signature is verified against a key distinct from the package issuer", async () => {
    // The issuer's own key must not be able to stand in for the granting
    // authority's: the record names one key and the signature must be made
    // with its private half.
    const result = await verify(await pack({ mandate: makeMandate({}, devPrivate) }));
    expect(result.valid).toBe(false);
    expect(result.failureReason).toBe(
      "mandate.json invalid: mandate.sig does not verify against the mandate's public_key.",
    );
    expect(result.mandate?.signatureVerified).toBe(false);
  });

  test("a missing mandate.sig rejects", async () => {
    const aep = await pack({ mandate: makeMandate() });
    const entries = { ...unzipSync(aep) };
    delete entries["mandate.sig"];
    const result = await verify(zipSync(entries, { level: 0, mtime: ZIP_ENTRY_MTIME }));
    expect(result.valid).toBe(false);
    expect(result.failureReason).toBe("mandate.json invalid: mandate.sig entry is missing.");
  });

  test("record bytes that are not JCS-canonical reject", async () => {
    const mandate = makeMandate();
    const aep = await pack({ mandate });
    const entries = { ...unzipSync(aep) };
    // Re-serialise with whitespace: same JSON value, different bytes, so
    // the digest reference no longer matches either.
    entries["mandate.json"] = new TextEncoder().encode(JSON.stringify(mandate.json, null, 2));
    const result = await verify(zipSync(entries, { level: 0, mtime: ZIP_ENTRY_MTIME }));
    expect(result.valid).toBe(false);
    expect(result.failureReason).toBe(
      "mandate.json invalid: digest does not match authorizing_principal.mandate_digest.",
    );
  });

  test("a record missing a required field rejects at the record check", async () => {
    const base = makeMandate().json;
    delete base["statement"];
    const signer = createSign("sha256");
    signer.update(jcs(base));
    signer.end();
    const resigned = { json: base, sig: signer.sign(grantingPrivate).toString("base64") };
    const result = await verify(await pack({ mandate: resigned }));
    expect(result.valid).toBe(false);
    expect(result.failureReason).toBe("mandate.json invalid: statement is required.");
  });

  test("the response-only form rejects the mandate rather than reporting it unbound", async () => {
    const result = await verify(await pack({ mandate: makeMandate(), canonicalForm: "response-only" }));
    expect(result.valid).toBe(false);
    expect(result.mandate?.bound).toBe(false);
    expect(result.failureReason).toBe(
      "mandate.json invalid: the response-only canonical form leaves authorizing_principal.mandate_digest outside signature.sig.",
    );
    // The contrast that makes the choice deliberate: under the same form a
    // warrant and an acceptance are reported and accepted, not rejected.
    expect(result.boundary.checks.find((c) => c.id === "mandate-bound")).toMatchObject({
      verdict: "fail",
      enforced: true,
    });
  });

  test("scope is appraisal: an action outside the grant reports and does not reject", async () => {
    const narrow = makeMandate({
      scope: { action_types: ["agentic-extended:mcp-tools-call"], policy_ids: ["atap-basic"] },
    });
    const result = await verify(await pack({ mandate: narrow }));
    expect(result.valid).toBe(true);
    expect(result.mandate?.inScope).toBe(false);
    expect(result.boundary.checks.find((c) => c.id === "mandate-scope")).toMatchObject({
      verdict: "fail",
      enforced: false,
    });
  });

  test("temporal containment is appraisal: an expired mandate reports and does not reject", async () => {
    const expired = makeMandate({
      valid_from: "2024-01-01T00:00:00Z",
      valid_until: "2025-12-31T23:59:59Z",
    });
    const result = await verify(await pack({ mandate: expired }));
    expect(result.valid).toBe(true);
    expect(result.mandate?.temporalContainment).toBe(false);
    expect(result.boundary.checks.find((c) => c.id === "mandate-temporal")).toMatchObject({
      verdict: "fail",
      enforced: false,
    });
  });

  test("a named principal without a signed mandate claims nothing", async () => {
    const result = await verify(await pack({}));
    expect(result.valid).toBe(true);
    expect(result.mandate).toMatchObject({ claimed: false, present: false, bound: null });
    for (const id of [
      "mandate-digest",
      "mandate-parse",
      "mandate-bound",
      "mandate-signature",
      "mandate-scope",
      "mandate-temporal",
    ]) {
      const row = result.boundary.checks.find((c) => c.id === id)!;
      expect(row.verdict, id).toBe("not_determinate");
      expect(row.enforced, id).toBe(false);
    }
  });

  test("a package with no authorizing principal reports the mandate checks as not assessed", async () => {
    const result = await verify(await pack({ omitAuthorizingPrincipal: true }));
    expect(result.valid).toBe(true);
    expect(result.mandate).toBeNull();
    const row = result.boundary.checks.find((c) => c.id === "mandate-digest")!;
    expect(row.verdict).toBe("not_assessed");
    expect(row.reason).toBe("input_absent");
  });

  test("a mandate.json smuggled in without a digest reference rejects", async () => {
    const mandate = makeMandate();
    const aep = await pack({});
    const entries = { ...unzipSync(aep) };
    entries["mandate.json"] = jcs(mandate.json);
    entries["mandate.sig"] = new TextEncoder().encode(mandate.sig + "\n");
    const result = await verify(zipSync(entries, { level: 0, mtime: ZIP_ENTRY_MTIME }));
    expect(result.valid).toBe(false);
    expect(result.failureReason).toBe(
      "mandate.json invalid: mandate.json is packaged but metadata.authorizing_principal.mandate_digest is missing.",
    );
  });
});
