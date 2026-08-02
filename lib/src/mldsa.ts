/** ML-DSA-65 (NIST FIPS 204) signing, verification, and RFC 9881 SPKI encoding. */

import { decodeBase64 } from "./rsa.js";

const ML_DSA_65_PUBLIC_KEY_BYTES = 1952;
const ML_DSA_SEED_BYTES = 32;

// RFC 9881 id-ml-dsa-65 = 2.16.840.1.101.3.4.3.18. AlgorithmIdentifier
// parameters MUST be absent. The BIT STRING contains the 1952 raw key bytes.
const ML_DSA_65_SPKI_PREFIX = new Uint8Array([
  0x30, 0x82, 0x07, 0xb2,
  0x30, 0x0b,
  0x06, 0x09, 0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x03, 0x12,
  0x03, 0x82, 0x07, 0xa1, 0x00,
]);

export type MlDsa65Keypair = {
  /** The 32-byte seed used to derive the expanded secret key. */
  seed: Uint8Array;
  /** FIPS 204 raw public-key encoding (1952 bytes). */
  publicKey: Uint8Array;
  /** Library-internal expanded secret key. Do not persist this as a standard key encoding. */
  secretKey: Uint8Array;
};

/** Parse either an RFC 9881 SubjectPublicKeyInfo PEM or the legacy raw-key PEM. */
export function mlDsa65PublicKeyFromPem(pem: string): Uint8Array {
  const block = parsePem(pem);
  if (block.label === "PUBLIC KEY") {
    if (block.bytes.length !== ML_DSA_65_SPKI_PREFIX.length + ML_DSA_65_PUBLIC_KEY_BYTES) {
      throw new Error("ML-DSA-65 SubjectPublicKeyInfo has the wrong length");
    }
    for (let i = 0; i < ML_DSA_65_SPKI_PREFIX.length; i += 1) {
      if (block.bytes[i] !== ML_DSA_65_SPKI_PREFIX[i]) {
        throw new Error(
          "ML-DSA-65 SubjectPublicKeyInfo must use id-ml-dsa-65 with absent parameters",
        );
      }
    }
    return block.bytes.slice(ML_DSA_65_SPKI_PREFIX.length);
  }
  if (block.label === "ML-DSA-65 PUBLIC KEY") {
    if (block.bytes.length !== ML_DSA_65_PUBLIC_KEY_BYTES) {
      throw new Error("Legacy ML-DSA-65 raw public key must be 1952 bytes");
    }
    return block.bytes;
  }
  throw new Error(`Unsupported ML-DSA-65 PEM label: ${block.label}`);
}

/** Encode a raw ML-DSA-65 public key as RFC 9881 SubjectPublicKeyInfo PEM. */
export function mlDsa65PublicKeyToPem(publicKey: Uint8Array): string {
  if (publicKey.length !== ML_DSA_65_PUBLIC_KEY_BYTES) {
    throw new Error("ML-DSA-65 public key must be 1952 bytes");
  }
  const spki = new Uint8Array(ML_DSA_65_SPKI_PREFIX.length + publicKey.length);
  spki.set(ML_DSA_65_SPKI_PREFIX);
  spki.set(publicKey, ML_DSA_65_SPKI_PREFIX.length);
  return encodePem("PUBLIC KEY", spki);
}

/** Encode a development/test seed. This is not PKCS #8 and is labelled accordingly. */
export function mlDsa65SeedToPem(seed: Uint8Array): string {
  if (seed.length !== ML_DSA_SEED_BYTES) {
    throw new Error("ML-DSA-65 seed must be 32 bytes");
  }
  return encodePem("ML-DSA-65 SEED", seed);
}

/** Decode the explicit development/test seed format used by eatf-sign. */
export function mlDsa65SeedFromPem(pem: string): Uint8Array {
  const block = parsePem(pem);
  if (block.label !== "ML-DSA-65 SEED" || block.bytes.length !== ML_DSA_SEED_BYTES) {
    throw new Error("Expected a 32-byte ML-DSA-65 SEED PEM block");
  }
  return block.bytes;
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
  const mod = await import("@noble/post-quantum/ml-dsa.js");
  const pub = mlDsa65PublicKeyFromPem(publicKeyPem);
  try {
    return mod.ml_dsa65.verify(signature, signedData, pub);
  } catch {
    return false;
  }
}

/** Generate a fresh, or deterministically seeded, ML-DSA-65 keypair. */
export async function generateMlDsa65Keypair(seed?: Uint8Array): Promise<MlDsa65Keypair> {
  const mod = await import("@noble/post-quantum/ml-dsa.js");
  const actualSeed = seed ? new Uint8Array(seed) : crypto.getRandomValues(new Uint8Array(32));
  if (actualSeed.length !== ML_DSA_SEED_BYTES) {
    throw new Error("ML-DSA-65 key generation seed must be 32 bytes");
  }
  const keypair = mod.ml_dsa65.keygen(actualSeed);
  return {
    seed: actualSeed,
    publicKey: new Uint8Array(keypair.publicKey),
    secretKey: new Uint8Array(keypair.secretKey),
  };
}

/** Produce an ML-DSA-65 signature over the supplied byte sequence. */
export async function signMlDsa65(
  secretKey: Uint8Array,
  signedData: Uint8Array,
  extraEntropy?: Uint8Array | false,
): Promise<Uint8Array> {
  const mod = await import("@noble/post-quantum/ml-dsa.js");
  return new Uint8Array(
    mod.ml_dsa65.sign(signedData, secretKey, { extraEntropy }),
  );
}

function parsePem(pem: string): { label: string; bytes: Uint8Array } {
  const match = pem.trim().match(
    /^-----BEGIN ([A-Z0-9 -]+)-----\s+([A-Za-z0-9+/=\s]+)\s+-----END \1-----$/,
  );
  if (!match) throw new Error("Malformed PEM block");
  return { label: match[1]!, bytes: decodeBase64(match[2]!.replace(/\s+/g, "")) };
}

function encodePem(label: string, bytes: Uint8Array): string {
  const base64 = Buffer.from(bytes).toString("base64");
  const lines = base64.match(/.{1,64}/g) ?? [base64];
  return `-----BEGIN ${label}-----\n${lines.join("\n")}\n-----END ${label}-----\n`;
}
