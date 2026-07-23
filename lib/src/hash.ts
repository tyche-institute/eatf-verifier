/**
 * v0.1: SHA-256 over the canonical byte sequence, via
 * Web Crypto SubtleCrypto (browser + Node 20+).
 */

const HEX = "0123456789abcdef";

export async function sha256(data: Uint8Array): Promise<Uint8Array> {
  // Re-wrap to keep TypeScript's BufferSource happy across DOM and Node lib defs.
  const buffer = new Uint8Array(data).buffer;
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return new Uint8Array(digest);
}

export function toHex(bytes: Uint8Array): string {
  let out = "";
  for (let i = 0; i < bytes.length; i++) {
    const b = bytes[i]!;
    out += HEX.charAt(b >>> 4) + HEX.charAt(b & 0x0f);
  }
  return out;
}

export function fromHex(hex: string): Uint8Array {
  const clean = hex.trim().toLowerCase();
  if (clean.length % 2 !== 0) throw new Error("Hex string of odd length.");
  const out = new Uint8Array(clean.length / 2);
  for (let i = 0; i < out.length; i++) {
    const hi = parseInt(clean.charAt(2 * i), 16);
    const lo = parseInt(clean.charAt(2 * i + 1), 16);
    if (Number.isNaN(hi) || Number.isNaN(lo)) throw new Error("Invalid hex.");
    out[i] = (hi << 4) | lo;
  }
  return out;
}
