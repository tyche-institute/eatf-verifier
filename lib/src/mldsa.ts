/**
 * v0.1: ML-DSA-65 (NIST FIPS 204) signature verification.
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

/**
 * Parse the ML-DSA-65 public key from PEM. v0.1 ships raw PEM
 * (no X.509 wrapping) because the LAMPS WG ML-DSA OID draft is still
 * in flight. The Java reference emits the raw 1952-byte public key
 * payload base64-wrapped in PEM-style headers.
 */
function pemToRawPublicKey(pem: string): Uint8Array {
  const body = pem
    .replace(/-----BEGIN [^-]+-----/g, "")
    .replace(/-----END [^-]+-----/g, "")
    .replace(/\s+/g, "");
  return decodeBase64(body);
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
