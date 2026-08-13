import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

import { unzipSync } from "fflate";

import { verify } from "../src/verifier.js";
import { sign } from "../src/signer.js";

// Shared test vectors live at the repository root under test-vectors/.
// vitest runs with cwd == lib/, so the relative path is ../test-vectors/.
const VALID_DIR = resolve("../test-vectors/valid");
const INVALID_DIR = resolve("../test-vectors/invalid");
const KEYS_DIR = resolve("../test-vectors/keys");

describe("VerifyResult.canonicalForm", () => {
  test("reports \"profile\" for the profile-canonical fixture", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "profile-canonical/package.aep"));

    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.canonicalForm).toBe("profile");
    expect(result.report).toContain("Canonical bytes match AEP profile canonical form.");
  });

  test("reports \"response-only\" for the minimal-roundtrip fixture", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "minimal-roundtrip/package.aep"));

    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.canonicalForm).toBe("response-only");
    expect(result.report).toContain("Canonical bytes match Java response-only canonical form.");
  });

  test("is null when verification fails before the canonical-form check", async () => {
    const result = await verify(new Uint8Array([0x00, 0x01, 0x02, 0x03]));

    expect(result.valid).toBe(false);
    expect(result.canonicalForm).toBe(null);
  });

  test("survives a failure after the canonical-form check", async () => {
    // tampered-metadata fails at the OVERT-inspired receipt cross-check, which
    // runs after the canonical form has already matched.
    const bytes = await readFile(resolve(INVALID_DIR, "tampered-metadata/package.aep"));

    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(false);
    expect(result.canonicalForm).toBe("response-only");
  });

  test("sign() with canonicalForm \"profile\" round-trips as profile", async () => {
    const baseline = unzipSync(
      new Uint8Array(await readFile(resolve(VALID_DIR, "valid-overt-profile/package.aep"))),
    );
    const output = await sign({
      payload: "canonicalForm round-trip probe.\n",
      privateKeyPem: await readFile(resolve(KEYS_DIR, "dev-rsa-4096.key"), "utf8"),
      publicKeyPem: await readFile(resolve(KEYS_DIR, "dev-rsa-4096.pem"), "utf8"),
      metadata: {
        schema: "urn:eatf:spec:aep:metadata:1.0",
        attestation_id: "att_canonical_form_probe_01",
        created_at: "2026-05-15T20:00:00Z",
      },
      overtScope: "foundational:aep-response",
      timestampTsr: baseline["timestamp.tsr"]!,
      canonicalForm: "profile",
    });

    const result = await verify(output.aep, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.canonicalForm).toBe("profile");
  });
});
