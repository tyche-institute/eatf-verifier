import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { describe, expect, test } from "vitest";

import { verify } from "../src/verifier.js";
import { sign } from "../src/signer.js";
import { unzipSync } from "fflate";
import {
  CHECK_REGISTRY,
  CHECK_REGISTRY_VERSION,
  checkRegistryDigest,
} from "../src/check-registry.js";

// Shared test vectors live at the repository root under test-vectors/.
// vitest runs with cwd == lib/, so the relative path is ../test-vectors/.
const VALID_DIR = resolve("../test-vectors/valid");
const INVALID_DIR = resolve("../test-vectors/invalid");
const KEYS_DIR = resolve("../test-vectors/keys");

function checkById(result: Awaited<ReturnType<typeof verify>>, id: string) {
  const found = result.boundary.checks.find((c) => c.id === id);
  expect(found, `boundary must carry check ${id}`).toBeDefined();
  return found!;
}

describe("VerifyResult.boundary", () => {
  test("carries the full registry, in order, on success", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "minimal-roundtrip/package.aep"));
    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.boundary.registryVersion).toBe(CHECK_REGISTRY_VERSION);
    expect(result.boundary.registryDigest).toBe(await checkRegistryDigest());
    expect(result.boundary.checks.map((c) => c.id)).toEqual(CHECK_REGISTRY.map((c) => c.id));
  });

  test("carries the full registry on failure too, tail short-circuited", async () => {
    const bytes = await readFile(resolve(INVALID_DIR, "missing-canonical-bin/package.aep"));
    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(false);
    expect(result.boundary.checks.map((c) => c.id)).toEqual(CHECK_REGISTRY.map((c) => c.id));
    expect(checkById(result, "required-entries")).toMatchObject({ verdict: "fail", enforced: true });
    const tail = result.boundary.checks.slice(
      result.boundary.checks.findIndex((c) => c.id === "metadata-parse"),
    );
    for (const check of tail) {
      expect(check).toMatchObject({
        verdict: "not_assessed",
        enforced: false,
        reason: "short_circuited",
      });
    }
  });

  test("response-only acceptance records the profile-form failure as advisory", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "minimal-roundtrip/package.aep"));
    const result = await verify(bytes, { tsaTrustList: [] });

    expect(checkById(result, "canonical-profile")).toMatchObject({ verdict: "fail", enforced: false });
    expect(checkById(result, "canonical-response-only")).toMatchObject({ verdict: "pass", enforced: true });
    expect(result.boundary.canonicalForm).toBe("response-only");
  });

  test("advisory TSA imprint failure stays valid:true with enforced:false", async () => {
    // Every shipped valid vector carries a timestamp token issued over a
    // different hash (the CI round-trip grafts older tokens), so the
    // imprint check fails while the package verifies — the live
    // "assessed, failed, accepted anyway" specimen.
    const bytes = await readFile(resolve(VALID_DIR, "minimal-roundtrip/package.aep"));
    const result = await verify(bytes, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(checkById(result, "tsa-imprint")).toMatchObject({ verdict: "fail", enforced: false });
    expect(checkById(result, "tsa-signerinfo")).toMatchObject({
      verdict: "not_determinate",
      enforced: false,
      reason: "input_absent",
    });
  });

  test("empty tsaTrustList records the chain check as option_disabled", async () => {
    const bytes = await readFile(resolve(VALID_DIR, "minimal-roundtrip/package.aep"));
    const result = await verify(bytes, { tsaTrustList: [] });

    expect(checkById(result, "tsa-chain-to-root")).toMatchObject({
      verdict: "not_assessed",
      enforced: false,
      reason: "option_disabled",
    });
  });

  test("unsignedFields lists every metadata field under response-only, none under profile", async () => {
    const responseOnly = await verify(
      await readFile(resolve(VALID_DIR, "minimal-roundtrip/package.aep")),
      { tsaTrustList: [] },
    );
    const metadataKeys = Object.keys(responseOnly.metadata!).sort();
    expect(responseOnly.boundary.unsignedFields).toEqual(metadataKeys.map((k) => `metadata.${k}`));

    const profile = await verify(
      await readFile(resolve(VALID_DIR, "profile-canonical/package.aep")),
      { tsaTrustList: [] },
    );
    expect(profile.boundary.canonicalForm).toBe("profile");
    expect(profile.boundary.unsignedFields).toEqual([]);
  });

  test("claimed_assessment_surface produces a claimed-vs-computed diff", async () => {
    const baseline = unzipSync(
      new Uint8Array(await readFile(resolve(VALID_DIR, "valid-overt-profile/package.aep"))),
    );
    const output = await sign({
      payload: "boundary claimed-surface probe.\n",
      privateKeyPem: await readFile(resolve(KEYS_DIR, "dev-rsa-4096.key"), "utf8"),
      publicKeyPem: await readFile(resolve(KEYS_DIR, "dev-rsa-4096.pem"), "utf8"),
      metadata: {
        schema: "urn:eatf:spec:aep:metadata:1.0",
        attestation_id: "att_boundary_claim_probe_01",
        created_at: "2026-05-15T20:00:00Z",
        claimed_assessment_surface: ["hash-sha256", "tsa-chain-to-root", "no-such-check"],
      },
      overtScope: "foundational:aep-response",
      timestampTsr: baseline["timestamp.tsr"]!,
    });

    const result = await verify(output.aep, { tsaTrustList: [] });

    expect(result.valid).toBe(true);
    expect(result.boundary.claimedSurface).toEqual({
      claimed: ["hash-sha256", "no-such-check", "tsa-chain-to-root"],
      unrecognized: ["no-such-check"],
      notAssessed: ["tsa-chain-to-root"],
    });
  });

  test("claimedSurface is null when the metadata field is absent", async () => {
    const result = await verify(
      await readFile(resolve(VALID_DIR, "minimal-roundtrip/package.aep")),
      { tsaTrustList: [] },
    );
    expect(result.boundary.claimedSurface).toBe(null);
  });
});
