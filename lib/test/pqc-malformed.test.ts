import { readFile } from "node:fs/promises";
import { unzipSync, zipSync } from "fflate";
import { describe, expect, test } from "vitest";

import type { VerifyOptions } from "../src/index.js";
import { verify } from "../src/verifier.js";

// Malformed ML-DSA entries must yield valid=false with a stable first-failure
// code, never a thrown error. lib-python/tests/test_pqc_malformed.py runs the
// same cases against the Python verifier.

const TEXT_ENC = new TextEncoder();
const NOT_BASE64 = TEXT_ENC.encode("!!!not-base64!!!\n");

async function labEntries(name: string): Promise<Record<string, Uint8Array>> {
  const source = await readFile(
    new URL(`../../workshops/pqc-hybrid-lab/packages/${name}`, import.meta.url),
  );
  return unzipSync(source);
}

const hybridEntries = () => labEntries("01-valid-hybrid.aep");

async function keyFile(name: string): Promise<Uint8Array> {
  return readFile(new URL(`../../test-vectors/keys/${name}`, import.meta.url));
}

const rsaPublicKeyPem = () => keyFile("dev-rsa-4096.pem");

// dev-mldsa65.pem is the key that signed 01-valid-hybrid.aep.
async function pinnedOptions(): Promise<VerifyOptions> {
  return { trustedPqcSignerPems: [new TextDecoder().decode(await keyFile("dev-mldsa65.pem"))] };
}

const PIN_MODES: Array<[string, () => Promise<VerifyOptions>]> = [
  ["without a key pin", async () => ({})],
  ["with a key pin", pinnedOptions],
];

function signatureText(entries: Record<string, Uint8Array>): string {
  return new TextDecoder().decode(entries["signature_pqc.sig"]!).trim();
}

function concat(...parts: Uint8Array[]): Uint8Array {
  const out = new Uint8Array(parts.reduce((n, part) => n + part.length, 0));
  let offset = 0;
  for (const part of parts) {
    out.set(part, offset);
    offset += part.length;
  }
  return out;
}

function wrap(signature: string, separators: number[]): Uint8Array {
  const lines = signature.match(/.{1,64}/g)!;
  const parts: Uint8Array[] = [];
  lines.forEach((line, i) => {
    parts.push(TEXT_ENC.encode(line), new Uint8Array([separators[i % separators.length]!]));
  });
  return concat(...parts);
}

const BAD_SIGNATURES: Array<[string, (signature: string) => Uint8Array]> = [
  ["text that is not base64", () => NOT_BASE64],
  [
    "a stray character inside the valid signature",
    (signature) => TEXT_ENC.encode(`${signature.slice(0, 100)}!${signature.slice(100)}\n`),
  ],
  ["base64 without its padding", () => TEXT_ENC.encode("AAAAAA\n")],
  ["padding in the middle", () => TEXT_ENC.encode("AA==AA==\n")],
  ["excess padding", () => TEXT_ENC.encode("AAAA====\n")],
  [
    "the URL-safe alphabet",
    (signature) => TEXT_ENC.encode(`${signature.replace(/\+/g, "-").replace(/\//g, "_")}\n`),
  ],
  [
    "a non-ASCII byte",
    (signature) => concat(TEXT_ENC.encode(signature), new Uint8Array([0xff, 0x0a])),
  ],
  [
    "a UTF-8 byte-order mark",
    (signature) => concat(new Uint8Array([0xef, 0xbb, 0xbf]), TEXT_ENC.encode(signature)),
  ],
  [
    "a non-breaking space",
    (signature) =>
      concat(
        TEXT_ENC.encode(signature.slice(0, 100)),
        new Uint8Array([0xc2, 0xa0]),
        TEXT_ENC.encode(signature.slice(100)),
      ),
  ],
];

describe("malformed ML-DSA entries", () => {
  test("rejects an RSA key in pqc_public_key.pem with PQC_VERIFY_ERROR", async () => {
    const entries = await hybridEntries();
    entries["pqc_public_key.pem"] = await rsaPublicKeyPem();
    const result = await verify(zipSync(entries, { level: 0 }));
    expect(result).toMatchObject({
      valid: false,
      failureCode: "PQC_VERIFY_ERROR",
      pqcValid: false,
    });
  });

  test("rejects a pqc_public_key.pem that is not a PEM block with PQC_VERIFY_ERROR", async () => {
    const entries = await hybridEntries();
    entries["pqc_public_key.pem"] = TEXT_ENC.encode("garbage\n");
    const result = await verify(zipSync(entries, { level: 0 }));
    expect(result).toMatchObject({
      valid: false,
      failureCode: "PQC_VERIFY_ERROR",
      pqcValid: false,
    });
  });

  test("rejects an empty pqc_public_key.pem with PQC_VERIFY_ERROR", async () => {
    const entries = await hybridEntries();
    entries["pqc_public_key.pem"] = new Uint8Array(0);
    const result = await verify(zipSync(entries, { level: 0 }));
    expect(result).toMatchObject({
      valid: false,
      failureCode: "PQC_VERIFY_ERROR",
      pqcValid: false,
    });
  });

  test("rejects an empty ML-DSA pair added to a classical package", async () => {
    const entries = await labEntries("04-classical-transition.aep");
    entries["signature_pqc.sig"] = new Uint8Array(0);
    entries["pqc_public_key.pem"] = new Uint8Array(0);
    const result = await verify(zipSync(entries, { level: 0 }));
    expect(result).toMatchObject({
      valid: false,
      failureCode: "PQC_VERIFY_ERROR",
      pqcValid: false,
    });
  });
});

describe.each(PIN_MODES)("signature_pqc.sig %s", (_mode, options) => {
  test.each(BAD_SIGNATURES)("rejects %s with PQC_SIGNATURE_ENCODING", async (_label, mutate) => {
    const entries = await hybridEntries();
    entries["signature_pqc.sig"] = mutate(signatureText(entries));
    const result = await verify(zipSync(entries, { level: 0 }), await options());
    expect(result).toMatchObject({
      valid: false,
      failureCode: "PQC_SIGNATURE_ENCODING",
      pqcValid: false,
    });
  });

  test("decodes a multi-megabyte entry without throwing", async () => {
    const entries = await hybridEntries();
    entries["signature_pqc.sig"] = TEXT_ENC.encode(`${"A".repeat(4_600_000)}\n`);
    const result = await verify(zipSync(entries, { level: 0 }), await options());
    expect(result).toMatchObject({
      valid: false,
      failureCode: "PQC_SIGNATURE_INVALID",
      pqcValid: false,
    });
  });

  test("still accepts a signature wrapped at 64 columns with CRLF", async () => {
    const entries = await hybridEntries();
    const signature = signatureText(entries);
    entries["signature_pqc.sig"] = TEXT_ENC.encode(
      `${signature.match(/.{1,64}/g)!.join("\r\n")}\r\n`,
    );
    const result = await verify(zipSync(entries, { level: 0 }), await options());
    expect(result).toMatchObject({ valid: true, failureCode: null, pqcValid: true });
  });

  test("ignores each of TAB, LF, VT, FF, CR and space", async () => {
    const entries = await hybridEntries();
    entries["signature_pqc.sig"] = wrap(
      signatureText(entries),
      [0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x20],
    );
    const result = await verify(zipSync(entries, { level: 0 }), await options());
    expect(result).toMatchObject({ valid: true, failureCode: null, pqcValid: true });
  });
});

describe("check order: key pin, then signature encoding, then key and signature", () => {
  test("without a pin, the signature encoding is reported before an unusable key", async () => {
    const entries = await hybridEntries();
    entries["signature_pqc.sig"] = NOT_BASE64;
    entries["pqc_public_key.pem"] = await rsaPublicKeyPem();
    const result = await verify(zipSync(entries, { level: 0 }));
    expect(result).toMatchObject({
      valid: false,
      failureCode: "PQC_SIGNATURE_ENCODING",
      pqcValid: false,
    });
  });

  test("with a pin, an unusable key is reported before the signature encoding", async () => {
    const entries = await hybridEntries();
    entries["signature_pqc.sig"] = NOT_BASE64;
    entries["pqc_public_key.pem"] = await rsaPublicKeyPem();
    const result = await verify(zipSync(entries, { level: 0 }), await pinnedOptions());
    expect(result).toMatchObject({
      valid: false,
      failureCode: "PQC_VERIFY_ERROR",
      pqcValid: null,
    });
  });

  test("with a pin, a foreign key is reported before the signature encoding", async () => {
    const entries = await labEntries("07-foreign-mldsa-key.aep");
    entries["signature_pqc.sig"] = NOT_BASE64;
    const result = await verify(zipSync(entries, { level: 0 }), await pinnedOptions());
    expect(result).toMatchObject({
      valid: false,
      failureCode: "PQC_SIGNER_NOT_TRUSTED",
      pqcValid: null,
    });
  });
});
