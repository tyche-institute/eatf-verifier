/**
 * Issuer key pinning (spec §8.1) — the boundary of the remedy.
 *
 * `test-vectors/boundary/reauthored-package-issuer-substitution` is a
 * frozen package in which an adversary holding a key of its own flipped
 * the recorded policy decision from deny to allow and then re-authored
 * everything the flip invalidates: canonical.bin, hash.sha256, the OVERT
 * receipt's content_hash, signature.sig and public_key.pem. The profile
 * canonical form does NOT close that class, and neither does the signed
 * mandate — a mandate binds who authorised the agent to act, not which
 * decision the policy reached.
 *
 * The same frozen bytes are verified twice here: once with no expectation
 * about the issuer (the self-attestation default, valid) and once with the
 * real issuer's key pinned (rejected). This is the only obligation in the
 * profile that separates the two packages, and it is caller-supplied.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

import { verify } from "../src/verifier.js";

const REAUTHORED = resolve(
  "../test-vectors/boundary/reauthored-package-issuer-substitution/package.aep",
);
const ORIGINAL = resolve("../test-vectors/valid/mandated-denied-action/package.aep");
const DEV_PUBLIC = readFileSync(resolve("../test-vectors/keys/dev-rsa-4096.pem"), "utf8");

describe("issuer key pinning (§8.1)", () => {
  test("without a trusted-signer list the re-authored package verifies", async () => {
    const result = await verify(new Uint8Array(readFileSync(REAUTHORED)));
    expect(result.valid).toBe(true);
    expect(result.metadata?.policy_decision).toBe("allow");
    // The mandate is not what fails: it verifies over its own bytes.
    expect(result.mandate).toMatchObject({ bound: true, signatureVerified: true });
    expect(result.boundary.checks.find((c) => c.id === "signer-key-pinned")).toMatchObject({
      verdict: "not_assessed",
      enforced: false,
      reason: "option_disabled",
    });
  });

  test("with the real issuer key pinned the same bytes are rejected", async () => {
    const result = await verify(new Uint8Array(readFileSync(REAUTHORED)), {
      trustedSignerPems: [DEV_PUBLIC],
    });
    expect(result.valid).toBe(false);
    expect(result.failureReason).toBe(
      "public_key.pem is not a member of the caller-supplied trustedSignerPems list.",
    );
    expect(result.boundary.checks.find((c) => c.id === "signer-key-pinned")).toMatchObject({
      verdict: "fail",
      enforced: true,
    });
  });

  test("the untampered package passes the same pinned run", async () => {
    const result = await verify(new Uint8Array(readFileSync(ORIGINAL)), {
      trustedSignerPems: [DEV_PUBLIC],
    });
    expect(result.valid).toBe(true);
    expect(result.metadata?.policy_decision).toBe("deny");
    expect(result.boundary.checks.find((c) => c.id === "signer-key-pinned")).toMatchObject({
      verdict: "pass",
      enforced: true,
    });
  });

  test("pinning ignores PEM whitespace differences", async () => {
    const result = await verify(new Uint8Array(readFileSync(ORIGINAL)), {
      trustedSignerPems: [DEV_PUBLIC.replace(/\n/g, "\r\n")],
    });
    expect(result.valid).toBe(true);
  });
});
