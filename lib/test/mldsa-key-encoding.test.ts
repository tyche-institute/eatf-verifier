import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { unzipSync, zipSync } from "fflate";
import { describe, expect, test } from "vitest";

import { verify } from "../src/index.js";
import { mlDsa65PublicKeyFromPem } from "../src/mldsa.js";

// Row 3 of docs/hybrid-test-matrix.md: the object identifier, absent parameters
// and the key length of an RFC 9881 ML-DSA-65 SubjectPublicKeyInfo. The same table
// is asserted in lib-python/tests/test_mldsa_key_encoding.py; both verifiers must
// agree on every row.

const LAB = resolve("../workshops/pqc-hybrid-lab");
const KEYS = resolve("../test-vectors/keys");

type Shape = { oidLast?: number; nullParameters?: boolean };

/** DER SubjectPublicKeyInfo for an ML-DSA key. Every length matches its content. */
function spki(key: Uint8Array, { oidLast = 0x12, nullParameters = false }: Shape = {}): Uint8Array {
  const algorithm = [
    0x06, 0x09, 0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x03, oidLast,
    ...(nullParameters ? [0x05, 0x00] : []),
  ];
  const bits = key.length + 1;
  const body = [
    0x30, algorithm.length, ...algorithm,
    0x03, 0x82, bits >> 8, bits & 0xff, 0x00, ...key,
  ];
  return Uint8Array.from([0x30, 0x82, body.length >> 8, body.length & 0xff, ...body]);
}

function pem(der: Uint8Array): string {
  const body = Buffer.from(der).toString("base64").match(/.{1,64}/g)!.join("\n");
  return `-----BEGIN PUBLIC KEY-----\n${body}\n-----END PUBLIC KEY-----\n`;
}

function withEntry(packageBytes: Uint8Array, name: string, bytes: Uint8Array): Uint8Array {
  const entries = unzipSync(packageBytes);
  entries[name] = bytes;
  return zipSync(entries);
}

const ROWS: Array<[string, (key: Uint8Array) => Uint8Array, boolean]> = [
  ["id-ml-dsa-65, absent parameters, 1952-byte key", (k) => spki(k), true],
  ["the id-ml-dsa-44 object identifier", (k) => spki(k, { oidLast: 0x11 }), false],
  ["the id-ml-dsa-87 object identifier", (k) => spki(k, { oidLast: 0x13 }), false],
  ["explicit NULL parameters", (k) => spki(k, { nullParameters: true }), false],
  ["a key one byte short", (k) => spki(k.slice(0, -1)), false],
  ["a key one byte long", (k) => spki(Uint8Array.from([...k, 0x00])), false],
];

const committed = await readFile(resolve(KEYS, "dev-mldsa65.pem"), "utf8");
const key = mlDsa65PublicKeyFromPem(committed);
const hybrid = new Uint8Array(await readFile(resolve(LAB, "packages", "01-valid-hybrid.aep")));

describe("ML-DSA-65 key encoding (shared with the Python verifier)", () => {
  test("the builder reproduces the committed RFC 9881 key byte for byte", () => {
    const der = Buffer.from(
      committed.replace(/-----BEGIN PUBLIC KEY-----|-----END PUBLIC KEY-----|\s+/g, ""),
      "base64",
    );
    expect(der.length).toBe(1974);
    expect(Buffer.from(spki(key)).equals(der)).toBe(true);
  });

  test.each(ROWS)("parser: %s", (_label, make, accepted) => {
    const text = pem(make(key));
    if (accepted) {
      expect(mlDsa65PublicKeyFromPem(text)).toEqual(key);
    } else {
      expect(() => mlDsa65PublicKeyFromPem(text)).toThrow();
    }
  });

  test.each(ROWS)("packaged key: %s", async (_label, make, accepted) => {
    const result = await verify(
      withEntry(hybrid, "pqc_public_key.pem", new TextEncoder().encode(pem(make(key)))),
      { pqcPolicy: "required" },
    );
    expect([result.valid, result.failureCode, result.pqcValid]).toEqual(
      accepted ? [true, null, true] : [false, "PQC_VERIFY_ERROR", false],
    );
  });
});
