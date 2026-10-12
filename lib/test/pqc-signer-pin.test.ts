import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { unzipSync } from "fflate";
import { describe, expect, test } from "vitest";

import { verify } from "../src/index.js";
import { mlDsa65PublicKeyFromPem } from "../src/mldsa.js";

const LAB = resolve("../workshops/pqc-hybrid-lab");
const KEYS = resolve("../test-vectors/keys");

async function labPackage(name: string): Promise<Uint8Array> {
  return new Uint8Array(await readFile(resolve(LAB, "packages", name)));
}

async function keyPem(name: string): Promise<string> {
  return readFile(resolve(KEYS, name), "utf8");
}

function legacyRawPem(spkiPem: string): string {
  const body = Buffer.from(mlDsa65PublicKeyFromPem(spkiPem)).toString("base64");
  return `-----BEGIN ML-DSA-65 PUBLIC KEY-----\n${body.match(/.{1,64}/g)!.join("\n")}\n-----END ML-DSA-65 PUBLIC KEY-----\n`;
}

describe("caller-supplied ML-DSA-65 signer pin", () => {
  test("accepts the hybrid package when its ML-DSA key matches the pin", async () => {
    const result = await verify(await labPackage("01-valid-hybrid.aep"), {
      pqcPolicy: "required",
      trustedPqcSignerPems: [await keyPem("dev-mldsa65.pem")],
    });
    expect(result.valid).toBe(true);
    expect(result.pqcValid).toBe(true);
    expect(result.report).toContain(
      "ML-DSA-65 signer public key matched the caller-supplied trust set.",
    );
  });

  test("compares decoded keys, so the legacy raw-key PEM spelling also matches", async () => {
    const result = await verify(await labPackage("01-valid-hybrid.aep"), {
      trustedPqcSignerPems: [legacyRawPem(await keyPem("dev-mldsa65.pem"))],
    });
    expect(result.valid).toBe(true);
    expect(result.pqcValid).toBe(true);
  });

  test("accepts a foreign ML-DSA key without a pin, even under the required policy", async () => {
    const result = await verify(await labPackage("07-foreign-mldsa-key.aep"), {
      pqcPolicy: "required",
      trustedSignerPems: [await keyPem("dev-rsa-4096.pem")],
    });
    expect(result.valid).toBe(true);
    expect(result.pqcValid).toBe(true);
    expect(result.report).toContain(
      "ML-DSA-65 signer identity not evaluated (no trustedPqcSignerPems supplied).",
    );
  });

  test("rejects a foreign ML-DSA key over the same canonical bytes", async () => {
    const result = await verify(await labPackage("07-foreign-mldsa-key.aep"), {
      pqcPolicy: "required",
      trustedSignerPems: [await keyPem("dev-rsa-4096.pem")],
      trustedPqcSignerPems: [await keyPem("dev-mldsa65.pem")],
    });
    expect(result.valid).toBe(false);
    expect(result.failureCode).toBe("PQC_SIGNER_NOT_TRUSTED");
    expect(result.pqcValid).toBeNull();
  });

  test("accepts any member of a multi-key pin set", async () => {
    const foreign = unzipSync(await labPackage("07-foreign-mldsa-key.aep"));
    const foreignPem = new TextDecoder().decode(foreign["pqc_public_key.pem"]);
    const result = await verify(await labPackage("01-valid-hybrid.aep"), {
      trustedPqcSignerPems: [foreignPem, await keyPem("dev-mldsa65.pem")],
    });
    expect(result.valid).toBe(true);
  });

  test("implies the required policy, so a classical-only package cannot bypass it", async () => {
    const result = await verify(await labPackage("04-classical-transition.aep"), {
      pqcPolicy: "if-present",
      trustedPqcSignerPems: [await keyPem("dev-mldsa65.pem")],
    });
    expect(result.valid).toBe(false);
    expect(result.failureCode).toBe("PQC_SIGNATURE_REQUIRED");
    expect(result.failureReason).toContain("key pin");
  });

  test("throws on a pin that is not an ML-DSA-65 public key", async () => {
    await expect(
      verify(await labPackage("01-valid-hybrid.aep"), {
        trustedPqcSignerPems: [await keyPem("dev-rsa-4096.pem")],
      }),
    ).rejects.toThrow("trustedPqcSignerPems[0] is not an ML-DSA-65 public key");
  });
});
