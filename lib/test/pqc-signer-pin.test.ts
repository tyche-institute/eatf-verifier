import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { unzipSync, zipSync } from "fflate";
import { describe, expect, test } from "vitest";

import { verify } from "../src/index.js";
import {
  generateMlDsa65Keypair,
  mlDsa65PublicKeyFromPem,
  mlDsa65PublicKeyToPem,
} from "../src/mldsa.js";

const LAB = resolve("../workshops/pqc-hybrid-lab");
const KEYS = resolve("../test-vectors/keys");

async function labPackage(name: string): Promise<Uint8Array> {
  return new Uint8Array(await readFile(resolve(LAB, "packages", name)));
}

async function keyPem(name: string): Promise<string> {
  return readFile(resolve(KEYS, name), "utf8");
}

async function foreignPem(): Promise<string> {
  const entries = unzipSync(await labPackage("07-foreign-mldsa-key.aep"));
  return new TextDecoder().decode(entries["pqc_public_key.pem"]);
}

function legacyRawPem(spkiPem: string): string {
  const body = Buffer.from(mlDsa65PublicKeyFromPem(spkiPem)).toString("base64");
  return `-----BEGIN ML-DSA-65 PUBLIC KEY-----\n${body.match(/.{1,64}/g)!.join("\n")}\n-----END ML-DSA-65 PUBLIC KEY-----\n`;
}

function withEntry(packageBytes: Uint8Array, name: string, bytes: Uint8Array): Uint8Array {
  const entries = unzipSync(packageBytes);
  entries[name] = bytes;
  return zipSync(entries);
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

  test("compares decoded keys, so the legacy raw-key PEM form also matches", async () => {
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

  test("enforces the pin under the default if-present policy", async () => {
    const result = await verify(await labPackage("07-foreign-mldsa-key.aep"), {
      trustedPqcSignerPems: [await keyPem("dev-mldsa65.pem")],
    });
    expect(result.valid).toBe(false);
    expect(result.failureCode).toBe("PQC_SIGNER_NOT_TRUSTED");
    expect(result.pqcValid).toBeNull();
  });

  test("accepts any member of a multi-key pin set, in either order", async () => {
    const dev = await keyPem("dev-mldsa65.pem");
    const foreign = await foreignPem();
    for (const pins of [[foreign, dev], [dev, foreign]]) {
      const result = await verify(await labPackage("01-valid-hybrid.aep"), {
        trustedPqcSignerPems: pins,
      });
      expect(result.valid).toBe(true);
    }
  });

  test("rejects when no member of a multi-key pin set matches", async () => {
    const other = mlDsa65PublicKeyToPem(
      (await generateMlDsa65Keypair(new Uint8Array(32).fill(3))).publicKey,
    );
    const result = await verify(await labPackage("01-valid-hybrid.aep"), {
      trustedPqcSignerPems: [await foreignPem(), other],
    });
    expect(result.valid).toBe(false);
    expect(result.failureCode).toBe("PQC_SIGNER_NOT_TRUSTED");
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

  test.each([
    ["an RSA public key", "rsa"],
    ["bytes that are not PEM", "garbage"],
  ])("returns PQC_VERIFY_ERROR when the packaged key is %s and a pin is supplied", async (_label, kind) => {
    const replacement = kind === "rsa"
      ? new Uint8Array(await readFile(resolve(KEYS, "dev-rsa-4096.pem")))
      : new TextEncoder().encode("not a PEM block\n");
    const result = await verify(
      withEntry(await labPackage("01-valid-hybrid.aep"), "pqc_public_key.pem", replacement),
      { trustedPqcSignerPems: [await keyPem("dev-mldsa65.pem")] },
    );
    expect(result.valid).toBe(false);
    expect(result.failureCode).toBe("PQC_VERIFY_ERROR");
    expect(result.pqcValid).toBeNull();
  });

  test("throws on a pin that is not an ML-DSA-65 public key", async () => {
    await expect(
      verify(await labPackage("01-valid-hybrid.aep"), {
        trustedPqcSignerPems: [await keyPem("dev-rsa-4096.pem")],
      }),
    ).rejects.toThrow("trustedPqcSignerPems[0] is not an ML-DSA-65 public key");
  });

  test("throws on a pin that holds two PEM blocks", async () => {
    await expect(
      verify(await labPackage("01-valid-hybrid.aep"), {
        trustedPqcSignerPems: [(await keyPem("dev-mldsa65.pem")) + (await foreignPem())],
      }),
    ).rejects.toThrow("trustedPqcSignerPems[0] is not an ML-DSA-65 public key");
  });
});

// The same table is asserted against the Python parser in
// lib-python/tests/test_pqc_signer_pin.py; both verifiers must agree on every row.
const unwrap = (pem: string): string => {
  const lines = pem.trim().split("\n");
  return `${lines[0]}\n${lines.slice(1, -1).join("")}\n${lines[lines.length - 1]}\n`;
};
const SPELLINGS: Array<[string, (spki: string, legacy: string, foreign: string) => string, boolean]> = [
  ["SPKI as written", (s) => s, true],
  ["CRLF line endings", (s) => s.replace(/\n/g, "\r\n"), true],
  ["leading byte-order mark", (s) => "﻿" + s, true],
  ["surrounding blank lines", (s) => "\n\n" + s + "\n  \n", true],
  ["body on one line", (s) => unwrap(s), true],
  ["legacy raw-key PEM", (_s, l) => l, true],
  ["legacy raw-key PEM without padding", (_s, l) => l.replace("=\n-----END", "\n-----END"), true],
  ["two PEM blocks", (s, _l, f) => s + f, false],
  ["the same block twice", (s) => s + s, false],
  ["text before the block", (s) => "pinned key:\n" + s, false],
  ["text after the block", (s) => s + "end\n", false],
  ["END label differs from BEGIN", (s) => s.replace("-----END PUBLIC KEY-----", "-----END ML-DSA-65 PUBLIC KEY-----"), false],
  ["lower-case label", (s) => s.replace(/PUBLIC KEY/g, "public key"), false],
  ["'=' inside the body", (s) => s.replace("-----\nMII", "-----\nM=II"), false],
  ["SPKI body under the legacy label", (s) => s.replace(/PUBLIC KEY/g, "ML-DSA-65 PUBLIC KEY"), false],
];

const spki = await keyPem("dev-mldsa65.pem");
const legacy = legacyRawPem(spki);
const foreign = await foreignPem();
const expected = mlDsa65PublicKeyFromPem(spki);

describe("ML-DSA-65 PEM parsing (shared with the Python verifier)", () => {
  test.each(SPELLINGS)("%s", (_label, make, accepted) => {
    const pem = make(spki, legacy, foreign);
    if (accepted) {
      expect(mlDsa65PublicKeyFromPem(pem)).toEqual(expected);
    } else {
      expect(() => mlDsa65PublicKeyFromPem(pem)).toThrow();
    }
  });
});
