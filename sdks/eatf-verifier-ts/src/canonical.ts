/**
 * Phase 1 step 1.20: `eatf-canonical-1` canonicalisation algorithm,
 * matching `docs/specs/aep-profile-v1.md` §6.
 *
 * Steps:
 *   1. UTF-8 bytes of response.txt, verbatim line endings.
 *   2. LF separator (0x0A).
 *   3. RFC 8785 JSON Canonicalisation Scheme (JCS) of metadata.json.
 *
 * The result is the byte sequence that the SHA-256 hash + RSA + ML-DSA
 * signatures are computed over.
 */

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
 * Minimal RFC 8785-conformant JCS encoder. Constraints from the AEP
 * profile: keys sorted by codepoint, no insignificant whitespace,
 * no trailing zeros in numbers, UTF-8 output, no BOM.
 *
 * v0.1 implementation handles the cases the EATF backend actually
 * emits (objects with string / number / boolean / null / nested
 * objects / arrays). Edge cases around the IEEE 754 number canonical
 * form are delegated to `Number.prototype.toString` which is correct
 * for everything we round-trip; if you need full RFC 8785 number
 * semantics for adversarial inputs, layer in a real JCS library.
 */
export function jcs(value: unknown): Uint8Array {
  return TEXT_ENC.encode(jcsString(value));
}

function jcsString(value: unknown): string {
  if (value === null || typeof value === "boolean" || typeof value === "number") {
    if (typeof value === "number" && !Number.isFinite(value)) {
      throw new Error("JCS does not support non-finite numbers.");
    }
    return JSON.stringify(value);
  }
  if (typeof value === "string") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return "[" + value.map(jcsString).join(",") + "]";
  }
  if (typeof value === "object") {
    const keys = Object.keys(value as Record<string, unknown>)
      .filter((k) => (value as Record<string, unknown>)[k] !== undefined)
      .sort();
    const parts = keys.map((k) => JSON.stringify(k) + ":" + jcsString((value as Record<string, unknown>)[k]));
    return "{" + parts.join(",") + "}";
  }
  throw new Error("Unsupported value type in JCS encoder: " + typeof value);
}
