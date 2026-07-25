/**
 * `eatf-canonical-1` canonicalisation algorithm,
 * matching the canonical forms described in `docs/aep-format.md`.
 *
 * Steps:
 *   1. UTF-8 bytes of response.txt, verbatim line endings.
 *   2. LF separator (0x0A).
 *   3. RFC 8785 JSON Canonicalisation Scheme (JCS) of metadata.json.
 *
 * The result is the byte sequence that the SHA-256 hash + RSA + ML-DSA
 * signatures are computed over.
 */

import canonicalizeJson from "canonicalize";

const TEXT_ENC = new TextEncoder();

export type CanonicalPair = {
  /** The textual payload as bytes (response.txt). */
  responseBytes: Uint8Array;
  /** Canonicalised metadata.json. */
  metadataBytes: Uint8Array;
};

/**
 * Concatenate response + LF + metadata into the canonical byte
 * sequence that is hashed and signed.
 */
export function canonical(pair: CanonicalPair): Uint8Array {
  const sep = new Uint8Array([0x0a]);
  const out = new Uint8Array(
    pair.responseBytes.length + sep.length + pair.metadataBytes.length,
  );
  out.set(pair.responseBytes, 0);
  out.set(sep, pair.responseBytes.length);
  out.set(pair.metadataBytes, pair.responseBytes.length + sep.length);
  return out;
}

/**
 * RFC 8785 JSON Canonicalization Scheme (JCS), encoded as UTF-8.
 * The maintained `canonicalize` implementation handles UTF-16 member
 * ordering, I-JSON number serialization, escaping, and nested values.
 */
export function jcs(value: unknown): Uint8Array {
  assertIJson(value, new Set<object>());
  const serialized = canonicalizeJson(value);
  if (serialized === undefined) {
    throw new Error("Value is not representable by RFC 8785 JCS.");
  }
  return TEXT_ENC.encode(serialized);
}

function assertIJson(value: unknown, seen: Set<object>): void {
  if (value === null || typeof value === "boolean") return;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new Error("RFC 8785 JCS does not support non-finite numbers.");
    }
    if (Number.isInteger(value) && !Number.isSafeInteger(value)) {
      throw new Error("RFC 8785 JCS requires integers in the I-JSON safe range.");
    }
    return;
  }
  if (typeof value === "string") {
    assertUnicodeScalarString(value);
    return;
  }
  if (typeof value !== "object") {
    throw new Error(`RFC 8785 JCS does not support ${typeof value} values.`);
  }
  if (seen.has(value)) {
    throw new Error("RFC 8785 JCS does not support circular references.");
  }
  seen.add(value);
  if (Array.isArray(value)) {
    for (const item of value) assertIJson(item, seen);
  } else {
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      assertUnicodeScalarString(key);
      assertIJson(item, seen);
    }
  }
  seen.delete(value);
}

function assertUnicodeScalarString(value: string): void {
  for (let index = 0; index < value.length; index += 1) {
    const unit = value.charCodeAt(index);
    if (unit >= 0xd800 && unit <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (!(next >= 0xdc00 && next <= 0xdfff)) {
        throw new Error("RFC 8785 JCS input contains an unpaired UTF-16 surrogate.");
      }
      index += 1;
    } else if (unit >= 0xdc00 && unit <= 0xdfff) {
      throw new Error("RFC 8785 JCS input contains an unpaired UTF-16 surrogate.");
    }
  }
}
