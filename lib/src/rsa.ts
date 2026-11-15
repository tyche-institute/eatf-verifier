/**
 * v0.1: RSA-4096 signature verification via Web Crypto.
 *
 * EATF signs with PKCS#1 v1.5 over SHA-256. The Java reference uses
 * `Signature.getInstance("SHA256withRSA", "BC")` which is the same
 * scheme. Web Crypto exposes it as `RSASSA-PKCS1-v1_5` with hash
 * SHA-256.
 *
 * Public key arrives as PEM: exactly one block labelled PUBLIC KEY whose body
 * is the DER SubjectPublicKeyInfo (SPKI) of an RSA key. The signer trust check
 * and the signature check both use these DER bytes.
 */

/**
 * Parse PEM text that holds exactly one block and nothing but whitespace
 * around it. `public_key.pem`, `pqc_public_key.pem` and every key pin are
 * read with this one rule; lib-python/eatf_verifier/pem.py ports it.
 */
export function parsePem(pem: string): { label: string; bytes: Uint8Array } {
  // One body group that starts and ends with whitespace accepts the same text
  // as \s+(...)\s+ but cannot backtrack cubically on a long whitespace run.
  const match = pem.trim().match(
    /^-----BEGIN ([A-Z0-9 -]+)-----(\s[A-Za-z0-9+/=\s]+\s)-----END \1-----$/,
  );
  if (!match) throw new Error("Malformed PEM block");
  return { label: match[1]!, bytes: decodeBase64(match[2]!.replace(/\s+/g, "")) };
}

/**
 * The DER SubjectPublicKeyInfo inside `public_key.pem` or an RSA signer pin:
 * one PEM block labelled PUBLIC KEY whose DER is one SEQUENCE with nothing
 * after it. `importRsaSpki` then requires the DER encoding of an RSA key.
 */
export function rsaSpkiFromPem(pem: string): Uint8Array {
  const block = parsePem(pem);
  if (block.label !== "PUBLIC KEY") {
    throw new Error(`PEM label is ${block.label}, not PUBLIC KEY`);
  }
  const c: DerCursor = { bytes: block.bytes, offset: 0 };
  const length = readSequence(c);
  if (c.offset + length !== block.bytes.length) {
    throw new Error("bytes follow the SubjectPublicKeyInfo");
  }
  return block.bytes;
}

/**
 * Import an RSA SubjectPublicKeyInfo and require that Web Crypto encodes the
 * imported key back to the same bytes, so that no other reading of `spki`
 * than the key that verifies exists. lib-python applies the same rule.
 */
export async function importRsaSpki(spki: Uint8Array): Promise<CryptoKey> {
  const key = await crypto.subtle.importKey(
    "spki",
    spki.slice().buffer,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    true,
    ["verify"],
  );
  const encoded = new Uint8Array(await crypto.subtle.exportKey("spki", key));
  if (!constantTimeEqual(encoded, spki)) {
    throw new Error("SubjectPublicKeyInfo is not the DER encoding of an RSA key");
  }
  return key;
}

export async function importRsaPublicKey(pem: string): Promise<CryptoKey> {
  return importRsaSpki(rsaSpkiFromPem(pem));
}

export async function verifyRsa(
  key: CryptoKey,
  signature: Uint8Array,
  signedData: Uint8Array,
): Promise<boolean> {
  return crypto.subtle.verify(
    "RSASSA-PKCS1-v1_5",
    key,
    (signature instanceof Uint8Array ? signature.buffer.slice(signature.byteOffset, signature.byteOffset + signature.byteLength) : signature) as ArrayBuffer,
    (signedData instanceof Uint8Array ? signedData.buffer.slice(signedData.byteOffset, signedData.byteOffset + signedData.byteLength) : signedData) as ArrayBuffer,
  );
}

/**
 * DER prefix of DigestInfo for SHA-256 with the AlgorithmIdentifier
 * parameters absent (`302f300b06096086480165030402010420`).
 *
 * RFC 8017 Appendix B.1 requires NULL parameters inside EMSA-PKCS1-v1_5, so
 * writers MUST NOT produce this form. Packages from the Java reference
 * signer (BouncyCastle NONEwithRSA over this DigestInfo) carry it.
 */
const SHA256_DIGEST_INFO_PREFIX_ABSENT_PARAMS = Uint8Array.from([
  0x30, 0x2f, 0x30, 0x0b, 0x06, 0x09, 0x60, 0x86, 0x48, 0x01, 0x65, 0x03,
  0x04, 0x02, 0x01, 0x04, 0x20,
]);

/**
 * Legacy-encoding compatibility path (read-only).
 *
 * Accepts exactly one encoding besides the RFC 8017 one that `verifyRsa`
 * checks: the full-length block
 * `0x00 0x01 0xFF..0xFF 0x00 || DigestInfo(SHA-256, absent parameters) || H`,
 * with the padding filling the modulus. The function builds that block for
 * the expected digest and compares the whole recovered block with it. Any
 * other DigestInfo, a short padding string, or extra bytes are rejected.
 *
 * Versions up to v0.7.3 stripped the padding and compared only the trailing
 * 32 bytes, which accepted arbitrary bytes between the padding and the digest
 * (the class of Bleichenbacher 2006 and BERserk 2014).
 */
export function verifyRsaDigestInfo(
  publicKeyPem: string,
  signature: Uint8Array,
  expectedDigest: Uint8Array,
): boolean {
  if (expectedDigest.length !== 32 || signature.length === 0) return false;
  return verifyRsaDigestInfoSpki(rsaSpkiFromPem(publicKeyPem), signature, expectedDigest);
}

/** `verifyRsaDigestInfo` over a SubjectPublicKeyInfo that `rsaSpkiFromPem` returned. */
export function verifyRsaDigestInfoSpki(
  spki: Uint8Array,
  signature: Uint8Array,
  expectedDigest: Uint8Array,
): boolean {
  if (expectedDigest.length !== 32 || signature.length === 0) return false;
  const { modulus, exponent } = parseRsaSpki(spki);
  const modulusBytes = Math.ceil(bitLength(modulus) / 8);
  if (signature.length !== modulusBytes) return false;
  const s = bytesToBigInt(signature);
  if (s >= modulus) return false;

  const tLen = SHA256_DIGEST_INFO_PREFIX_ABSENT_PARAMS.length + expectedDigest.length;
  if (modulusBytes < tLen + 11) return false;
  const expected = new Uint8Array(modulusBytes);
  expected[0] = 0x00;
  expected[1] = 0x01;
  expected.fill(0xff, 2, modulusBytes - tLen - 1);
  expected[modulusBytes - tLen - 1] = 0x00;
  expected.set(SHA256_DIGEST_INFO_PREFIX_ABSENT_PARAMS, modulusBytes - tLen);
  expected.set(expectedDigest, modulusBytes - expectedDigest.length);

  const encoded = bigIntToBytes(modPow(s, exponent, modulus), modulusBytes);
  return constantTimeEqual(encoded, expected);
}

/**
 * Helper: decode a Base64-encoded signature (standard alphabet with
 * padding, as emitted by the Java reference) into raw bytes.
 */
export function decodeBase64(b64: string): Uint8Array {
  const cleaned = b64.replace(/\s+/g, "");
  const raw = atob(cleaned);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

type DerCursor = {
  bytes: Uint8Array;
  offset: number;
};

function parseRsaSpki(spki: Uint8Array): { modulus: bigint; exponent: bigint } {
  const c: DerCursor = { bytes: spki, offset: 0 };
  readSequence(c);
  skipAny(c); // AlgorithmIdentifier
  const bitString = readBitString(c);
  const r: DerCursor = { bytes: bitString, offset: 0 };
  readSequence(r);
  const modulus = bytesToBigInt(readInteger(r));
  const exponent = bytesToBigInt(readInteger(r));
  if (modulus <= 0n || exponent <= 0n) throw new Error("Invalid RSA public key.");
  return { modulus, exponent };
}

function readSequence(c: DerCursor): number {
  return readTagAndLength(c, 0x30);
}

function readInteger(c: DerCursor): Uint8Array {
  const len = readTagAndLength(c, 0x02);
  let out = c.bytes.slice(c.offset, c.offset + len);
  c.offset += len;
  while (out.length > 1 && out[0] === 0x00) out = out.slice(1);
  return out;
}

function readBitString(c: DerCursor): Uint8Array {
  const len = readTagAndLength(c, 0x03);
  if (len < 1) throw new Error("Invalid BIT STRING.");
  const unusedBits = c.bytes[c.offset]!;
  if (unusedBits !== 0) throw new Error("Unsupported BIT STRING padding.");
  const out = c.bytes.slice(c.offset + 1, c.offset + len);
  c.offset += len;
  return out;
}

function skipAny(c: DerCursor): void {
  if (c.offset >= c.bytes.length) throw new Error("Unexpected end of DER.");
  c.offset++;
  const len = readLength(c);
  c.offset += len;
  if (c.offset > c.bytes.length) throw new Error("DER length exceeds input.");
}

function readTagAndLength(c: DerCursor, expectedTag: number): number {
  if (c.bytes[c.offset++] !== expectedTag) {
    throw new Error("Unexpected DER tag.");
  }
  return readLength(c);
}

function readLength(c: DerCursor): number {
  const first = c.bytes[c.offset++]!;
  if ((first & 0x80) === 0) return first;
  const count = first & 0x7f;
  if (count === 0 || count > 4) throw new Error("Unsupported DER length.");
  let len = 0;
  for (let i = 0; i < count; i++) {
    len = (len << 8) | c.bytes[c.offset++]!;
  }
  if (c.offset + len > c.bytes.length) throw new Error("DER length exceeds input.");
  return len;
}

function bytesToBigInt(bytes: Uint8Array): bigint {
  let out = 0n;
  for (const b of bytes) out = (out << 8n) | BigInt(b);
  return out;
}

function bigIntToBytes(value: bigint, length: number): Uint8Array {
  const out = new Uint8Array(length);
  let current = value;
  for (let i = length - 1; i >= 0; i--) {
    out[i] = Number(current & 0xffn);
    current >>= 8n;
  }
  return out;
}

function bitLength(value: bigint): number {
  return value.toString(2).length;
}

function modPow(base: bigint, exponent: bigint, modulus: bigint): bigint {
  if (modulus === 1n) return 0n;
  let result = 1n;
  let b = base % modulus;
  let e = exponent;
  while (e > 0n) {
    if ((e & 1n) === 1n) result = (result * b) % modulus;
    e >>= 1n;
    b = (b * b) % modulus;
  }
  return result;
}

function constantTimeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i]! ^ b[i]!;
  return diff === 0;
}
