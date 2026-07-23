/**
 * Phase 1 step 1.20: ML-DSA-65 (NIST FIPS 204) signature verification.
 *
 * Web Crypto does not yet expose ML-DSA. We use `@noble/post-quantum`
 * which ships pure-TS implementations of Kyber and Dilithium / ML-DSA.
 * `@noble/post-quantum`'s `ml_dsa65` matches the parameter set the
 * EATF Java reference uses (`PqcSignatureServiceImpl`).
 *
 * v0.1-alpha caveat: the dependency is imported lazily so that bundlers
 * that strip unused exports do not pull the WASM/JS body unless the
 * caller actually verifies a PQC-signed package.
 */

import { decodeBase64 } from "./rsa.js";

/** Raw ML-DSA-65 public key size per NIST FIPS 204. */
const ML_DSA_65_PUBLIC_KEY_BYTES = 1952;

/**
 * Parse the ML-DSA-65 public key from PEM. Two encodings are accepted:
 *
 *   (a) Raw 1952-byte key body base64-wrapped in PEM. Phase 1.20
 *       reference profile (eatf-sign CLI).
 *   (b) SubjectPublicKeyInfo (RFC 5280) wrapping the raw key as a
 *       BIT STRING under the ML-DSA-65 OID (2.16.840.1.101.3.4.3.18).
 *       What the reference signing implementation emits via
 *       {@code SubjectPublicKeyInfoFactory.createSubjectPublicKeyInfo}.
 *
 * If the decoded blob is exactly 1952 bytes we treat it as raw. Anything
 * larger is parsed as SPKI and the BIT STRING contents are returned;
 * we tolerate either a leading 0x00 unused-bits octet or its absence.
 */
function pemToRawPublicKey(pem: string): Uint8Array {
  const body = pem
    .replace(/-----BEGIN [^-]+-----/g, "")
    .replace(/-----END [^-]+-----/g, "")
    .replace(/\s+/g, "");
  const decoded = decodeBase64(body);
  if (decoded.length === ML_DSA_65_PUBLIC_KEY_BYTES) {
    return decoded;
  }
  const unwrapped = extractMldsaBitString(decoded);
  if (unwrapped && unwrapped.length === ML_DSA_65_PUBLIC_KEY_BYTES) {
    return unwrapped;
  }
  // Last-ditch: return whatever was decoded. Noble will reject if the
  // bytes are not a valid ML-DSA-65 public key.
  return decoded;
}

/**
 * Minimal DER walker for the SubjectPublicKeyInfo SEQUENCE that wraps
 * an ML-DSA public key. Returns the contents of the inner BIT STRING
 * with the unused-bits prefix stripped, or `null` on any parse error
 * (the caller falls back to the raw decoded bytes).
 *
 * Layout:
 *   SEQUENCE          30 LL                  -- SPKI
 *     SEQUENCE        30 LL                  -- AlgorithmIdentifier
 *       OBJECT ID     06 LL ...              -- algorithm OID
 *     BIT STRING      03 LL 00 <key bytes>   -- raw ML-DSA-65 public key
 */
function extractMldsaBitString(der: Uint8Array): Uint8Array | null {
  try {
    let p = 0;
    if (der[p++] !== 0x30) return null;            // outer SEQUENCE tag
    const outerLen = readLength(der, p);
    if (outerLen == null) return null;
    p += outerLen.lenBytes;
    if (der[p++] !== 0x30) return null;            // AlgorithmIdentifier SEQUENCE tag
    const algLen = readLength(der, p);
    if (algLen == null) return null;
    p += algLen.lenBytes + algLen.value;            // skip AlgorithmIdentifier
    if (der[p++] !== 0x03) return null;            // BIT STRING tag
    const bsLen = readLength(der, p);
    if (bsLen == null) return null;
    p += bsLen.lenBytes;
    // BIT STRING body starts with one octet giving the count of unused
    // bits at the end of the final octet — for keys that are an integral
    // number of bytes, this is always 0x00. Tolerate either presence
    // (0x00 prefix) or producers that emit the raw bytes directly.
    if (der[p] === 0x00 && bsLen.value === ML_DSA_65_PUBLIC_KEY_BYTES + 1) {
      return der.subarray(p + 1, p + 1 + ML_DSA_65_PUBLIC_KEY_BYTES);
    }
    if (bsLen.value === ML_DSA_65_PUBLIC_KEY_BYTES) {
      return der.subarray(p, p + ML_DSA_65_PUBLIC_KEY_BYTES);
    }
    return null;
  } catch {
    return null;
  }
}

function readLength(der: Uint8Array, off: number): { value: number; lenBytes: number } | null {
  const b = der[off];
  if (b === undefined) return null;
  if (b < 0x80) return { value: b, lenBytes: 1 };
  const n = b & 0x7f;
  if (n === 0 || n > 4) return null;
  let value = 0;
  for (let i = 1; i <= n; i++) {
    const byte = der[off + i];
    if (byte === undefined) return null;
    value = (value << 8) | byte;
  }
  return { value, lenBytes: 1 + n };
}

/**
 * Verify an ML-DSA-65 signature over the canonical byte sequence.
 * Returns boolean; throws only on input shape errors.
 */
export async function verifyMlDsa65(
  publicKeyPem: string,
  signature: Uint8Array,
  signedData: Uint8Array,
): Promise<boolean> {
  // Lazy-import so consumers who only ship RSA-only packages do not
  // pay the ML-DSA bundle cost.
  const mod = await import("@noble/post-quantum/ml-dsa");
  const pub = pemToRawPublicKey(publicKeyPem);
  try {
    return mod.ml_dsa65.verify(pub, signedData, signature);
  } catch {
    return false;
  }
}
